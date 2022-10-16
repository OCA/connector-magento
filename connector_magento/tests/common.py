# Copyright 2013-2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

# pylint: disable=missing-manifest-dependency
# disable warning on 'vcr' missing in manifest: this is only a dependency for
# dev/tests

"""
Helpers usable in the tests
"""

import xmlrpc.client
import logging
import urllib

import mock
import odoo

from os.path import dirname, join
from contextlib import contextmanager
from psycopg2.extensions import AsIs
from odoo import models
from odoo.addons.component.tests.common import SavepointComponentCase
from odoo.tools import mute_logger

from vcr import VCR

logging.getLogger("vcr").setLevel(logging.WARNING)

recorder = VCR(
    record_mode='once',
    cassette_library_dir=join(dirname(__file__), 'fixtures/cassettes'),
    path_transformer=VCR.ensure_suffix('.yaml'),
    filter_headers=['Authorization'],
)


class MockResponseImage(object):

    def __init__(self, resp_data, code=200, msg='OK'):
        self.resp_data = resp_data
        self.content = resp_data
        self.status_code = code
        self.msg = msg
        self.headers = {'content-type': 'image/jpeg'}

    def raise_for_status(self):
        if self.status_code != 200:
            raise urllib.error.HTTPError(
                '', self.status_code, str(self.status_code), None, None)

    def read(self):
        # pylint: disable=method-required-super
        return self.resp_data

    def getcode(self):
        return self.code


@contextmanager
def mock_urlopen_image():
    with mock.patch('requests.get') as requests_get:
        requests_get.return_value = MockResponseImage('')
        yield


class MagentoHelper(object):

    def __init__(self, cr, registry, model_name):
        self.cr = cr
        self.model = registry(model_name)

    def get_next_id(self):
        self.cr.execute("SELECT max(external_id::int) FROM %s ",
                        (AsIs(self.model._table),))
        result = self.cr.fetchone()
        if result:
            return int(result[0] or 0) + 1
        else:
            return 1


class MagentoTestCase(SavepointComponentCase):
    """ Base class - Test the imports from a Magento Mock.

    The data returned by Magento are those created for the
    demo version of Magento on a standard 1.9 version.
    """

    @classmethod
    def setUpClass(cls):
        super(MagentoTestCase, cls).setUpClass()
        cls.recorder = recorder
        # disable commits when run from pytest/nosetest
        odoo.tools.config['test_enable'] = True

        cls.backend_model = cls.env['magento.backend']
        warehouse = cls.env.ref('stock.warehouse0')
        cls.backend = cls.backend_model.create(
            {'name': 'Test Magento',
             'version': '1.7',
             'location': 'http://magento',
             'username': 'odoo',
             'warehouse_id': warehouse.id,
             'password': 'odoo42'}
        )
        # payment method needed to import a sale order
        cls.workflow = cls.env.ref(
            'sale_automatic_workflow.manual_validation')
        cls.journal = cls.env['account.journal'].create(
            {'name': 'Check', 'type': 'cash', 'code': 'Check'}
        )
        payment_method = cls.env.ref(
            'account.account_payment_method_manual_in'
        )
        for name in ['checkmo', 'ccsave', 'cashondelivery']:
            cls.env['account.payment.mode'].create(
                {'name': name,
                 'workflow_process_id': cls.workflow.id,
                 'import_rule': 'always',
                 'days_before_cancel': 0,
                 'bank_account_link': 'fixed',
                 'payment_method_id': payment_method.id,
                 'fixed_journal_id': cls.journal.id})

    def get_magento_helper(self, model_name):
        return MagentoHelper(self.cr, self.registry, model_name)

    @classmethod
    def create_binding_no_export(cls, model_name, odoo_id, external_id=None,
                                 **cols):
        if isinstance(odoo_id, models.BaseModel):
            odoo_id = odoo_id.id
        values = {
            'backend_id': cls.backend.id,
            'odoo_id': odoo_id,
            'external_id': external_id,
        }
        if cols:
            values.update(cols)
        return cls.env[model_name].with_context(
            connector_no_export=True
        ).create(values)

    @contextmanager
    def mock_with_delay(self):
        with mock.patch('odoo.addons.queue_job.models.base.DelayableRecordset',
                        name='DelayableRecordset', spec=True
                        ) as delayable_cls:
            # prepare the mocks
            delayable = mock.MagicMock(name='DelayableBinding')
            delayable_cls.return_value = delayable
            yield delayable_cls, delayable

    def parse_cassette_request(self, body):
        args, __ = xmlrpc.client.loads(body)
        # the first argument is a hash, we don't mind
        return args[1:]

    @classmethod
    def _import_record(cls, model_name, magento_id, cassette=True):
        assert model_name.startswith('magento.')
        table_name = model_name.replace('.', '_')
        # strip 'magento_' from the model_name to shorted the filename
        filename = 'import_%s_%s' % (table_name[8:], str(magento_id))

        def run_import():
            with mute_logger(
                    'odoo.addons.mail.models.mail_mail',
                    'odoo.models.unlink',
                    'odoo.tests'):
                if cls.backend.version != '1.7':
                    return cls.env[model_name].import_record(
                        cls.backend, magento_id)
                with mock_urlopen_image():
                    cls.env[model_name].import_record(
                        cls.backend, magento_id)

        if cassette:
            with cls.recorder.use_cassette(filename):
                run_import()
        else:
            run_import()

        binding = cls.env[model_name].search(
            [('backend_id', '=', cls.backend.id),
             ('external_id', '=', str(magento_id))]
        )
        assert len(binding) == 1, "Binding not found after import"
        return binding

    def assert_records(self, expected_records, records):
        """ Assert that a recordset matches with expected values.

        The expected records are a list of nametuple, the fields of the
        namedtuple must have the same name than the recordset's fields.

        The expected values are compared to the recordset and records that
        differ from the expected ones are show as ``-`` (missing) or ``+``
        (extra) lines.

        Example::

            ExpectedShop = namedtuple('ExpectedShop',
                                      'name company_id')
            expected = [
                ExpectedShop(
                    name='MyShop1',
                    company_id=self.company_ch
                ),
                ExpectedShop(
                    name='MyShop2',
                    company_id=self.company_ch
                ),
            ]
            self.assert_records(expected, shops)

        Possible output:

         - foo.shop(name: MyShop1, company_id: res.company(2,))
         - foo.shop(name: MyShop2, company_id: res.company(1,))
         + foo.shop(name: MyShop3, company_id: res.company(1,))

        :param expected_records: list of namedtuple with matching values
                                 for the records
        :param records: the recordset to check
        :raises: AssertionError if the values do not match
        """
        model_name = records._name
        records = list(records)
        assert len(expected_records) > 0, "must have > 0 expected record"
        fields = expected_records[0]._fields
        not_found = []
        equals = []
        for expected in expected_records:
            for record in records:
                for field, value in list(expected._asdict().items()):
                    if not getattr(record, field) == value:
                        break
                else:
                    records.remove(record)
                    equals.append(record)
                    break
            else:
                not_found.append(expected)
        message = []
        for record in equals:
            # same records
            message.append(
                ' ✓ {}({})'.format(
                    model_name,
                    ', '.join('%s: %s' % (field, getattr(record, field)) for
                              field in fields)
                )
            )
        for expected in not_found:
            # missing records
            message.append(
                ' - {}({})'.format(
                    model_name,
                    ', '.join('%s: %s' % (k, v) for
                              k, v in list(expected._asdict().items()))
                )
            )
        for record in records:
            # extra records
            message.append(
                ' + {}({})'.format(
                    model_name,
                    ', '.join('%s: %s' % (field, getattr(record, field)) for
                              field in fields)
                )
            )
        if not_found or records:
            raise AssertionError('Records do not match:\n\n{}'.format(
                '\n'.join(message)
            ))


class MagentoSyncTestCase(MagentoTestCase):

    @classmethod
    def setUpClass(cls):
        super(MagentoSyncTestCase, cls).setUpClass()
        # Mute logging of notifications about new checkpoints
        with mute_logger(
                'odoo.addons.mail.models.mail_mail',
                'odoo.models.unlink',
                'odoo.tests'):
            with recorder.use_cassette('metadata'):
                cls.backend.synchronize_metadata()

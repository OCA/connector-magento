# Copyright 2013-2019 Camptocamp SA
# Copyright 2020 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

# pylint: disable=missing-manifest-dependency
# disable warning on 'vcr' missing in manifest: this is only a dependency for
# dev/tests

"""
Magento2 version of the helpers from tests/common.py
"""

from os.path import dirname, join
from vcr import VCR

from odoo.tools import mute_logger
from ..common import MagentoTestCase


recorder = VCR(
    cassette_library_dir=join(dirname(__file__), 'fixtures/cassettes'),
    decode_compressed_response=True,
    filter_headers=['Authorization'],
    path_transformer=VCR.ensure_suffix('.yaml'),
    record_mode='once',
)


class Magento2TestCase(MagentoTestCase):
    @classmethod
    def setUpClass(cls):
        super(Magento2TestCase, cls).setUpClass()
        cls.recorder = recorder
        cls.backend.write({
            'version': '2.0',
            'token': 'm59qseoztake3xm1zcvkiv8qnuj09da0',
        })


class Magento2SyncTestCase(Magento2TestCase):
    @classmethod
    def setUpClass(cls):
        super(Magento2SyncTestCase, cls).setUpClass()
        with mute_logger(
                'odoo.addons.mail.models.mail_mail',
                'odoo.models.unlink',
                'odoo.tests'):
            with recorder.use_cassette('metadata'):
                cls.backend.synchronize_metadata()

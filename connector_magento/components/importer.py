# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""

Importers for Magento.

An import can be skipped if the last sync date is more recent than
the last update in Magento.

They should call the ``bind`` method if the binder even if the records
are already bound, to update the last sync date.

"""

import logging
from odoo import fields, _
from odoo.addons.component.core import AbstractComponent, Component
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.queue_job.exception import NothingToDoJob

_logger = logging.getLogger(__name__)


class MagentoImporter(AbstractComponent):
    """ Base importer for Magento """

    _name = 'magento.importer'
    _inherit = ['base.importer', 'base.magento.connector']
    _usage = 'record.importer'

    def __init__(self, work_context):
        super(MagentoImporter, self).__init__(work_context)
        self.external_id = None
        self.magento_record = None

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.external_id`` """
        return self.backend_adapter.read(self.external_id)

    def _before_import(self):
        """ Hook called before the import, when we have the Magento
        data"""

    def _is_uptodate(self, binding):
        """Return True if the import should be skipped because
        it is already up-to-date in OpenERP"""
        assert self.magento_record
        if not self.magento_record.get('updated_at'):
            return  # no update date on Magento, always import it.
        if not binding:
            return  # it does not exist so it should not be skipped
        sync = binding.sync_date
        if not sync:
            return
        from_string = fields.Datetime.from_string
        sync_date = from_string(sync)
        magento_date = from_string(self.magento_record['updated_at'])
        # if the last synchronization date is greater than the last
        # update in magento, we skip the import.
        # Important: at the beginning of the exporters flows, we have to
        # check if the magento_date is more recent than the sync_date
        # and if so, schedule a new import. If we don't do that, we'll
        # miss changes done in Magento
        return magento_date < sync_date

    def _import_dependency(self, external_id, binding_model,
                           importer=None, always=False):
        """ Import a dependency.

        The importer class is a class or subclass of
        :class:`MagentoImporter`. A specific class can be defined.

        :param external_id: id of the related binding to import
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param importer_component: component to use for import
                                   By default: 'importer'
        :type importer_component: Component
        :param always: if True, the record is updated even if it already
                       exists, note that it is still skipped if it has
                       not been modified on Magento since the last
                       update. When False, it will import it only when
                       it does not yet exist.
        :type always: boolean
        """
        if not external_id:
            return
        binder = self.binder_for(binding_model)
        if always or not binder.to_internal(external_id):
            if importer is None:
                importer = self.component(usage='record.importer',
                                          model_name=binding_model)
            try:
                importer.run(external_id)
            except NothingToDoJob:
                _logger.info(
                    'Dependency import of %s(%s) has been ignored.',
                    binding_model._name, external_id
                )

    def _import_dependencies(self):
        """ Import the dependencies for the record

        Import of dependencies can be done manually or by calling
        :meth:`_import_dependency` for each dependency.
        """
        return

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~odoo.addons.connector.components.mapper.MapRecord`

        """
        return self.mapper.map_record(self.magento_record)

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid.

        Raise `InvalidDataError`
        """
        return

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        return

    def _get_binding(self):
        return self.binder.to_internal(self.external_id)

    def _create_data(self, map_record, **kwargs):
        return map_record.values(for_create=True, **kwargs)

    def _create(self, data):
        """ Create the OpenERP record """
        # special check on data before import
        self._validate_data(data)
        model = self.model.with_context(connector_no_export=True)
        binding = model.create(data)
        _logger.debug('%d created from magento %s', binding, self.external_id)
        return binding

    def _update_data(self, map_record, **kwargs):
        return map_record.values(**kwargs)

    def _update(self, binding, data):
        """ Update an OpenERP record """
        # special check on data before import
        self._validate_data(data)
        binding.with_context(connector_no_export=True).write(data)
        _logger.debug('%d updated from magento %s', binding, self.external_id)
        return

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    def run(self, external_id, force=False, data=None):
        """ Run the synchronization

        :param external_id: identifier of the record on Magento
        """
        self.external_id = external_id
        lock_name = 'import({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.work.model_name,
            external_id,
        )

        if data:
            self.magento_record = data
        else:
            try:
                self.magento_record = self._get_magento_data()
            except IDMissingInBackend:
                return _('Record does no longer exist in Magento')

        skip = self._must_skip()    # pylint: disable=assignment-from-none
        if skip:
            return skip

        binding = self._get_binding()

        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')

        # Keep a lock on this import until the transaction is committed
        # The lock is kept since we have detected that the informations
        # will be updated into Odoo
        self.advisory_lock_or_retry(lock_name)
        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record)
            self._update(binding, record)
        else:
            record = self._create_data(map_record)
            binding = self._create(record)

        self.binder.bind(self.external_id, binding)

        self._after_import(binding)


class BatchImporter(AbstractComponent):
    """ The role of a BatchImporter is to search for a list of
    items to import, then it can either import them directly or delay
    the import of each item separately.
    """

    _name = 'magento.batch.importer'
    _inherit = ['base.importer', 'base.magento.connector']
    _usage = 'batch.importer'

    def run(self, filters=None):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search(filters)
        for record_id in record_ids:
            self._import_record(record_id)

    def _import_record(self, external_id):
        """ Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
        raise NotImplementedError


class DirectBatchImporter(AbstractComponent):
    """ Import the records directly, without delaying the jobs. """

    _name = 'magento.direct.batch.importer'
    _inherit = 'magento.batch.importer'

    def _import_record(self, external_id):
        """ Import the record directly """
        self.model.import_record(self.backend_record, external_id)


class DelayedBatchImporter(AbstractComponent):
    """ Delay import of the records """

    _name = 'magento.delayed.batch.importer'
    _inherit = 'magento.batch.importer'

    def _import_record(self, external_id, job_options=None, **kwargs):
        """ Delay the import of the records"""
        delayable = self.model.with_delay(**job_options or {})
        delayable.import_record(self.backend_record, external_id, **kwargs)


class SimpleRecordImporter(Component):
    """ Import one Magento Website """

    _name = 'magento.simple.record.importer'
    _inherit = 'magento.importer'
    _apply_on = [
        'magento.res.partner.category',
    ]


class TranslationImporter(Component):
    """ Import translations for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products and products' categories importers.
    """

    _name = 'magento.translation.importer'
    _inherit = 'magento.importer'
    _usage = 'translation.importer'

    def _get_magento_data(self, storeview=None):
        """ Return the raw Magento data for ``self.external_id`` """
        if storeview is None:
            storeview_id = None
        elif self.collection.version == '2.0':
            storeview_id = storeview.code
        else:
            storeview_id = storeview.id
        return self.backend_adapter.read(self.external_id, storeview_id)

    def run(self, external_id, binding, mapper=None):
        self.external_id = external_id
        default_lang = self.backend_record.default_lang_id
        storeviews = self.env['magento.storeview'].search(
            [('backend_id', '=', self.backend_record.id),
             ('lang_id', '!=', False), ('lang_id', '!=', default_lang.id)])
        if not storeviews:
            return
        lang2storeview = dict(
            (storeview.lang_id, storeview) for storeview in storeviews)

        # find the translatable fields of the model
        fields = self.model.fields_get()
        translatable_fields = [field for field, attrs in list(fields.items())
                               if attrs.get('translate')]

        if mapper is None:
            mapper = self.mapper
        else:
            mapper = self.component_by_name(mapper)

        for storeview in lang2storeview.values():
            lang_record = self._get_magento_data(storeview)
            map_record = mapper.map_record(lang_record)
            record = map_record.values()

            data = dict((field, value) for field, value in list(record.items())
                        if field in translatable_fields)

            binding.with_context(connector_no_export=True,
                                 lang=storeview.lang_id.code).write(data)

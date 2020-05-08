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

from ..common import MagentoTestCase


recorder = VCR(
    cassette_library_dir=join(dirname(__file__), 'fixtures/cassettes'),
    decode_compressed_response=True,
    filter_headers=['Authorization'],
    path_transformer=VCR.ensure_suffix('.yaml'),
    record_mode='once',
)


class Magento2TestCase(MagentoTestCase):
    def setUp(self):
        super(Magento2TestCase, self).setUp()
        self.recorder = recorder
        self.backend.write({
            'version': '2.0',
            'token': 'm59qseoztake3xm1zcvkiv8qnuj09da0',
        })


class Magento2SyncTestCase(Magento2TestCase):
    def setUp(self):
        super(Magento2SyncTestCase, self).setUp()
        with recorder.use_cassette('metadata'):
            self.backend.synchronize_metadata()

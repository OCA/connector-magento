# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Chafique DELLI
#    Copyright 2014 AKRETION SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.magentoerpconnect.tests.test_synchronization import SetUpMagentoSynchronized
from openerp.addons.magentoerpconnect.unit.import_synchronizer import import_record
from openerp.addons.magentoerpconnect_rma.claim import (export_claim_comment,
                                                        export_claim_attachment)
from openerp.addons.magentoerpconnect.tests.common import (mock_api,
                                                           mock_urlopen_image)
from .test_data import magento_rma_responses


class SetUpMagentoWithCrmClaim(SetUpMagentoSynchronized):

    def setUp(self):
        super(SetUpMagentoWithCrmClaim, self).setUp()
        mag_claim_model = self.registry('magento.crm.claim')
        with mock_api(magento_rma_responses):
            with mock_urlopen_image():
                import_record(self.session,
                              'magento.crm.claim',
                              self.backend_id, 18)
        self.mag_claim_ids = mag_claim_model.search(self.cr, self.uid, [
            ('backend_id', '=', self.backend_id),
            ('magento_id', '=', '18'),
            ])
        self.mag_claim = mag_claim_model.browse(self.cr, self.uid,
                                                self.mag_claim_ids[0])


class TestImportMagento(SetUpMagentoWithCrmClaim):
    """
        Test the imports of Claims, Claim Comments and Claim Attachments from a Magento Mock.
    """

    def test_import_claim_with_attachment(self):
        """ Import a Claim: check """
        backend_id = self.backend_id
        #with mock_api(magento_rma_responses):
        #    with mock_urlopen_image():
        #        import_record(self.session, 'magento.crm.claim',
        #                      backend_id, 18)
        #mag_claim_model = self.registry('magento.crm.claim')
        #mag_claim_ids = mag_claim_model.search(self.cr,
        #                               self.uid,
        #                               [('backend_id', '=', backend_id),
        #                                ('magento_id', '=', '18')])

        self.assertEqual(len(self.mag_claim_ids), 1)

        #claim = mag_claim_model.read(self.cr, self.uid, mag_claim_ids[0], ['openerp_id'])
        #claim_id = claim['openerp_id'][0]
        mag_attachment_model = self.registry('magento.claim.attachment')
        mag_attachment_ids = mag_attachment_model.search(
            self.cr, self.uid,
            [('backend_id', '=', backend_id),
             ('res_id', '=', self.mag_claim.openerp_id.id)])

        self.assertEqual(len(mag_attachment_ids), 1)


    def test_import_claim_comment(self):
        """ Import a Claim Comment: check """
        backend_id = self.backend_id
        with mock_api(magento_rma_responses):
            import_record(self.session, 'magento.claim.comment',
                          backend_id, {'created_at': '2014-05-19 14:53:13',
                                       'is_customer': '1',
                                       'message': 'message client',
                                       'rma_comment_id': '68',
                                       'rma_id': '18'})

        mag_comment_model = self.registry('magento.claim.comment')
        mag_comment_ids = mag_comment_model.search(
            self.cr, self.uid,
            [('backend_id', '=', backend_id),
             ('res_id', '=', self.mag_claim.openerp_id.id)])
        self.assertEqual(len(mag_comment_ids), 1)

    def test_import_claim_attachment(self):
        """ Import a Claim Attachment: check """
        backend_id = self.backend_id
        with mock_api(magento_rma_responses):
            import_record(self.session, 'magento.claim.attachment',
                          backend_id, {'content' : '',
                                       'updated_at': '2014-05-19 14:52:14',
                                       'filename': '700b46f82e18b168b2100437da1fc09f',
                                       'is_customer': '1',
                                       'mimetype': 'image/png',
                                       'name': '60.png',
                                       'rma_attachment_id': '60',
                                       'rma_id': '18'})

        mag_attachment_model = self.registry('magento.claim.attachment')
        mag_attachment_ids = mag_attachment_model.search(
            self.cr, self.uid,
            [('backend_id', '=', backend_id),
             ('res_id', '=', self.mag_claim.openerp_id.id),
             ('magento_id', '=', '60')])
        
        self.assertEqual(len(mag_attachment_ids), 1)


class TestExportMagento(SetUpMagentoWithCrmClaim):
    """
        Test the exports of Claim Comments and Claim Attachments to a Magento Mock.
    """

    def test_export_claim_comment(self):
        """ Export a Claim Comment: check """
        response = {
            'rma_comment.create': {'created_at': '2014-05-19 14:51:10',
                                   'is_customer': '0',
                                   'message': '<p>nous allons traiter votre reclamation au plus vite</p>',
                                   'rma_comment_id': '67',
                                   'rma_id': '18'},
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_comment_model = self.registry('magento.claim.comment')
            mail_message_model = self.registry('mail.message')

            comment_id = mail_message_model.create(self.cr, self.uid, {
                'res_id': self.mag_claim.openerp_id.id,
                'body': 'nous allons traiter votre reclamation au plus vite',
                'model': 'crm.claim',
                'type': 'comment',
                'subtype_id': 1,
            })

            mag_comment_id = mag_comment_model.search(self.cr, self.uid, [
                ('backend_id', '=', self.backend_id),
                ('openerp_id', '=', comment_id),
                ])[0]

            export_claim_comment(
                self.session, 'magento.claim.comment', mag_comment_id)

            self.assertEqual(len(calls_done), 1)

            method, infos = calls_done[0]

            self.assertEqual(method, 'rma_comment.create')
            self.assertEqual(infos[0]['rma_id'], '18')
            self.assertEqual(infos[0]['message'], '<p>nous allons traiter votre reclamation au plus vite</p>')

    def test_export_claim_attachment(self):
        """ Export a Claim Attachment: check """
        response = {
            'rma_attachment.create': {'content': 'cG91ciBqYW1lcyBoZWVsZXkob2spCmVycF9zdXBlckBqYW1lc2hlZWxleS5ha3JldGlvbi5jb20KYWRtaW4KbWRwIGFrCgpwb3VyIHN0b3JlIGRpc2NvdW50KG9rKQpodHRwOi8vZXJwLXByb2Quc3RvcmVzLWRpc2NvdW50LXNlcnZpY2VzLmNvbS8gCmFkbWluCm1kcCBPbGkxNDchCgpwb3VyIG91dGlsbGFnZShvaykKb3V0aWxsYWdlLW9ubGluZS5ha3JldGlvbi5jb20KYWRtaW4gCm1kcCBmZGlrNDVFUkRhOAoKcG91ciBhZGFwdG9vIChvaykKdHUgdGUgY29ubmVjdGVzIGF2ZWMgZXJwX3N1cGVyIApzc2ggZXJwX3N1cGVyQGFkYXB0b28uYWtyZXRpb24uY29tIAplbnN1aXRlIHR1IGxhbmNlICJwc3FsIHByb2QgLVUgZXJwX3Byb2QiCmV0IHR1IHLDqWN1cMOocmUgbGUgbW90IGRlIHBhc3NlIApzZWxlY3QgKiBmcm9tIHJlc191c2VyczsKCnBvdXIgc2NlbnR5cwpzc2ggZXJwX3N1cGVyQHNjZW50eXMuYWtyZXRpb24uY29tCmFkbWluCm1kcCBIZXRPb3JueWV1ajAK',
                                      'created_at': '2014-05-19 14:51:48',
                                      'filename': 'f692c41200ce7327a625535827e70a9d',
                                      'is_customer': '0',
                                      'mimetype': '',
                                      'name': 'update_tax',
                                      'rma_attachment_id': '59',
                                      'rma_id': '18'},
        }
        with mock_api(response, key_func=lambda m, a: m) as calls_done:
            mag_attachment_model = self.registry('magento.claim.attachment')
            ir_attachment_model = self.registry('ir.attachment')

            attachment_id = ir_attachment_model.create(self.cr, self.uid, {
                'res_id': self.mag_claim.openerp_id.id,
                'name': 'update_tax',
                'datas_fname': 'update_tax',
                'datas': 'cG91ciBqYW1lcyBoZWVsZXkob2spCmVycF9zdXBlckBqYW1lc2hlZWxleS5ha3JldGlvbi5jb20K\nYWRtaW4KbWRwIGFrCgpwb3VyIHN0b3JlIGRpc2NvdW50KG9rKQpodHRwOi8vZXJwLXByb2Quc3Rv\ncmVzLWRpc2NvdW50LXNlcnZpY2VzLmNvbS8gCmFkbWluCm1kcCBPbGkxNDchCgpwb3VyIG91dGls\nbGFnZShvaykKb3V0aWxsYWdlLW9ubGluZS5ha3JldGlvbi5jb20KYWRtaW4gCm1kcCBmZGlrNDVF\nUkRhOAoKcG91ciBhZGFwdG9vIChvaykKdHUgdGUgY29ubmVjdGVzIGF2ZWMgZXJwX3N1cGVyIApz\nc2ggZXJwX3N1cGVyQGFkYXB0b28uYWtyZXRpb24uY29tIAplbnN1aXRlIHR1IGxhbmNlICJwc3Fs\nIHByb2QgLVUgZXJwX3Byb2QiCmV0IHR1IHLDqWN1cMOocmUgbGUgbW90IGRlIHBhc3NlIApzZWxl\nY3QgKiBmcm9tIHJlc191c2VyczsKCnBvdXIgc2NlbnR5cwpzc2ggZXJwX3N1cGVyQHNjZW50eXMu\nYWtyZXRpb24uY29tCmFkbWluCm1kcCBIZXRPb3JueWV1ajAK\n',
                'res_model': 'crm.claim',
                'type': 'binary',
            })

            mag_attachment_id = mag_attachment_model.search(self.cr, self.uid, [
                ('backend_id', '=', self.backend_id),
                ('openerp_id', '=', attachment_id),
                ])[0]

            export_claim_attachment(
                self.session, 'magento.claim.attachment', mag_attachment_id)

            self.assertEqual(len(calls_done), 1)

            method, infos = calls_done[0]

            self.assertEqual(method, 'rma_attachment.create')
            self.assertEqual(infos[0]['name'], 'update_tax')
            self.assertEqual(infos[0]['rma_id'], '18')

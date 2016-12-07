# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ddt
import webob

from nova.api.openstack import api_version_request
from nova.api.openstack.compute import extension_info
from nova.api.openstack.compute import quota_classes as quota_classes_v21
from nova import exception
from nova import test
from nova.tests.unit.api.openstack import fakes


@ddt.ddt
class QuotaClassSetsTestV21(test.TestCase):
    validation_error = exception.ValidationError

    def setUp(self):
        super(QuotaClassSetsTestV21, self).setUp()
        self.req = fakes.HTTPRequest.blank('')
        ext_info = extension_info.LoadedExtensionInfo()
        self.controller = quota_classes_v21.QuotaClassSetsController(
            extension_info=ext_info)
        self.class_name = 'test_class'

    def _get_quota_class_set(self, req, update_data=None):
        data = {
            'metadata_items': 128,
            'ram': 51200,
            'instances': 10,
            'injected_files': 5,
            'cores': 20,
            'injected_file_content_bytes': 10240,
            'key_pairs': 100,
            'injected_file_path_bytes': 255,
        }
        if api_version_request.is_supported(req, max_version='2.49'):
            data['floating_ips'] = 10
            data['fixed_ips'] = -1
            data['security_groups'] = 10
            data['security_group_rules'] = 20
        if api_version_request.is_supported(req, min_version='2.50'):
            data['server_groups'] = 10
            data['server_group_members'] = 10
        if api_version_request.is_supported(req, min_version='2.54'):
            data['local_gb'] = 150
        if update_data:
            data.update(update_data)
        return {'quota_class_set': data}

    @ddt.data('2.1', '2.35', '2.36', '2.49', '2.50', '2.53', '2.54')
    def test_quotas_show(self, microversion):
        req = fakes.HTTPRequest.blank('', version=microversion)

        res_dict = self.controller.show(req, self.class_name)

        expected = self._get_quota_class_set(req, {'id': self.class_name})
        self.assertEqual(expected, res_dict)

    @ddt.data('2.1', '2.35', '2.36', '2.49', '2.50', '2.53', '2.54')
    def test_quotas_update(self, microversion):
        req = fakes.HTTPRequest.blank('', version=microversion)
        request_body = self._get_quota_class_set(req)

        res_dict = self.controller.update(
            req, self.class_name, body=request_body)

        expected_body = self._get_quota_class_set(req)
        self.assertEqual(expected_body, res_dict)

    def test_quotas_update_with_empty_body(self):
        body = {}
        self.assertRaises(self.validation_error, self.controller.update,
                          self.req, 'test_class', body=body)

    def test_quotas_update_with_invalid_integer(self):
        body = {'quota_class_set': {'instances': 2 ** 31 + 1}}
        self.assertRaises(self.validation_error, self.controller.update,
                          self.req, 'test_class', body=body)

    def test_quotas_update_with_long_quota_class_name(self):
        name = 'a' * 256
        body = {'quota_class_set': {'instances': 10}}
        self.assertRaises(webob.exc.HTTPBadRequest, self.controller.update,
                          self.req, name, body=body)

    def test_quotas_update_with_non_integer(self):
        body = {'quota_class_set': {'instances': "abc"}}
        self.assertRaises(self.validation_error, self.controller.update,
                          self.req, 'test_class', body=body)

        body = {'quota_class_set': {'instances': 50.5}}
        self.assertRaises(self.validation_error, self.controller.update,
                          self.req, 'test_class', body=body)

        body = {'quota_class_set': {
                'instances': u'\u30aa\u30fc\u30d7\u30f3'}}
        self.assertRaises(self.validation_error, self.controller.update,
                          self.req, 'test_class', body=body)

    def test_quotas_update_with_unsupported_quota_class(self):
        body = {'quota_class_set': {'instances': 50, 'cores': 50,
                                    'ram': 51200, 'unsupported': 12}}
        self.assertRaises(self.validation_error, self.controller.update,
                          self.req, 'test_class', body=body)


class QuotaClassesPolicyEnforcementV21(test.NoDBTestCase):

    def setUp(self):
        super(QuotaClassesPolicyEnforcementV21, self).setUp()
        ext_info = extension_info.LoadedExtensionInfo()
        self.controller = quota_classes_v21.QuotaClassSetsController(
            extension_info=ext_info)
        self.req = fakes.HTTPRequest.blank('')

    def test_show_policy_failed(self):
        rule_name = "os_compute_api:os-quota-class-sets:show"
        self.policy.set_rules({rule_name: "quota_class:non_fake"})
        exc = self.assertRaises(
            exception.PolicyNotAuthorized,
            self.controller.show, self.req, fakes.FAKE_UUID)
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % rule_name,
            exc.format_message())

    def test_update_policy_failed(self):
        rule_name = "os_compute_api:os-quota-class-sets:update"
        self.policy.set_rules({rule_name: "quota_class:non_fake"})
        exc = self.assertRaises(
            exception.PolicyNotAuthorized,
            self.controller.update, self.req, fakes.FAKE_UUID,
            body={'quota_class_set': {}})
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % rule_name,
            exc.format_message())

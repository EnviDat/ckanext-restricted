# coding: utf8

from __future__ import unicode_literals
import ckan.authz as authz
import ckan.logic.auth as logic_auth
import ckan.plugins.toolkit as toolkit
from ckanext.restricted import logic

from logging import getLogger
log = getLogger(__name__)


@toolkit.auth_allow_anonymous_access
def restricted_resource_show(context, data_dict=None):
    if context.get('ignore_auth'):
        return {'success': True}

    # Ensure user who can edit the package can see the resource
    resource = data_dict.get('resource', context.get('resource', {}))
    if not resource:
        resource = logic_auth.get_resource_object(context, data_dict)
    if type(resource) is not dict:
        resource = resource.as_dict()

    # if user has rights to edit package return true
    if authz.is_authorized(
            'package_update', context,
            {'id': resource.get('package_id')}).get('success'):
        return {'success': True}

    user_name = logic.restricted_get_username_from_context(context)

    package = data_dict.get('package', {})
    if not package:
        model = context['model']
        package = model.Package.get(resource.get('package_id'))
        package = package.as_dict()

    # if resource is not in the list, resource was deleted
    # let CKAN auth check access if that is the case (it will return not found)
    package_resources = [res.get("id") for res in package.get('resources', [])]
    resource_id = resource.get('id')
    if resource_id not in package_resources:
        log.debug("restricted_resource_show: resource {0} not in package list".format(resource_id))
        return {'success': True}

    return (logic.restricted_check_user_resource_access(
        user_name, resource, package))

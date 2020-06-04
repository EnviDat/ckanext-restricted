# coding: utf8

from __future__ import unicode_literals

from ckan import authz
from ckan.logic import (
    get_action,
    side_effect_free,
    ValidationError,
)
from ckan.logic.action.get import resource_search

from ckanext.restricted import logic

import json

from logging import getLogger


log = getLogger(__name__)


@side_effect_free
def restricted_resource_search(context, data_dict):
    resource_search_result = resource_search(context, data_dict)

    restricted_resource_search_result = {}

    for key, value in resource_search_result.items():
        if key == 'results':
            # restricted_resource_search_result[key] = \
            #     _restricted_resource_list_url(context, value)
            restricted_resource_search_result[key] = \
                _restricted_resource_list_hide_fields(context, value)
        else:
            restricted_resource_search_result[key] = value

    return restricted_resource_search_result


@side_effect_free
def restricted_check_access(context, data_dict):

    package_id = data_dict.get('package_id', False)
    resource_id = data_dict.get('resource_id', False)

    user_name = logic.restricted_get_username_from_context(context)

    if not package_id:
        raise ValidationError('Missing package_id')
    if not resource_id:
        raise ValidationError('Missing resource_id')

    log.debug("action.restricted_check_access: user_name = " + str(user_name))

    log.debug("checking package " + str(package_id))
    package_dict = get_action('package_show')(dict(context, return_type='dict'), {'id': package_id})
    log.debug("checking resource")
    resource_dict = get_action('resource_show')(dict(context, return_type='dict'), {'id': resource_id})

    return logic.restricted_check_user_resource_access(user_name, resource_dict, package_dict)


def _restricted_resource_list_hide_fields(context, resource_list):
    restricted_resources_list = []
    for resource in resource_list:
        # copy original resource
        restricted_resource = dict(resource)

        # get the restricted fields
        restricted_dict = logic.restricted_get_restricted_dict(restricted_resource)

        # hide other fields in restricted to everyone but dataset owner(s)
        if not authz.is_authorized(
                'package_update', context, {'id': resource.get('package_id')}
                ).get('success'):

            user_name = logic.restricted_get_username_from_context(context)

            # hide partially other allowed user_names (keep own)
            allowed_users = []
            for user in restricted_dict.get('allowed_users'):
                if len(user.strip()) > 0:
                    if user_name == user:
                        allowed_users.append(user_name)
                    else:
                        allowed_users.append(user[0:3] + '*****' + user[-2:])

            new_restricted = json.dumps({
                'level': restricted_dict.get("level"),
                'allowed_users': ','.join(allowed_users)})
            extras_restricted = resource.get('extras', {}).get('restricted', {})
            if (extras_restricted):
                restricted_resource['extras']['restricted'] = new_restricted

            field_restricted_field = resource.get('restricted', {})
            if (field_restricted_field):
                restricted_resource['restricted'] = new_restricted

        restricted_resources_list += [restricted_resource]
    return restricted_resources_list

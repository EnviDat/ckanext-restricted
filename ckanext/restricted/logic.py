import logging

import ckan.logic as logic

import json


logger = logging.getLogger(__name__)


def restricted_check_user_resource_access(user, resource_dict, package_dict):
    restricted_level = 'public'
    allowed_users  = []

    # check in resource_dict
    if resource_dict:
        extras = resource_dict.get('extras',{})
        restricted = resource_dict.get('restricted', extras.get('restricted', {}))
        if not isinstance(restricted, dict):
            restricted = json.loads(restricted)
        restricted_level = restricted.get('level', 'public')
        allowed_users = restricted.get('allowed_users', "").split(',')

    # Public resources (DEFAULT)
    if not restricted_level or restricted_level == 'public':
        return {'success': True }

    # Registered user
    if not user:
        return {'success': False, 'msg': "Resource access restricted to registered users" }
    else:
        if restricted_level == 'registered' or not restricted_level:
            return {'success': True }

    # Since we have a user, check if it is in the allowed list
    if user in allowed_users:
        return {'success': True }

    # Get organization list
    user_organization_dict = {}

    context = {'user': user}
    data_dict = {'permission': 'read'}

    for org in logic.get_action('organization_list_for_user')(context, data_dict):
        name = org.get('name', '')
        id = org.get('id', '')
        if name and id:
            user_organization_dict[id] =  name

    # Any Organization Members (Trusted Users)
    if not user_organization_dict:
        return {'success': False, 'msg': "Resource access restricted to members of an organization" }
    if restricted == 'any_organization':
        return {'success': True }

    pkg_organization_id = package_dict.get('owner_org', '')

    # Same Organization Members
    if restricted_level == 'same_organization':
        if pkg_organization_id in user_organization_dict.keys():
            return {'success': True }

    return {'success': False, 'msg': "Resource access restricted to same organization (" + pkg_organization_id + ") members" }


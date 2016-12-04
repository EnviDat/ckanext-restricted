import logging

import ckan.logic as logic
from ckan.common import c

logger = logging.getLogger(__name__)


def restricted_check_user_resource_access(user, resource_dict, package_dict):
    restricted = 'public'

    # check in resource_dict
    if resource_dict:
        extras = resource_dict.get('extras',{})
        restricted = resource_dict.get('restricted', extras.get('restricted', None))

    # Public resources (DEFAULT)
    if not restricted or restricted == 'public':
        return {'success': True }

    # Registered user
    if not user:
        return {'success': False, 'msg': "Resource access restricted to registered users" }
    else:
        if restricted == 'registered' or not restricted:
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
    if restricted == 'same_organization':
        if pkg_organization_id in user_organization_dict.keys():
            return {'success': True }

    return {'success': False, 'msg': "Resource access restricted to " + pkg_organization_name + " members" }


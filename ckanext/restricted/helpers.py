import logging

import ckan.logic as logic
from ckan.common import c

logger = logging.getLogger(__name__)

def restricted_check_user_resources_access(user, restricted = 'registered'):

    # Public resources
    if restricted == 'public':
        return True
    # Registered user (DEFAULT)
    if not user:
        return False
    else:
        if restricted == 'registered' or not restricted:
            return True

    # Get organization list
    user_organization_list = []

    context = {'user': user}
    data_dict = {'permission': 'read'}

    for org in logic.get_action('organization_list_for_user')(context, data_dict):
        name = org.get('name', '')
        if name:
            user_organization_list += [name]

    # Any Organization Members (Trusted Users)
    if not user_organization_list:
        return False
    if restricted == 'any_organization':
        return True
    pkg_organization_name = c.pkg_dict.get('organization', {'name':' '}).get('name', ' ')

    # Same Organization Members
    if restricted == 'same_organization':
        if pkg_organization_name in user_organization_list:
            return True

    return False


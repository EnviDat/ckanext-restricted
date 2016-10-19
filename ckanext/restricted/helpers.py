import logging
from ckan.common import c

logger = logging.getLogger(__name__)

def restricted_check_user_resources_access(user, restricted = 'registered'):
    import ckan.lib.helpers as h

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
    for org in h.organizations_available(permission='read'):
        name = org.get('name', '')
        if name:
            user_organization_list += [name]
    logger.debug ('restricted_check_user_resources_access: organizations for ' + str(user) + ': ' + ",  ".join(user_organization_list))

    # Any Organization Members (Trusted Users)
    if not user_organization_list:
        return False
    if restricted == 'any_organization':
        return True
    pkg_organization_name = c.pkg_dict.get('organization', {'name':' '}).get('name', ' ')
    logger.debug('restricted_check_user_resources_access: package organization ' + pkg_organization_name)

    # Same Organization Members
    if restricted == 'same_organization':
        if pkg_organization_name in user_organization_list:
            return True

    return False


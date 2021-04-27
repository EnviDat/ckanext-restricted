# coding: utf8
from ckan import model
from ckan.common import c
from ckan.plugins import toolkit

from logging import getLogger

from six import text_type


log = getLogger(__name__)


def restricted_get_user_id():
    return str(c.user)


def get_admin_emails(org_id=None, package_id=None):
    if package_id and not org_id:
        package = toolkit.get_action('package_show')({'ignore_auth': True}, {'id': package_id})
        org_id = package['owner_org']

    org = toolkit.get_action('organization_show')(
        {'ignore_auth': True}, {'id': org_id})
    users = [model.User.by_name(text_type(user['name'])) for user in org['users']]

    users_to_show = []
    for user in users:

        # Filter out sysadmins
        if user.sysadmin:
            log.error('skipping sysadmin')
            continue

        # Filter users without emails
        if not user.email:
            continue

        # Filter inactive users
        if not user.active:
            continue

        # Filter non admin or editors
        user_orgs = toolkit.get_action('organization_list_for_user')(
                {'ignore_auth': True}, {'id': user.id})

        if not user_orgs:
            continue

        for user_org in user_orgs:
            if (user_org['id'] == org_id and
                    user_org['capacity'] in ['admin', 'editor']):
                users_to_show.append(user)

    # Fallback to sysadmin
    if len(users_to_show) == 0:
        sysadmins = model.Session.query(model.User).filter(model.User.sysadmin==True).all()
        if len(sysadmins) == 0:
            return [] # TODO this will cause an error on the form

        return [{'value': sysadmins[0].email, 'text': sysadmins[0].email}]

    emails = [{'value': str(user.email), 'text': str(user.email)} for user in users_to_show]

    return emails

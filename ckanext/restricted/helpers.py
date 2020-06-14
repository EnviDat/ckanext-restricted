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
    emails = [{'value': str(user.email), 'text': str(user.email)} for user in users]

    return emails

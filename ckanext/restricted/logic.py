# coding: utf8

from __future__ import unicode_literals
import ckan.authz as authz
from ckan.common import _

from ckan.lib.base import render_jinja2
import ckan.lib.mailer as mailer
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import json

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

from logging import getLogger

log = getLogger(__name__)


def restricted_get_username_from_context(context):
    auth_user_obj = context.get('auth_user_obj', None)
    user_name = ''
    if auth_user_obj:
        user_name = auth_user_obj.as_dict().get('name', '')
    else:
        if authz.get_user_id_for_username(context.get('user'), allow_none=True):
            user_name = context.get('user', '')
    return user_name


def restricted_get_restricted_dict(resource_dict):
    restricted_dict = {'level': 'public', 'allowed_users': []}

    # the ckan plugins ckanext-scheming and ckanext-composite
    # change the structure of the resource dict and the nature of how
    # to access our restricted field values
    if resource_dict:
        # the dict might exist as a child inside the extras dict
        extras = resource_dict.get('extras', {})
        # or the dict might exist as a direct descendant of the resource dict
        restricted = resource_dict.get('restricted', extras.get('restricted', {}))
        if not isinstance(restricted, dict):
            # if the restricted property does exist, but not as a dict,
            # we may need to parse it as a JSON string to gain access to the values.
            # as is the case when making composite fields
            try:
                restricted = json.loads(restricted)
            except ValueError:
                restricted = {}

        if restricted:
            restricted_level = restricted.get('level', 'public')
            allowed_users = restricted.get('allowed_users', '')
            if not isinstance(allowed_users, list):
                allowed_users = allowed_users.split(',')
            restricted_dict = {
                'level': restricted_level,
                'allowed_users': allowed_users}

    return restricted_dict


def restricted_check_user_resource_access(user, resource_dict, package_dict):
    restricted_dict = restricted_get_restricted_dict(resource_dict)

    restricted_level = restricted_dict.get('level', 'public')
    allowed_users = restricted_dict.get('allowed_users', [])

    # Public resources (DEFAULT)
    if not restricted_level or restricted_level == 'public':
        return {'success': True}

    # Registered user
    if not user:
        return {
            'success': False,
            'msg': 'Resource access restricted to registered users'}
    else:
        if restricted_level == 'registered' or not restricted_level:
            return {'success': True}

    # Since we have a user, check if it is in the allowed list
    if user in allowed_users:
        return {'success': True}
    elif restricted_level == 'only_allowed_users':
        return {
            'success': False,
            'msg': 'Resource access restricted to allowed users only'}

    # Get organization list
    user_organization_dict = {}

    context = {'user': user}
    data_dict = {'permission': 'read'}

    for org in logic.get_action('organization_list_for_user')(context, data_dict):
        name = org.get('name', '')
        id = org.get('id', '')
        if name and id:
            user_organization_dict[id] = name

    # Any Organization Members (Trusted Users)
    if not user_organization_dict:
        return {
            'success': False,
            'msg': 'Resource access restricted to members of an organization'}

    if restricted_level == 'any_organization':
        return {'success': True}

    pkg_organization_id = package_dict.get('owner_org', '')

    # Same Organization Members
    if restricted_level == 'same_organization':
        if pkg_organization_id in user_organization_dict.keys():
            return {'success': True}

    return {
        'success': False,
        'msg': ('Resource access restricted to same '
                'organization ({}) members').format(pkg_organization_id)}

def restricted_mail_allowed_user(user_id, resource):
    log.debug('restricted_mail_allowed_user: Notifying "{}"'.format(user_id))
    try:
        # Get user information
        context = {}
        context['ignore_auth'] = True
        context['keep_email'] = True
        user = toolkit.get_action('user_show')(context, {'id': user_id})
        user_email = user['email']
        user_name = user.get('display_name', user['name'])
        resource_name = resource.get('name', resource['id'])

        # maybe check user[activity_streams_email_notifications]==True

        mail_body = restricted_allowed_user_mail_body(user, resource)
        mail_subject = _('Access granted to resource {}').format(resource_name)

        # Send mail to user
        mailer.mail_recipient(user_name, user_email, mail_subject, mail_body)

        # Send copy to admin
        mailer.mail_recipient(
            'CKAN Admin', config.get('email_to'),
            'Fwd: {}'.format(mail_subject), mail_body)

    except Exception as e:
        log.warning(('restricted_mail_allowed_user: '
                     'Failed to send mail to "{0}": {1}').format(user_id,e))


def restricted_allowed_user_mail_body(user, resource):
    resource_link = toolkit.url_for(
        controller='package', action='resource_read',
        id=resource.get('package_id'), resource_id=resource.get('id'))

    extra_vars = {
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'user_name': user.get('display_name', user['name']),
        'resource_name': resource.get('name', resource['id']),
        'resource_link': config.get('ckan.site_url') + resource_link,
        'resource_url': resource.get('url')}

    return render_jinja2(
        'restricted/emails/restricted_user_allowed.txt', extra_vars)

def restricted_notify_allowed_users(previous_value, updated_resource):

    def _safe_json_loads(json_string, default={}):
        try:
            return json.loads(json_string)
        except Exception:
            return default

    previous_restricted = _safe_json_loads(previous_value)
    updated_restricted = _safe_json_loads(updated_resource.get('restricted', ''))

    # compare restricted users_allowed values
    updated_allowed_users = set(updated_restricted.get('allowed_users', '').split(','))
    if updated_allowed_users:
        previous_allowed_users = previous_restricted.get('allowed_users', '').split(',')
        for user_id in updated_allowed_users:
            if user_id not in previous_allowed_users:
                restricted_mail_allowed_user(user_id, updated_resource)

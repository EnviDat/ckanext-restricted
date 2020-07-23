# coding: utf8

from __future__ import unicode_literals
import ckan.authz as authz
from ckan.common import _

from ckan.lib.base import render_jinja2
from ckan.lib.mailer import mail_recipient
from ckan.lib.mailer import MailerException
import ckan.logic
import ckan.plugins as p
from ckan.logic.action.create import user_create
from ckan.logic.action.get import package_search
from ckan.logic.action.get import package_show
from ckan.logic.action.get import resource_search
from ckan.logic.action.get import resource_view_list
from ckan.logic import side_effect_free
from ckanext.restricted import auth
from ckanext.restricted import logic
import json

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

from logging import getLogger
log = getLogger(__name__)


_get_or_bust = ckan.logic.get_or_bust

NotFound = ckan.logic.NotFound


def restricted_user_create_and_notify(context, data_dict):

    def body_from_user_dict(user_dict):
        body = ''
        for key, value in user_dict.items():
            body += '* {0}: {1}\n'.format(
                key.upper(), value if isinstance(value, str) else str(value))
        return body

    user_dict = user_create(context, data_dict)

    # Send your email, check ckan.lib.mailer for params
    try:
        name = _('CKAN System Administrator')
        email = config.get('email_to')
        if not email:
            raise MailerException('Missing "email-to" in config')

        subject = _('New Registration: {0} ({1})').format(
            user_dict.get('name', _(u'new user')), user_dict.get('email'))

        extra_vars = {
            'site_title': config.get('ckan.site_title'),
            'site_url': config.get('ckan.site_url'),
            'user_info': body_from_user_dict(user_dict)}

        body = render_jinja2(
            'restricted/emails/restricted_user_registered.txt', extra_vars)

        mail_recipient(name, email, subject, body)

    except MailerException as mailer_exception:
        log.error('Cannot send mail after registration')
        log.error(mailer_exception)

    return (user_dict)


@side_effect_free
def restricted_resource_view_list(context, data_dict):
    model = context['model']
    id = _get_or_bust(data_dict, 'id')
    resource = model.Resource.get(id)
    if not resource:
        raise NotFound
    authorized = auth.restricted_resource_show(
        context, {'id': resource.get('id'), 'resource': resource}).get('success', False)
    if not authorized:
        return []
    else:
        return resource_view_list(context, data_dict)


@side_effect_free
def restricted_package_show(context, data_dict):
    hide_inaccessible_resources = p.toolkit.asbool(data_dict.get('hide_inaccessible_resources', False))

    package_metadata = package_show(context, data_dict)

    # Ensure user who can edit can see the resource
    if authz.is_authorized(
            'package_update', context, package_metadata).get('success', False):
        return package_metadata

    # Custom authorization
    if isinstance(package_metadata, dict):
        restricted_package_metadata = dict(package_metadata)
    else:
        restricted_package_metadata = dict(package_metadata.for_json())

    # restricted_package_metadata['resources'] = _restricted_resource_list_url(
    #     context, restricted_package_metadata.get('resources', []))
    resources = restricted_package_metadata.get('resources', [])
    if hide_inaccessible_resources:
        resources = _restricted_resource_list_accessible_by_user(context, resources)
        restricted_package_metadata['num_resources'] = len(resources)
    resources = _restricted_resource_list_hide_fields(context, resources)
    restricted_package_metadata['resources'] = resources

    return (restricted_package_metadata)


def _restricted_resource_list_accessible_by_user(context, resource_list):
    restricted_resources_list = []
    user_name = logic.restricted_get_username_from_context(context)
    for resource in resource_list:
        resource_dict = dict(resource)
        package_dict = dict(id=resource_dict['package_id'])
        if logic.restricted_check_user_resource_access(user_name, resource_dict, package_dict).get('success', False):
            restricted_resources_list.append(resource_dict)

    return restricted_resources_list


@side_effect_free
def restricted_resource_search(context, data_dict):
    hide_inaccessible_resources = p.toolkit.asbool(data_dict.get('hide_inaccessible_resources', False))

    resource_search_result = resource_search(context, data_dict)
    results = resource_search_result['results']
    if hide_inaccessible_resources:
        results = _restricted_resource_list_accessible_by_user(context, results)
    results = _restricted_resource_list_hide_fields(context, results)
    count = len(results)

    resource_search_result.update({'count': count, 'results': results})
    return resource_search_result


@side_effect_free
def restricted_package_search(context, data_dict):
    # pop the param as ckan package search action doesn't support any extra parameters
    hide_inaccessible_resources = p.toolkit.asbool(data_dict.pop('hide_inaccessible_resources', False))
    package_search_result = package_search(context, data_dict)

    restricted_package_search_result = {}

    for key, value in package_search_result.items():
        if key == 'results':
            restricted_package_search_result_list = []
            for package in value:
                restricted_package_search_result_list.append(
                    restricted_package_show(
                        context, {'id': package.get('id'), 'hide_inaccessible_resources': hide_inaccessible_resources})
                )
            restricted_package_search_result[key] = \
                restricted_package_search_result_list
        else:
            restricted_package_search_result[key] = value

    return restricted_package_search_result


@side_effect_free
def restricted_check_access(context, data_dict):

    package_id = data_dict.get('package_id', False)
    resource_id = data_dict.get('resource_id', False)

    user_name = logic.restricted_get_username_from_context(context)

    if not package_id:
        raise ckan.logic.ValidationError('Missing package_id')
    if not resource_id:
        raise ckan.logic.ValidationError('Missing resource_id')

    log.debug("action.restricted_check_access: user_name = " + str(user_name))

    log.debug("checking package " + str(package_id))
    package_dict = ckan.logic.get_action('package_show')(dict(context, return_type='dict'), {'id': package_id})
    log.debug("checking resource")
    resource_dict = ckan.logic.get_action('resource_show')(dict(context, return_type='dict'), {'id': resource_id})

    return logic.restricted_check_user_resource_access(user_name, resource_dict, package_dict)

# def _restricted_resource_list_url(context, resource_list):
#     restricted_resources_list = []
#     for resource in resource_list:
#         authorized = auth.restricted_resource_show(
#             context, {'id': resource.get('id'), 'resource': resource}).get('success', False)
#         restricted_resource = dict(resource)
#         if not authorized:
#             restricted_resource['url'] = _('Not Authorized')
#         restricted_resources_list += [restricted_resource]
#     return restricted_resources_list


def _restricted_resource_list_hide_fields(context, resource_list):
    restricted_resources_list = []
    for resource in resource_list:
        # copy original resource
        restricted_resource = dict(resource)

        # get the restricted fields
        restricted_dict = logic.restricted_get_restricted_dict(restricted_resource)

        # hide fields to unauthorized users
        auth.restricted_resource_show(
            context, {'id': resource.get('id'), 'resource': resource}
        ).get('success', False)

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

            allowed_orgs = []
            for org in restricted_dict.get('allowed_organizations', []):
                if len(org.strip()) > 0:
                    allowed_orgs.append(org)

            new_restricted = json.dumps({
                'level': restricted_dict.get("level"),
                'allowed_users': ','.join(allowed_users),
                'allowed_organizations': ','.join(allowed_orgs)
            })
            extras_restricted = resource.get('extras', {}).get('restricted', {})
            if (extras_restricted):
                restricted_resource['extras']['restricted'] = new_restricted

            field_restricted_field = resource.get('restricted', {})
            if (field_restricted_field):
                restricted_resource['restricted'] = new_restricted

        restricted_resources_list += [restricted_resource]
    return restricted_resources_list

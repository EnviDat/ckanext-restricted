import ckan.authz as authz
from ckan.common import _
from ckan.lib.base import render_jinja2
from ckan.lib.mailer import mail_recipient
from ckan.lib.mailer import MailerException
import ckan.logic
from ckan.logic.action.create import user_create
from ckan.logic.action.get import package_search
from ckan.logic.action.get import package_show
from ckan.logic.action.get import resource_search
from ckan.logic.action.get import resource_view_list
from ckan.logic import side_effect_free
from ckanext.restricted import auth

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
        body = u''
        for key, value in user_dict.items():
            body += u'* {0}: {1}\n'.format(
                key.upper(), value if isinstance(value, str) else str(value))
        return body

    user_dict = user_create(context, data_dict)

    # Send your email, check ckan.lib.mailer for params
    try:
        name = _(u'CKAN System Administrator')
        email = config.get('email_to')
        if not email:
            raise MailerException('Missing "email-to" in config')

        subject = _(u'New Registration: {0} ({1})').format(
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

    restricted_package_metadata['resources'] = _restricted_resource_list_url(
        context, restricted_package_metadata.get('resources', []))

    return (restricted_package_metadata)


@side_effect_free
def restricted_resource_search(context, data_dict):
    resource_search_result = resource_search(context, data_dict)

    restricted_resource_search_result = {}

    for key, value in resource_search_result.items():
        if key == 'results':
            restricted_resource_search_result[key] = \
                _restricted_resource_list_url(context, value)
        else:
            restricted_resource_search_result[key] = value

    return restricted_resource_search_result


@side_effect_free
def restricted_package_search(context, data_dict):
    package_search_result = package_search(context, data_dict)

    restricted_package_search_result = {}

    for key, value in package_search_result.items():
        if key == 'results':
            restricted_package_search_result_list = []
            for package in value:
                restricted_package_search_result_list += [
                    restricted_package_show(context, {'id': package.get('id')})]
            restricted_package_search_result[key] = \
                restricted_package_search_result_list
        else:
            restricted_package_search_result[key] = value

    return restricted_package_search_result


def _restricted_resource_list_url(context, resource_list):
    restricted_resources_list = []
    for resource in resource_list:
        authorized = auth.restricted_resource_show(
            context, {'id': resource.get('id'), 'resource': resource}).get('success', False)
        restricted_resource = dict(resource)
        if not authorized:
            restricted_resource['url'] = 'Not Authorized'
        restricted_resources_list += [restricted_resource]
    return restricted_resources_list

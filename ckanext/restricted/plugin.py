import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.authz as authz

from ckan.lib.mailer import mail_recipient, MailerException
from ckan.logic.action.create import user_create

from ckan.logic import side_effect_free, check_access
from ckan.logic.action.get import package_show, resource_show

from ckanext.restricted import helpers
from ckanext.restricted import logic

from pylons import config
import simplejson as json

from logging import getLogger
log = getLogger(__name__)

def restricted_user_create_and_notify(context, data_dict):

    def body_from_user_dict(user_dict):
         body = '\n'
         for key,value in user_dict.items():
             body += ' \t - '+ str(key.upper()) + ': ' + str(value) + '\n'
         return body
    user_dict = user_create(context, data_dict)

    # Send your email, check ckan.lib.mailer for params
    try:
        name = 'CKAN System Administrator'
        email = config.get('email_to')
        subject = 'New Registration: ' +  user_dict.get('name', 'new user') + ' (' +  user_dict.get('email') + ')'
        body = 'A new user registered, please review the information: ' + body_from_user_dict(user_dict)
        log.debug('Mail sent to ' + email + ', subject: ' + subject)
        mail_recipient(name, email, subject, body)

    except MailerException as mailer_exception:
        log.error("Cannot send mail after registration ")
        log.error(mailer_exception)
        pass

    return (user_dict)

@side_effect_free
def restricted_package_show(context, data_dict):
    package_metadata = package_show(context, data_dict)

    # Ensure user who can edit can see the resource
    if authz.is_authorized('package_update', context, package_metadata).get('success', False):
        return package_metadata

    # Custom authorization
    if (type(package_metadata) == type(dict())):
        restricted_package_metadata = dict(package_metadata)
    else:
        package_metadata_json_str = str(package_metadata.for_json())
        restricted_package_metadata = json.loads(package_metadata_json_str)

    restricted_resources_list = []
    for resource in restricted_package_metadata.get('resources',[]):
        authorized = restricted_resource_show(context, {'id':resource.get('id'), 'resource':resource, 'package': package_metadata }).get('success', False)
        log.debug('restricted_package_show ' + resource.get('id','') + ', ' + resource.get('name','') + ' (' + str(resource.get('restricted', '')) + '): ' + str(authorized))
        restricted_resource = dict(resource)
        log.debug(restricted_resource)
        if not authorized:
            restricted_resource['url'] = 'Not Authorized'
        restricted_resources_list += [restricted_resource]
    restricted_package_metadata['resources'] = restricted_resources_list

    return (restricted_package_metadata)

@toolkit.auth_allow_anonymous_access
def restricted_resource_show(context, data_dict=None):

    # Ensure user who can edit can see the resource
    resource = data_dict.get('resource', context.get('resource',{}))
    if type(resource) is not dict:
        resource = resource.as_dict()

    if authz.is_authorized('package_update', context, {'id': resource.get('package_id')}).get('success'):
        return ({'success': True })

    # custom retricted check
    auth_user_obj = context.get('auth_user_obj', None)
    user_name = ""
    if auth_user_obj:
        user_name = auth_user_obj.as_dict().get('name','')
    else:
        if authz.get_user_id_for_username(context.get('user'), allow_none=True):
            user_name = context.get('user','')
    log.debug("restricted_resource_show: USER:" + user_name)

    package = data_dict.get('package', {})
    if not package:
        model = context['model']
        package = model.Package.get(resource.get('package_id'))
        package = package.as_dict()

    return (logic.restricted_check_user_resource_access(user_name, resource, package))

class RestrictedPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IRoutes, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'restricted')

    # IActions

    def get_actions(self):
        return { 'user_create': restricted_user_create_and_notify,
                 'package_show': restricted_package_show
                 #,'restricted_request_access': restricted_request_access
        }

    # ITemplateHelpers

    def get_helpers(self):
        return { 'restricted_get_user_id':helpers.restricted_get_user_id}

    # IAuthFunctions

    def get_auth_functions(self):
        return { 'resource_show': restricted_resource_show,
                 #'resource_view_list': restricted_resource_show
                 'resource_view_show': restricted_resource_show
               }
    # IRoutes

    def before_map(self, map_):
        map_.connect(
            'restricted_request_access',
            '/dataset/{package_id}/restricted_request_access/{resource_id}',
            controller='ckanext.restricted.controller:RestrictedController',
            action = 'restricted_request_access_form'
        )
        return map_

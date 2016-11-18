import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckan.lib.mailer import mail_recipient, MailerException
from ckan.logic.action.create import user_create

from ckan.logic import side_effect_free, check_access
from ckan.logic.action.get import package_show

#from ckanext.restricted import helpers

from ckanext.restricted import logic

from pylons import config

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

    restricted_resources_list = []
    for resource in package_metadata.get('resources',[]):
        authorized = restricted_resource_show(context, {'id':resource.get('id',''), 'resource':resource }).get('success', False)
        log.debug(" * resource: " + resource.get('name', '') + ", \t restriction=" + resource.get('restricted', '') + ", \t auth=" + str(authorized) )
        restricted_resource = resource
        if not authorized:
            restricted_resource['url'] = 'Not Authorized'
        restricted_resources_list += [restricted_resource]

    package_metadata['resources'] = restricted_resources_list
    return (package_metadata)


@toolkit.auth_allow_anonymous_access
def restricted_resource_show(context, data_dict=None):
    auth_user_obj = context.get('auth_user_obj', None)

    resource = data_dict.get('resource', context.get('resource', {}))
    if type(resource) is not dict:
        resource = resource.as_dict()

    return (logic.restricted_check_user_resource_access(auth_user_obj, resource))

class RestrictedPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'restricted')

    # IActions

    def get_actions(self):
        return { 'user_create': restricted_user_create_and_notify,
                 'package_show': restricted_package_show }

    # ITemplateHelpers

    def get_helpers(self):
        return { } 

    # IAuthFunctions

    def get_auth_functions(self):
        return { 'resource_show': restricted_resource_show,
                 #'resource_view_list': restricted_resource_show
                 'resource_view_show': restricted_resource_show
               }

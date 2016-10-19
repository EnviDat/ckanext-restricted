import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckan.lib.mailer import mail_recipient, MailerException
from ckan.logic.action.create import user_create

from ckanext.restricted import helpers

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


class RestrictedPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'restricted')

    # IActions

    def get_actions(self):
        return { 'user_create': restricted_user_create_and_notify }

    # ITemplateHelpers

    def get_helpers(self):
        return { 'restricted_check_user_resources_access': helpers.restricted_check_user_resources_access }


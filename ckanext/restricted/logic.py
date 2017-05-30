import sys
import json
from sets import Set

import ckan.lib.mailer as mailer
import ckan.logic as logic
#from ckan.common import config
from ckan.lib.base import render_jinja2
import ckan.plugins.toolkit as toolkit

from pylons import config

from logging import getLogger
log = getLogger(__name__)

def restricted_check_user_resource_access(user, resource_dict, package_dict):
    restricted_level = 'public'
    allowed_users  = []
    
    # check in resource_dict
    if resource_dict:
        extras = resource_dict.get('extras',{})
        restricted = resource_dict.get('restricted', extras.get('restricted', {}))
        if not isinstance(restricted, dict):
            try:
                restricted = json.loads(restricted)
            except:
                log.info('Error loading restricted value: "{0}"'.format(restricted))
                restricted = {}

        if restricted:
            restricted_level = restricted.get('level', 'public')
            allowed_users = restricted.get('allowed_users', '').split(',')
        
    # Public resources (DEFAULT)
    if not restricted_level or restricted_level == 'public':
        return {'success': True }

    # Registered user
    if not user:
        return {'success': False, 'msg': 'Resource access restricted to registered users' }
    else:
        if restricted_level == 'registered' or not restricted_level:
            return {'success': True }

    # Since we have a user, check if it is in the allowed list
    if user in allowed_users:
        return {'success': True }
    elif  restricted_level == 'only_allowed_users':
        return {'success': False, 'msg': 'Resource access restricted to allowed users only' }

    # Get organization list
    user_organization_dict = {}

    context = {'user': user}
    data_dict = {'permission': 'read'}

    for org in logic.get_action('organization_list_for_user')(context, data_dict):
        name = org.get('name', '')
        id = org.get('id', '')
        if name and id:
            user_organization_dict[id] =  name

    # Any Organization Members (Trusted Users)
    if not user_organization_dict:
        return {'success': False, 'msg': 'Resource access restricted to members of an organization' }
    if restricted_level == 'any_organization':
        return {'success': True }

    pkg_organization_id = package_dict.get('owner_org', '')

    # Same Organization Members
    if restricted_level == 'same_organization':
        if pkg_organization_id in user_organization_dict.keys():
            return {'success': True }

    return {'success': False, 'msg': 'Resource access restricted to same organization (' + pkg_organization_id + ') members' }

def restricted_mail_allowed_user(user_id, resource):
    log.debug('restricted_mail_allowed_user notifying {0}'.format(user_id))
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
        mail_subject = 'Access granted to resource {0}'.format(resource_name)

        # Send mail to user
        mailer.mail_recipient(user_name, user_email, mail_subject, mail_body)
        
        # Sendo copy to admin
        mailer.mail_recipient('CKAN Admin', config.get('email_to'), 'Fwd: ' + mail_subject, mail_body)
        
    except:
        log.warning('restricted_mail_allowed_user: Failed to send mail to "{0}"'.format(user_id))

def restricted_allowed_user_mail_body(user, resource):
        
    resource_link = toolkit.url_for(controller='package', action='resource_read', 
                                    id=resource.get('package_id'), resource_id=resource.get('id'))
    extra_vars = {
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'user_name': user.get('display_name', user['name']),
        'resource_name': resource.get('name', resource['id']),
        'resource_link': config.get('ckan.site_url') + resource_link,
        'resource_url': resource.get('url')
        }

    return render_jinja2('restricted/emails/restricted_user_allowed.txt', extra_vars)

def restricted_notify_allowed_users(previous_value, updated_resource):
    def _safe_json_loads(json_string, default={}):
        try:
            return json.loads(json_string)
        except:
            return default
            
    previous_restricted = _safe_json_loads(previous_value)
    updated_restricted = _safe_json_loads(updated_resource.get('restricted', ''))        

    # compare restricted users_allowed values
    updated_allowed_users =  Set(updated_restricted.get('allowed_users','').split(','))
    if updated_allowed_users:
        previous_allowed_users = previous_restricted.get('allowed_users','').split(',')
        for user_id in updated_allowed_users:
            if user_id not in previous_allowed_users:
                restricted_mail_allowed_user(user_id, updated_resource)






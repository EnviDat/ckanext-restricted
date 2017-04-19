import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.captcha as captcha
import ckan.lib.mailer as mailer

import ckan.plugins.toolkit as toolkit
from ckan.common import _, request, c, g
from routes import url_for

from logging import getLogger
from pylons import config
from email.header import Header

import simplejson as json

import ckan.lib.navl.dictization_functions as dictization_functions
DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten

render = base.render

log = getLogger(__name__)

class RestrictedController(toolkit.BaseController):

    def __before__(self, action, **env):
        base.BaseController.__before__(self, action, **env)
        try:
            context = {'model': base.model, 'user': base.c.user or base.c.author,
                       'auth_user_obj': base.c.userobj}
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to see this page'))

    def _send_request_mail(self, data):
        success = False
        try:
            site_title = g.site_title
            email_dict = {data.get('maintainer_email'): data.get('maintainer_name', 'Maintainer'), config.get('email_to', 'email_to_undefined'): site_title + ' Admin'}
            subject = 'Access Request to resource ' +  data.get('resource_name','') + ' (' +  data.get('package_name','')  + ') from ' + data.get('user_name','')
            url = config.get('ckan.site_url') + url_for(controller='package', action='resource_read', id=data.get('package_name') , resource_id=data.get('resource_id'))
            edit_link = config.get('ckan.site_url') + url_for(controller='package', action='resource_edit', id=data.get('package_name') , resource_id=data.get('resource_id'))
            body = 'A user has requested access to your data in ' + site_title + ': '
            body += '\n\t * Resource: ' +  data.get('resource_name','') + ' ( ' + str(url) + ' )'
            body += '\n\t * Dataset: ' +  data.get('package_name','')
            body += '\n\t * User: ' + data.get('user_name','') + ' (' + data.get('user_email','') + ')'
            body += '\n\t * Message: ' + data.get('message','')
            body += '\n\n You can allow this user to access you resource by adding ' + data.get('user_id','the user id')+ ' to the list of allowed users.'
            body += ' If you have editor rights, you can edit the resource in this link: ' + str(edit_link)
            body += '\n\n If you have any questions about how to preceed with this request, please contact the ' + site_title + ' support at ' + config.get('email_to', 'email_to_undefined')

            headers = {'CC': ",".join(email_dict.keys()),  'reply-to': data.get('user_email')}
            ## CC doesn't work and mailer cannot send to multiple addresses
            for email, name in email_dict.iteritems():
                mailer.mail_recipient(name, email, subject, body, headers)
            ## Special copy for the user (no links)
            email = data.get('user_email')
            name = data.get('user_name','User')
            body_user = "Please find below a copy of the access request mail sent. \n\n >> " + body.replace("\n", "\n >> ").replace(edit_link, " [ ... ] ").replace(url, " [ ... ] ")
            mailer.mail_recipient(name, email, subject, body_user, headers)
            success=True

        except mailer.MailerException as mailer_exception:
            log.error("Cannot access request mail after registration ")
            log.error(mailer_exception)
            pass

        return success

    def _send_request(self, context):

        try:
            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))

            captcha.check_recaptcha(request)

        except logic.NotAuthorized:
            toolkit.abort(401, _('Not authorized to see this page'))
        except captcha.CaptchaError:
            error_msg = _(u'Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.restricted_request_access_form(package_id=data_dict.get('package_name'), resource_id=data_dict.get('resource'), data=data_dict)

        try:
            pkg = toolkit.get_action('package_show')(context, {'id': data_dict.get('package_name')})
            data_dict['pkg_dict'] = pkg
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')
        except:
            toolkit.abort(404, 'Exception retrieving dataset to send mail')

        # Validation
        errors = {}
        error_summary = {}

        if (data_dict["message"] == ''):
            errors['message'] = [u'Missing Value']
            error_summary['message'] =  u'Missing Value'

        if len(errors) > 0:
            return self.restricted_request_access_form(package_id=data_dict.get('package-name'), resource_id=data_dict.get('resource'), errors=errors, error_summary=error_summary, data=data_dict)

        success = self._send_request_mail(data_dict)

        return render('restricted/restricted_request_access_result.html', extra_vars={'data': data_dict, 'pkg_dict': pkg, 'success': success } )

    def restricted_request_access_form(self, package_id, resource_id, data=None, errors=None, error_summary=None):
        '''Redirects to form
        '''
        user_id = toolkit.c.user
        context = {
            'model': model,
            'session': model.Session,
            'user': user_id,
            'save': 'save' in request.params
        }

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        if (context['save']) and not data and not errors:
            return self._send_request(context)

        if not data:
            data['package_id'] = package_id
            data['resource_id'] = resource_id

            user = toolkit.get_action('user_show')(context, {'id': user_id})
            data['user_id'] = user_id
            data['user_name'] = user.get('display_name', user_id)
            data['user_email'] = user.get('email', '')

            resource_name = ""

            try:
                pkg = toolkit.get_action('package_show')(context, {'id': package_id})
                data['package_name'] = pkg.get('name')
                resources = pkg.get('resources', [])
                for resource in resources:
                    if resource['id'] == resource_id:
                        resource_name = resource['name']
                        break
                else:
                    toolkit.abort(404, 'Dataset resource not found')
                # get mail
                contact_email = pkg.get('maintainer_email', "")
                contact_name = pkg.get('maintainer_name', "Dataset Maintainer")
                if not contact_email:
                    contact_email = json.loads(pkg.get('maintainer', "{}")).get('email','')
                    contact_name = json.loads(pkg.get('maintainer', "{}")).get('name','Dataset Maintainer')
                if not contact_email:
                    contact_email = config.get('email_to', 'email_to_undefined')
                    contact_name = "CKAN Admin"
            except toolkit.ObjectNotFound:
                toolkit.abort(404, 'Dataset not found')
            except:
                toolkit.abort(404, 'Exception retrieving dataset for the form')

            data['resource_name'] = resource_name
            data['maintainer_email'] = contact_email
            data['maintainer_name'] = contact_name
        else:
            pkg = data.get('pkg_dict', {})

        extra_vars = {'pkg_dict':pkg, 'data': data, 'errors':errors, 'error_summary': error_summary}
        return render('restricted/restricted_request_access_form.html', extra_vars=extra_vars)

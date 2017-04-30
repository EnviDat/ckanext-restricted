import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.captcha as captcha
import ckan.lib.mailer as mailer

import ckan.plugins.toolkit as toolkit
from ckan.common import _, request, c, g
from ckan.lib.base import render_jinja2

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

            resource_link = toolkit.url_for(controller='package', action='resource_read', 
                                    id=data.get('package_name'), resource_id=data.get('resource_id'))
            
            resource_edit_link = toolkit.url_for(controller='package', action='resource_edit', 
                                              id=data.get('package_name') , resource_id=data.get('resource_id'))

            extra_vars = {
                'site_title': config.get('ckan.site_title'),
                'site_url': config.get('ckan.site_url'),
                'maintainer_name': data.get('maintainer_name', 'Maintainer'),
                'user_id': data.get('user_id','the user id'),
                'user_name': data.get('user_name', ''),
                'user_email': data.get('user_email', ''),
                'resource_name': data.get('resource_name',''),
                'resource_link': config.get('ckan.site_url') + resource_link,
                'resource_edit_link': config.get('ckan.site_url') + resource_edit_link,
                'package_name': data.get('resource_name',''),
                'message': data.get('message',''),
                'admin_email_to': config.get('email_to', 'email_to_undefined')
                }

            body = render_jinja2('restricted/emails/restricted_access_request.txt', extra_vars)
            subject = 'Access Request to resource ' +  data.get('resource_name','') + ' (' +  data.get('package_name','')  + ') from ' + data.get('user_name','')

            email_dict = {data.get('maintainer_email'): extra_vars.get('maintainer_name'), extra_vars.get('admin_email_to'): extra_vars.get('site_title') + ' Admin'}
            headers = {'CC': ",".join(email_dict.keys()),  'reply-to': data.get('user_email')}

            ## CC doesn't work and mailer cannot send to multiple addresses
            for email, name in email_dict.iteritems():
                mailer.mail_recipient(name, email, subject, body, headers)
            
            ## Special copy for the user (no links)
            email = data.get('user_email')
            name = data.get('user_name','User')
            
            extra_vars['resource_link'] = '[...]'
            extra_vars['resource_edit_link'] = '[...]'
            body = render_jinja2('restricted/emails/restricted_access_request.txt', extra_vars)
            body_user = "Please find below a copy of the access request mail sent. \n\n >> {0}".format( body.replace("\n", "\n >> "))
            mailer.mail_recipient(name, email, 'Fwd: ' + subject, body_user, headers)
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
            toolkit.abort(404, _('Dataset not found'))
        except:
            toolkit.abort(404, _('Exception retrieving dataset to send mail'))

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
        
        if not user_id:
            toolkit.abort(401, _('Access request form is available to logged in users only.'))
            
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

            try:
                user = toolkit.get_action('user_show')(context, {'id': user_id})
                data['user_id'] = user_id
                data['user_name'] = user.get('display_name', user_id)
                data['user_email'] = user.get('email', '')

                resource_name = ""

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
                contact_details = self._get_contact_details(pkg)
            except toolkit.ObjectNotFound:
                toolkit.abort(404, _('Dataset not found'))
            except Exception as e:
                log.warn('Exception Request Form: ' + repr(e))
                toolkit.abort(404, _('Exception retrieving dataset for the form (' + str(e) + ')'))
            except:
                toolkit.abort(404, _('Unknown exception retrieving dataset for the form'))

            data['resource_name'] = resource_name
            data['maintainer_email'] = contact_details.get('contact_email', '')
            data['maintainer_name'] = contact_details.get('contact_name', '')
        else:
            pkg = data.get('pkg_dict', {})

        extra_vars = {'pkg_dict':pkg, 'data': data, 'errors':errors, 'error_summary': error_summary}
        return render('restricted/restricted_request_access_form.html', extra_vars=extra_vars)

    def _get_contact_details(self, pkg_dict):
        contact_email = ""
        contact_name = ""
        # Maintainer as Composite field
        try:
            contact_email = json.loads(pkg_dict.get('maintainer', "{}")).get('email','')
            contact_name = json.loads(pkg_dict.get('maintainer', "{}")).get('name','Dataset Maintainer')
        except:
            pass
        # Maintainer Directly defined
        if not contact_email:
            contact_email = pkg_dict.get('maintainer_email', "")
            contact_name = pkg_dict.get('maintainer', "Dataset Maintainer")
        # 1st Author Directly defined
        if not contact_email:
            contact_email = pkg_dict.get('author_email', '')
            contact_name = pkg_dict.get('author', '')
        # First Author from Composite Repeating
        if not contact_email:
            try:
                author = json.loads(pkg_dict.get('author'))[0]
                contact_email = author.get('email','')
                contact_name = author.get('name','Dataset Maintainer')
            except:
                pass
        # CKAN instance Admin
        if not contact_email:
            contact_email = config.get('email_to', 'email_to_undefined')
            contact_name = "CKAN Admin"
        return {'contact_email':contact_email, 'contact_name':contact_name}



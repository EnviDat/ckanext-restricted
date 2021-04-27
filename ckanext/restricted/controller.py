# coding: utf8

from __future__ import unicode_literals

from ckan import logic, model
from ckan.common import (
    _,
    config,
    request,
)
from ckan.lib import (
    base,
    captcha,
    helpers as h,
    mailer,
)
from ckan.lib.navl.dictization_functions import unflatten
from ckan.plugins import toolkit

from ckanext.restricted import helpers

from logging import getLogger


log = getLogger(__name__)


class RestrictedController(toolkit.BaseController):

    def __before__(self, action, **env):
        base.BaseController.__before__(self, action, **env)
        try:
            context = {'model': base.model,
                       'user': base.c.user or base.c.author,
                       'auth_user_obj': base.c.userobj}
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to see this page'))

    def _send_request_mail(self, data):
        success = False
        try:

            resource_link = toolkit.url_for(
                action='resource_read',
                controller='package',
                id=data.get('package_name'),
                resource_id=data.get('resource_id'))

            resource_edit_link = toolkit.url_for(
                action='resource_edit',
                controller='package',
                id=data.get('package_name'),
                resource_id=data.get('resource_id'))

            extra_vars = {
                'site_title': config.get('ckan.site_title'),
                'site_url': config.get('ckan.site_url'),
                'maintainer_name': data.get('maintainer_name', 'Maintainer'),
                'user_id': data.get('user_id', 'the user id'),
                'user_name': data.get('user_name', ''),
                'user_email': data.get('user_email', ''),
                'resource_name': data.get('resource_name', ''),
                'resource_link': config.get('ckan.site_url') + resource_link,
                'resource_edit_link': config.get('ckan.site_url') + resource_edit_link,
                'package_name': data.get('resource_name', ''),
                'message': data.get('message', ''),
                'admin_email_to': data.get('maintainer_email', 'Admin')
            }

            body = base.render_jinja2('restricted/emails/restricted_access_request.txt', extra_vars)
            subject = \
                _('Access Request to resource {0} ({1}) from {2}').format(
                    data.get('resource_name', ''),
                    data.get('package_name', ''),
                    data.get('user_name', ''))

            email_dict = {
                data.get('maintainer_email'): extra_vars.get('maintainer_name'),
                extra_vars.get('admin_email_to'): '{} Admin'.format(extra_vars.get('site_title'))}

            headers = {
                'CC': ",".join(email_dict.keys()),
                'reply-to': data.get('user_email')}

            # CC doesn't work and mailer cannot send to multiple addresses
            for email, name in email_dict.iteritems():
                mailer.mail_recipient(name, email, subject, body, headers)

            # Special copy for the user (no links)
            email = data.get('user_email')
            name = data.get('user_name', 'User')

            extra_vars['resource_link'] = '[...]'
            extra_vars['resource_edit_link'] = '[...]'
            body = base.render_jinja2(
                'restricted/emails/restricted_access_request.txt', extra_vars)

            body_user = _(
                'Please find below a copy of the access '
                'request mail sent. \n\n >> {}'
            ).format(body.replace("\n", "\n >> "))

            mailer.mail_recipient(
                name, email, 'Fwd: ' + subject, body_user, headers)
            success = True

        except mailer.MailerException as mailer_exception:
            log.error('Can not access request mail after registration.')
            log.error(mailer_exception)

        return success

    def _send_request(self, context):

        try:
            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))

            captcha.check_recaptcha(request)

        except logic.NotAuthorized:
            toolkit.abort(401, _('Not authorized to see this page'))
        except captcha.CaptchaError:
            error_msg = _('Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.restricted_request_access_form(
                package_id=data_dict.get('package_name'),
                resource_id=data_dict.get('resource'),
                data=data_dict)

        try:
            pkg = toolkit.get_action('package_show')(
                context, {'id': data_dict.get('package_name')})
            data_dict['pkg_dict'] = pkg
        except toolkit.ObjectNotFound:
            toolkit.abort(404, _('Dataset not found'))
        except Exception:
            toolkit.abort(404, _('Exception retrieving dataset to send mail'))

        # Validation
        errors = {}
        error_summary = {}

        if (data_dict['message'] == ''):
            msg = _('Missing Value')
            errors['message'] = [msg]
            error_summary['message'] = msg

        if len(errors) > 0:
            return self.restricted_request_access_form(
                data=data_dict,
                errors=errors,
                error_summary=error_summary,
                package_id=data_dict.get('package-name'),
                resource_id=data_dict.get('resource'))

        success = self._send_request_mail(data_dict)

        return base.render(
            'restricted/restricted_request_access_result.html',
            extra_vars={'data': data_dict, 'pkg_dict': pkg, 'success': success})

    def restricted_request_access_form(
            self, package_id, resource_id,
            data=None, errors=None, error_summary=None):
        """Redirects to form."""
        user_id = toolkit.c.user
        if not user_id:
            toolkit.abort(401, _('Access request form is available to logged in users only.'))

        context = {'model': model,
                   'session': model.Session,
                   'user': user_id,
                   'save': 'save' in request.params}

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

                resource_name = ''

                pkg = toolkit.get_action('package_show')(context, {'id': package_id})
                data['package_name'] = pkg.get('name')
                resources = pkg.get('resources', [])
                for resource in resources:
                    if resource['id'] == resource_id:
                        resource_name = resource['name']
                        break
                else:
                    toolkit.abort(404, 'Dataset resource not found')

            except toolkit.ObjectNotFound:
                toolkit.abort(404, _('Dataset not found'))
            except Exception as e:
                log.warn('Exception Request Form: ' + repr(e))
                toolkit.abort(404, _(u'Exception retrieving dataset for the form ({})').format(str(e)))
            except Exception:
                toolkit.abort(404, _('Unknown exception retrieving dataset for the form'))

            data['resource_name'] = resource_name

        else:
            pkg = data.get('pkg_dict', {})

        # get mail
        contact_details = self._get_contact_details(pkg)
        data['maintainer_email'] = contact_details.get('contact_email', '')
        data['maintainer_name'] = contact_details.get('contact_name', '')

        extra_vars = {
            'pkg_dict': pkg, 'data': data,
            'errors': errors, 'error_summary': error_summary}
        return base.render(
            'restricted/restricted_request_access_form.html',
            extra_vars=extra_vars)

    def _get_contact_details(self, pkg_dict):
        contact_email = helpers.get_maintainer_email(
            package_id=pkg_dict.get('id'))
        contact_name = 'CKAN Admin'
        return {'contact_email': contact_email, 'contact_name': contact_name}


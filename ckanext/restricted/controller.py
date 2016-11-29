import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h

import ckan.plugins.toolkit as toolkit
from ckan.common import _, request, c

from logging import getLogger
from pylons import config

import simplejson as json
import ckan.lib.captcha as captcha

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
            return self.restricted_request_access_form(package_id=data_dict.get('package-name'), resource_id=data_dict.get('resource'), data=data_dict)

        log.debug('_send_request')
        log.debug('context = ' + repr (context))
        log.debug('data_dict = ' + repr (data_dict))

        try:
            pkg = toolkit.get_action('package_show')(context, {'id': data_dict.get('package-name')})
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')

        return render('restricted/restricted_request_access_result.html', extra_vars={'data': data_dict, 'pkg_dict': pkg } )

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

        if (context['save']) and not data:
            return self._send_request(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data['package_id'] = package_id 
        data['resource_id'] = resource_id

        user = toolkit.get_action('user_show')(context, {'id': user_id})
        data['user_name'] = user.get('display_name', user_id)
        data['user_email'] = user.get('email', '')

        resource_name = ""
        try:
            pkg = toolkit.get_action('package_show')(context, {'id': package_id})
            #log.debug('restricted_request_access package_show (' + package_id + ', ' +  resource_id +'):' + repr(pkg))
            resources = pkg.get('resources', [])
            for resource in resources:
                if resource['id'] == resource_id:
                    resource_name = resource['name']
                    break
            else:
                toolkit.abort(404, 'Dataset resource not found')
            # get mail
            contact_email = pkg.get('maintainer_email', "")
            if not contact_email:
                contact_email = json.loads(pkg.get('maintainer', "{}")).get('email','')
            if not contact_email:
                contact_email = config.get('email_to')
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')

        data['resource_name'] = resource_name
        data['email'] = contact_email
        extra_vars = {'pkg_dict':pkg, 'data': data, 'errors':errors, 'error_summary': error_summary}

        return render('restricted/restricted_request_access_form.html', extra_vars=extra_vars)

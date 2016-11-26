import ckan.model as model
import ckan.plugins.toolkit as toolkit

from logging import getLogger
import ckan.lib.base as base

from pylons import config
import simplejson as json

render = base.render

log = getLogger(__name__)

class RestrictedController(toolkit.BaseController):

    def restricted_request_access(self, package_id, resource_id):
        '''Redirects to form
        '''
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }

        resource_name = ""
        try:
            pkg = toolkit.get_action('package_show')(context, {'id': package_id})
            resources = pkg.get('resources', [])
            for resource in resources:
                if resource['id'] == resource_id:
                    resource_name = resource['name']
            # get mail
            email = pkg.get('maintainer_email', "")
            if not email:
                email = json.loads(pkg.get('maintainer', "{}")).get('email','')
            if not email:
                email = config.get('email_to')
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')

        extra_vars = {'pkg_dict':pkg, 'errors':{}}
        extra_vars['data'] = {'user':toolkit.c.user, 'package_id':package_id, 'resource_id':resource_id, 'resource_id':resource_name, 'email': email}

        return render('package/restricted_request_access.html', extra_vars=extra_vars)

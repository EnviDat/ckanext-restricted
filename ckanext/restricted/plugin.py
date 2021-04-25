# coding: utf8

from __future__ import unicode_literals
from ckan.lib.plugins import DefaultTranslation
import ckan.logic
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.restricted import action
from ckanext.restricted import auth
from ckanext.restricted import helpers
from ckanext.restricted import logic
from ckanext.restricted import validation
import ckanext.restricted.blueprints as blueprints

from logging import getLogger
log = getLogger(__name__)


_get_or_bust = ckan.logic.get_or_bust


class RestrictedPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint, inherit=True)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IValidators)


    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'restricted')

    # IActions
    def get_actions(self):
        return {'user_create': action.restricted_user_create_and_notify,
                'resource_view_list': action.restricted_resource_view_list,
                'restricted_check_access': action.restricted_check_access}

    # ITemplateHelpers
    def get_helpers(self):
        return {'restricted_get_user_id': helpers.restricted_get_user_id}

    # IAuthFunctions
    def get_auth_functions(self):
        return {'resource_show': auth.restricted_resource_show,
                'resource_view_show': auth.restricted_resource_show}

    # IResourceController
    def before_update(self, context, current, resource):
        context['__restricted_previous_value'] = current.get('restricted')

    def after_update(self, context, resource):
        previous_value = context.get('__restricted_previous_value')
        logic.restricted_notify_allowed_users(previous_value, resource)

    # IBlueprint
    def get_blueprint(self):
        return blueprints.get_blueprints(self.name, self.__module__)

    # IValidators
    def get_validators(self):
        return {'restricted_username_from_mail': validation.restricted_username_from_mail}

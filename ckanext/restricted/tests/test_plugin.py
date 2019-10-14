"""Tests for plugin.py."""
# encoding: utf-8

from nose.tools import assert_raises
import ckan.model as model
import ckan.plugins
import ckan.tests.factories as factories
import ckan.logic as logic


class TestExampleIAuthFunctionsPluginV6ParentAuthFunctions(object):
    '''Tests for the ckanext.example_iauthfunctions.plugin module.

    Specifically tests that overriding parent auth functions will cause
    child auth functions to use the overridden version.
    '''
    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''
        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        ckan.plugins.load('restricted')

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''
        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class
        have been run.

        '''
        # We have to unload the plugin we loaded, so it doesn't affect any
        # tests that run after ours.
        ckan.plugins.unload('restricted')

    def test_basic_access(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''

        owner = factories.User()
        access = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=True)
        resource = factories.Resource(package_id=dataset['id'])

        assert logic.check_access('package_show', {'user': owner['name']}, {'id': dataset['id']})
        assert logic.check_access('resource_show', {'user': owner['name']}, {'id': resource['id']})
        with assert_raises(logic.NotAuthorized):
            logic.check_access('package_show', {'user': access['name']}, {'id': dataset['id']})
        with assert_raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})

    def test_public_package_restricted_resource(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''

        owner = factories.User()
        org_user = factories.User()
        access = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'},
                   {'name': org_user['id'], 'capacity': 'member'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        resource = factories.Resource(package_id=dataset['id'])

        assert logic.check_access('package_show', {'user': access['name']}, {'id': dataset['id']})
        assert logic.check_access('resource_show', {'user': org_user['name']}, {'id': resource['id']})

        with assert_raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})

    def test_public_resource(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''

        owner = factories.User()
        access = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]

        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        resource = factories.Resource(package_id=dataset['id'],
                                      restricted='{"level": "public"}')

        assert logic.check_access('package_show', {'user': access['name']}, {'id': dataset['id']})
        assert logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})

    def test_allow_users(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''

        owner = factories.User()
        access = factories.User()
        access2 = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]

        )
        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        restrict_string = '{"level": "restricted", "allowed_users":["%s"]}' % (access["name"], )
        resource = factories.Resource(package_id=dataset['id'],
                                      restricted=restrict_string)

        assert logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})
        with assert_raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access2['name']}, {'id': resource['id']})

    def test_allow_organizations(self):
        '''Normally organization admins can delete resources
        Our plugin prevents this by blocking delete organization.

        Ensure the delete button is not displayed (as only resource delete
        is checked for showing this)

        '''

        owner = factories.User()
        access = factories.User()
        access2 = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]

        )
        access_org = factories.Organization(
            users=[{'name': access['id'], 'capacity': 'admin'}]
        )

        dataset = factories.Dataset(owner_org=owner_org['id'], private=False)
        restrict_string = '{"level": "restricted", "allowed_organizations":["%s"]}' % (access_org["name"], )
        resource = factories.Resource(package_id=dataset['id'],
                                      restricted=restrict_string)

        assert logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})
        with assert_raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access2['name']}, {'id': resource['id']})

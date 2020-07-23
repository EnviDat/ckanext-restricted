"""Tests for plugin.py."""
# encoding: utf-8
from ckan.tests import helpers
from nose.tools import assert_raises
import ckan.tests.factories as factories
import ckan.logic as logic


class TestRestrictedPlugin(helpers.FunctionalTestBase):
    '''Tests for the ckanext.example_iauthfunctions.plugin module.
    Specifically tests that overriding parent auth functions will cause
    child auth functions to use the overridden version.
    '''

    _load_plugins = ['restricted']

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
        restrict_string = '{"level": "restricted", "allowed_users":["%s"]}' % (access["name"],)
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
        restrict_string = '{"level": "restricted", "allowed_organizations":["%s"]}' % (access_org["name"],)
        resource = factories.Resource(package_id=dataset['id'],
                                      restricted=restrict_string)

        assert logic.check_access('resource_show', {'user': access['name']}, {'id': resource['id']})
        with assert_raises(logic.NotAuthorized):
            logic.check_access('resource_show', {'user': access2['name']}, {'id': resource['id']})

    def _two_users_with_two_restricted_resources(self):
        restrict_string = '{{"level": "restricted", "allowed_organizations":["{!s}"]}}'
        user = factories.User()
        user_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]

        )
        user_dataset = factories.Dataset(user_org=user_org['id'], private=False)
        user_resource = factories.Resource(package_id=user_dataset['id'],
                                           name="user-resource",
                                           restricted=restrict_string.format(user_org["name"]))
        other = factories.User()
        other_org = factories.Organization(users=[{'name': other['id'], 'capacity': 'admin'}])
        other_dataset = factories.Dataset(other_org=other_org['id'], private=False)
        other_resource = factories.Resource(package_id=other_dataset['id'],
                                            name="other-resource",
                                            restricted=restrict_string.format(other_org["name"]))
        return user, user_resource, other, other_resource

    def test_user_can_search_only_accessible_resources(self):
        # given:
        user, user_resource, other, other_resource = self._two_users_with_two_restricted_resources()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        resource_search = helpers.call_action(
            'resource_search',
            context,
            query='name:resource',
            hide_inaccessible_resources=True
        )
        # then:
        assert resource_search['count'] == 1
        assert len(resource_search['results']) == 1
        assert resource_search['results'][0] == other_resource

    def test_user_can_search_all_resources(self):
        # given:
        user, user_resource, other, other_resource = self._two_users_with_two_restricted_resources()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        resource_search = helpers.call_action(
            'resource_search',
            context,
            query='name:resource'
        )
        # then:
        assert resource_search['count'] == 2
        for r in [user_resource, other_resource]:
            assert r in resource_search['results']

    def _two_users_one_package_two_resources_one_restricted(self):
        user = factories.User()
        other = factories.User()
        organisation = factories.Organization(
            users=[
                {'name': user['id'], 'capacity': 'admin'}
            ]

        )
        restrict_other = '{{"level": "restricted", "allowed_users":["{}"]}}'.format(other["name"])
        restrict_org = '{{"level": "restricted", "allowed_organisations":["{}"]}}'.format(organisation["name"])
        dataset = factories.Dataset(owner_org=organisation['id'], private=False)
        other_resource = factories.Resource(package_id=dataset['id'],
                                            name="other-resource",
                                            restricted=restrict_other)
        org_resource = factories.Resource(package_id=dataset['id'],
                                          name="org-resource",
                                          restricted=restrict_org)
        return dataset, other, other_resource, org_resource

    def test_user_can_see_only_accessible_resource_in_package_show(self):
        # given:
        dataset, other, other_resource, org_resource = self._two_users_one_package_two_resources_one_restricted()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        package_show = helpers.call_action(
            'package_show',
            context,
            id=dataset['id'],
            hide_inaccessible_resources=True
        )
        # then:
        assert package_show['num_resources'] == 1
        assert len(package_show['resources']) == 1
        assert package_show['resources'][0]['id'] == other_resource['id']

    def test_user_can_see_all_resource_in_package_show(self):
        # given:
        dataset, other, other_resource, org_resource = self._two_users_one_package_two_resources_one_restricted()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        package_show = helpers.call_action(
            'package_show',
            context,
            id=dataset['id']
        )
        # then:
        assert package_show['num_resources'] == 2
        assert len(package_show['resources']) == 2
        resources_ids = [x['id'] for x in package_show['resources']]
        for r in [org_resource['id'], other_resource['id']]:
            assert r in resources_ids

    def test_user_can_see_only_accessible_resource_in_package_search(self):
        # given:
        dataset, other, other_resource, org_resource = self._two_users_one_package_two_resources_one_restricted()
        # when:
        context = {
            'ignore_auth': False,
            'user': other['name']
        }
        package_search = helpers.call_action(
            'package_search',
            context,
            q=dataset['title'],
            hide_inaccessible_resources=True
        )
        # then:
        package = package_search['results'][0]
        assert package['num_resources'] == 1
        assert len(package['resources']) == 1
        assert package['resources'][0]['id'] == other_resource['id']

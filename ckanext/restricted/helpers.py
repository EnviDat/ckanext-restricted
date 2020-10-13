# coding: utf8

from ckan.common import c
from ckan.plugins import toolkit


def restricted_get_user_id():
    return (str(c.user))


def get_package_from_id(package_id):
    context = {'user': toolkit.g.user}
    return toolkit.get_action('package_show')(context, {'id': package_id})

# coding: utf8 


from ckan.common import c


def restricted_get_user_id():
    return (str(c.user))

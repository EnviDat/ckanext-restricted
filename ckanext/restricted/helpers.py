from ckan.common import c

def restricted_get_user_id():
    print(" XXXXXXX  restricted_get_user_id " + str(c.user))

    return (str(c.user))

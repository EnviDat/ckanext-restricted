from ckantoolkit import _
import json
from ckanext.scheming.validation import scheming_validator
import ckan.model as model
from sqlalchemy.sql.expression import or_

from ckan.model import meta

import logging

logger = logging.getLogger(__name__)

@scheming_validator
def restricted_username_from_mail(field, schema):
    def validator(key, data, errors, context):
        """
          replace the email entered with an username
        """
        restricted_data = {}
        try:
            restricted_data = json.loads(data.get(key, '{}'))
        except json.JSONDecodeError as e:
            logger.warning('restricted_username_from_mail: issues parsing data: "{0}", ERROR: {1}'.format(data, e))


        if restricted_data.get('allowed_users'):
            allowed_users = restricted_data['allowed_users'].split(',')
            new_allowed_users = []
            for username in allowed_users:
                new_name = username
                if username.find('@') > 0:
                    new_name = ''
                    query = _restricted_user_search(username)
                    query = query.filter(model.User.state != model.State.DELETED)
                    query = query.limit(1)

                    for user in query.all():
                        new_name = user.name
                        break
                if new_name and new_name not in new_allowed_users:
                    logger.debug("restricted_username_from_mail: replacing {0} => {1}".format(username, new_name))
                    new_allowed_users += [new_name]
            restricted_data['allowed_users'] = ','.join(new_allowed_users)
            data[key] = json.dumps(restricted_data)

    return validator

def _restricted_user_search(querystr):
    '''Search name, fullname, email. '''
    query = meta.Session.query(model.User)
    qstr = '%' + querystr + '%'
    filters = [
        model.User.name.ilike(qstr),
        model.User.fullname.ilike(qstr),
        model.User.email.ilike(qstr)
    ]
    query = query.filter(or_(*filters))
    return query

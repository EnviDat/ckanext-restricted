.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/espona/ckanext-restricted.svg?branch=master
    :target: https://travis-ci.org/espona/ckanext-restricted

.. image:: https://coveralls.io/repos/espona/ckanext-restricted/badge.svg
  :target: https://coveralls.io/r/espona/ckanext-restricted

.. image:: https://img.shields.io/pypi/dm/ckanext-restricted.svg
    :target: https://pypi.python.org/pypi//ckanext-restricted/
    :alt: Downloads

.. image:: https://img.shields.io/pypi/v/ckanext-restricted.svg
    :target: https://pypi.python.org/pypi/ckanext-restricted/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/ckanext-restricted.svg
    :target: https://pypi.python.org/pypi/ckanext-restricted/
    :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/status/ckanext-restricted.svg
    :target: https://pypi.python.org/pypi/ckanext-restricted/
    :alt: Development Status

.. image:: https://img.shields.io/pypi/l/ckanext-restricted.svg
    :target: https://pypi.python.org/pypi/ckanext-restricted/
    :alt: License

=============
ckanext-restricted
=============

.. Put a description of your extension here:
   What does it do? What features does it have?
   Consider including some screenshots or embedding a video!

CKAN extension to restrict the accessibility to the resources of a dataset.
This way the package metadata is accesible but not the data itself (resource). 
The resource access restriction level can be individualy defined for every package.

Users can request access to a dataset by pressing a button and filling up a simple form. The package owner can
allow individual users to access the resource. If the users allowed individually 
will be notified by mail. It also includes notifying by mail on every new user registration that can be disabled (expained later in this document). The mails are generated from templates that can be extended.

All information inside the restricted fields (except 'level') is hidden for users other than the ones who can edit the dataset. We used this to keep a shared-secret key field for accessing remotely hosted resources (https://github.com/EnviDat/ckanext-envidat_theme/blob/4265ecfe90e10eb1f095e8e8d19fe43554ab6799/ckanext/envidat_theme/helpers.py#L28). 
The allowed usernames are hidden partially to the non-editors, in our case was critical because they were very similar to the user emails (https://github.com/EnviDat/ckanext-restricted/blob/2d7b2915ef50249fe8d9ec43ceaf532918506539/ckanext/restricted/action.py#L153).

restricted_resources_metadata.PNG
restricted_resources_preview.PNG

.. figure:: restricted_resources_preview.PNG
    :align: center
    :alt: Package view with restricted resources
    :figclass: align-center

    Package view with restricted resources

.. figure:: restricted_resources_metadata.PNG
    :align: center
    :alt: Resource metadata including restriction configuration
    :figclass: align-center

    Resource metadata including restriction configuration
    
.. figure:: restricted_resources_request_form.PNG
    :align: center
    :alt: Request form for restricted resources
    :figclass: align-center

    Request form for restricted resources

------------
Requirements
------------

This extension has been developed for CKAN version 2.5.2 and is compatible up to 2.7.x.

The resource access restriction level can be individualy defined for every package. This requires adding an extra field to package metadata with (some of) the possible values: "public",  "registered", "any_organization",  "same_organization" (as the package).

The allowed user list is also defined in an additional field that includes autocomplete.

If you use ckanext-scheming and ckanext-composite, this is the field definition in JSON:
::
     {
     "scheming_version": 1,
     "dataset_type": "dataset",
     "about": "",
     "about_url": "http://github.com/ckan/ckanext-scheming",
     "dataset_fields": [...],
     "resource_fields": [
      [...]
       {
       "field_name": "restricted",
       "label": "Access Restriction",
       "preset": "composite",
       "subfields":
        [
          {
            "field_name": "level",
            "label": "Level",
            "preset": "select",
            "form_include_blank_choice": false,
            "required": true,
            "choices": [
              {
                "value": "public",
                "label": "Public"
              },
              {
                "value": "registered",
                "label": "Registered Users"
              },
              {
                "value": "any_organization",
                "label": "Any Organization Members (Trusted Users)"
              },
              {
                "value": "same_organization",
                "label": "Same Organization Members"
               },
               {
                "value": "only_allowed_users",
                "label": "Allowed Users Only"
              }
             ]
           },
            {
            "field_name": "allowed_users",
             "label": "Allowed Users",
             "preset": "tag_string_autocomplete",
             "data-module-source":"/api/2/util/user/autocomplete?q=?"
             }
           ]
         }
       ]
     }

The usage of this extension, regarding the level "any_organization", makes more sense if the CKAN administrator sets some users as members of an organization. In our case we created an organization called "trusted_users" where the mail accounts have been double checked. Therefore this extension sends a mail to the defined 'mail_to' in the CKAN config file at every new user registration. To switch off this functionality, just comment out the code at:  
https://github.com/espona/ckanext-restricted/blob/master/ckanext/restricted/plugin.py#L14

It is also recommended to set up the recaptcha in the config file
     # Restricted
     ckan.recaptcha.version = 2
     ckan.recaptcha.privatekey = 6LeQxxxxxxxxxxxxxxxxxxxxxxxxdN82ojuQAgBd
     ckan.recaptcha.publickey =  6LeQxxxxxxxxxxxxxxxxxxxxxxxxdN82ojuQAgBd

The for mail notifications, the mail_to and smtp options in the ini file have to be configured. Please take a look to the following documentation: 

- http://docs.ckan.org/en/latest/maintaining/configuration.html#email-settings
- http://docs.ckan.org/en/latest/maintaining/email-notifications.html

 
------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-restricted:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-restricted Python package into your virtual environment::

     pip install ckanext-restricted

3. Add ``restricted`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

Document any optional config settings here. For example::

    # The minimum number of hours to wait before re-checking a resource
    # (optional, default: 24).
    ckanext.restricted.some_setting = some_default_value


------------------------
Development Installation
------------------------

To install ckanext-restricted for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/espona/ckanext-restricted.git
    cd ckanext-restricted
    python setup.py develop
    pip install -r dev-requirements.txt


-----------------
Running the Tests
-----------------

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.restricted --cover-inclusive --cover-erase --cover-tests


---------------------------------
Registering ckanext-restricted on PyPI
---------------------------------

ckanext-restricted should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-restricted. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


----------------------------------------
Releasing a New Version of ckanext-restricted
----------------------------------------

ckanext-restricted is availabe on PyPI as https://pypi.python.org/pypi/ckanext-restricted.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags

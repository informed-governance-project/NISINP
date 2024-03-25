Permissions and roles
=====================

Roles
-----

The available roles are:

- PlatformAdmin (Django super admin)
- RegulatorAdmin
- RegulatorUser
- OperatorAdmin
- OperatorUser

The first PlatformAdmin user must be created with the Django command:

.. code-block:: bash

    $ python manage.py createsuperuser


This user will be able to create RegulatorAdmin users and able
to configure the ``Site`` section of the Django application.


Incident module members permissions
-----------------------------------

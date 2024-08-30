Permissions and roles
=====================

Summary
----------

The available roles are:

- PlatformAdmin (Django super admin)
- RegulatorAdmin
- RegulatorUser
- OperatorAdmin
- OperatorUser
- ObserverUser
- ObserverAdmin


Permissions 
--------------------

PlatformAdmin (Django super admin)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first PlatformAdmin user must be created with the Django command:

.. code-block:: bash

    $ python manage.py createsuperuser


This user will be able to create RegulatorAdmin users and able
to configure the ``Site`` section of the Django application.

This user can create Observer and Regulator and linked to that ObserverAdmin et RegulatorAdmin. 

RegulatorAdmin
~~~~~~~~~~~~~~~~
The RegulatorAdmin can create other RegulatorAdmin, or RegulatorUser for his entity. 
The RegulatorAdmin has also the responsibility to define the different incident notification workflows. 

ObserverAdmin
~~~~~~~~~~~~~~~~
The ObserverAdmin can create other ObserverAdmin, or ObserverUser for his entity. 


RegulatorUser
~~~~~~~~~~~~~~~~
The RegulatorUser can create company and create an OperatorAdmin who is the administrator of the company (operator)

OperatorAdmin
~~~~~~~~~~~~~~~~

OperatorAdmin creates OperatorUser for his company. 

OperatorUser and ObserverUser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

They have no administration role. 



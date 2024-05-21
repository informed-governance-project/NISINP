Administrator interface
=====================

log-in
-----

On this page you can log in or create an account in case you have to notify an incident and you don't have your credential.

.. figure:: _static/ui_user_login_page.png
   :alt: Login page.
   :target: _static/ui_user_login_page.png

   Screenshot of the login page.

If you have credentials and don't remember the password please use the link: 'Forgotten your password or username?'

At the first login, you need to activate the 2FA.

Access to the administrator page
-----

The following roles have access to the administrator interface: 

- PlatformAdmin : create regulation, regulators, certs
- RegulatorAdmin : create the workflows for incidents, RegulatorUser for its regulator
- RegulatorUser : create companies
- OperatorAdmin : create OperatorUser for its company
- CertAdmin : create CertUser for its CERT 

.. figure:: _static/ui_admin_overview.png
   :alt: admin page.
   :target: _static/ui_admin_overview.png

   Screenshot of an administrator page.

The administrator page is composed of 3 parts:

1. The navigation bar where you can change your account settings, language, also leaves the website and return on the user interface 
2. A list of modules you have access and things you can modify, see, or delete
3. A list of your recent changes on the application

Standard list view
-----

When clicking on an entity for example "Impacts" here, you list all the objects and you have different possible actions. 

.. figure:: _static/ui_standard_list.png
   :alt: edit page.
   :target: _static/ui_standard_list.png

   Screenshot of a list page.

1. For some entities, you can import/export in several formats (JSON, CSV, etc.)
2. For some entities, you can filter the list depending of its attributes
3. It's also possible to limit the number of displayed items with the search bar 
4. Some group actions are also available, for that you need to tick the case corresponding to the entries you want to modify and select the appropriate action

Standard add / change function
-----

When clicking on add or editing an object, you arrive on this kind of view for all the objects. The difference between editing and adding is in editing mode, the values are prefilled by the existing one

.. figure:: _static/ui_standard_add_edit.png
   :alt: edit page.
   :target: _static/ui_standard_add_edit.png

   Screenshot of an edition page.

1. You can change the language of the object, be informed that you always need to fill the fallback language. Be aware that you need to save each language separately. So, if you want to save the 3 languages in one step use the "save and continue editing"
2. In case of editions you can see the history of the object (all the modifications done)
3. Different possibilities to save the object
4. In case of editing you can also delete the object. If you choose to delete the object, a confirmation message will be shown with the impacts on other entities




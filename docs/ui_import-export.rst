Importing and exporting database tables (currently disabled for security reasons)
--------------------------------------------------------------------------------------

Some models of the application can be exported and/or imported. The import / export is done **language by language**. So, if you want to export in two languages, you have to do 2 exports. Same for the import.

 .. figure:: _static/ui_admin_export.png
    :alt: import / export.
    :target: _static/ui_admin_export.png

    Import export principle.

1. Button to import. When you click on import, you can choose the format of your file. And the view shows you the available field to import. **If you want to create, it's preferable to not put the id field**.After clicking on that button, you have to select the file and the format (e.g. xlsx) and click on submit. **Take care of choosing the right language, it will import in the language you have chosen**. After that you have this view :

 .. figure:: _static/ui_admin_import.png
    :alt: import view.
    :target: _static/ui_admin_import.png

    Import view.

 This view is summarizing the import, you can see the changes.

2. Button to export, when you export, the result of the export is the list which is displayed on the page. So you can reduce the list by searching or using a filter on the page if there are some available. After clicking on it, you can choose the format, the easiest is to choose ``xlsx``.

3. Search bar to reduce the exported list.


Questions of incident report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To import or export questions you need three models: ``predefined answers, question categories, questions``

Importing has to happen in this order:

1. Question categories
2. Questions
3. Predefined answers

If you want to create the files from scratch, you can create a ``question categories`` file mentioning:

- ``label`` : the name of the category

- ``position`` : position of the category, lower positions are shown in first during the incident report

After you have to import the ``questions``:

- ``label`` : The question itself
- ``tooltip`` : If the question needs a tooltip
- ``question_type`` : The type of the question, there are several types :
   - MULTI - multiple choice,
   - FREETEXT - free text question,
   - SO - single option choice,
   - MT - multiple choice and free text,
   - ST - single choice and free text,
   - CL - Country list,
   - RL - Region list,
   - DATE - a date picker question.
- ``is_mandatory`` : if the question is mandatory, put True, if not put False
- ``position`` : position of the question inside the category, lower positions are shown in first during the incident report
- ``category`` : label of the category in the language you want to import

After you have to import the ``predefined answers``:

- ``predefined_answer`` : The answer, for exemple Yes for a Yes/No question.
- ``question`` : The label of the question in the language you want to import
- ``position`` : position of the answer, lower positions are shown in first during the incident report

You have now your database in one language. If you want to import other languages, you can now export the model (e.g. questions, question categories, etc.) you want to translate to get the IDs.
You have to follow the same procedure than before but putting the id to the file to have an update instead of a creation. And remember to **import in the right language**.

Sectors
~~~~~~~~

For importing sectors you need to respect the following rules:

- If your sector has a parent, **please put the parent before** in the file, the parent has to be imported before
- If there is no parent, **don't let the field blank**, put ``NULL`` or ``-`` into the field. Blank fields raise errors

The fields are:

- ``parent`` : the sector above (name in the same language)
- ``name`` : the name of the sector
- ``acronym`` : acronym for the sector, used for the incident reference

To update fields, for example, to update translations you need to export first to have the id and put the id field into the file.

Impacts
~~~~~~~~

For importing impacts, all the reffered elements (regulation and sectors) should be present in the system.

The fields are:

- ``regulation`` : the regulation affected by the impact
- ``label`` : description of the impact
- ``headline`` : headline of the impacts
- ``sectors`` : name of the sectors, to link the impact to one or several sectors, **|** is the separator

To update fields, for example, to update translations you need to export first to have the id and put the id field into the file.


Companies
~~~~~~~~~~

The fields are the following:

- ``identifier`` : 4 digits identifier of the company
- ``name`` : Name of the company
- ``address`` : Address of the company
- ``country`` : 2 letters country code following the ISO 3166-2. for exemple FR for France
- ``email`` : generic email of the company
- ``phone_number`` : generic phone number of the company, for exemple +1 212-555-2368


Users
~~~~~~~~

For importing users, you need first to import the company or companies, they are linked to and sector(s). You can only import ``OperatorUser``, ``OperatorAdmin``, ``IncidentUser``.

The system can't tolerate two users with the same email address.

The fields are the following:

- ``firstname`` : first name of the user
- ``lastname`` : last name of the user
- ``email`` : email of the users, it's the pivot to update a user
- ``phone_number`` : phone number of the user, for exemple +1 212-555-2368
- ``sectors`` : sectors linked to the user. Company(ies) have to be present. If they are not present sectors are ignored
- ``companies`` : companies linked to the user. Sector(s) have to be present. if they are not present companies are ignored
- ``administrator`` : True if the user has to be an administrator of the company else False.

By default user without companies and sectors are categorized as ``IncidentUser``.

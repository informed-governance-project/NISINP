Platform Admin
-------------------

If you are a **Platform Admin**, you can use the **Administration Console** as described below. 

  **Please note that as a Platform Admin, you do not have access to the user interface** (when you log in, you are presented with the Admin Console, 
  and you cannot click the Settings button on the user interface). 

There are four sections in the Administration Console: **Administration, Governance, Sites**, and **Recent Actions**.

.. figure:: _static/platform_admin_images/PLAT_ADM_01.png
   :alt: Platform Admin - Administration Console
   :target: _static/platform_admin_images/PLAT_ADM_01.png

The Platform Admin has very special rights and scope of activities as follows:

-	Creates a common database for all regulators and the users of the regulators
-	Configures the server and the regulator users
-	Sets up the admin platform
-	Creates workflows

Administration
~~~~~~~~~~~~~~~~~~~~~

In the Administration section, there is only one link called **Log entries**.

Log entries
^^^^^^^^^^^^^^^^^^^^^

A log records any action performed by Regulator Admins or other Platform Admins. When you click the **Log Entries** link (or the View link), you are taken to the **Select Log Entry to view** screen. This screen displays a list of all log entries in the system.

The table includes four columns:

-	**Action Time**: 	when the action occurred
-	**User**: 		who performed the action
-	**Content Type**:	which section or type of content was affected
-	**Activity**:		the type of action that was taken

You can sort the columns in descending or ascending order. Also, you can use the search field at the top or use the **Filter** section on the right to narrow down the number of entries and find the log you are looking for.

.. figure:: _static/platform_admin_images/PLAT_ADM_02.png
   :alt: Select Log Entry to view
   :target: _static/platform_admin_images/PLAT_ADM_02.png

If you need further information about a log entry, click its link in the **Action Time** column. You will be directed to the **View Log Entry** screen, where you can find additional details about the selected log entry.

.. figure:: _static/platform_admin_images/PLAT_ADM_03.png
   :alt: View Log Entry
   :target: _static/platform_admin_images/PLAT_ADM_03.png

Governance
~~~~~~~~~~~~~~~~~~~~~

The next section in the left panel is called **Governance**. It includes several functionalities, which are briefly explained in this chapter.

Django Settings
^^^^^^^^^^^^^^^^^^^^^

You can use **Django Settings** to check the configuration of your **SERIMA** server instance. The variables you can see here are read-only.

.. figure:: _static/platform_admin_images/PLAT_ADM_04.png
   :alt: Django Settings
   :target: _static/platform_admin_images/PLAT_ADM_04.png

Entity categories
^^^^^^^^^^^^^^^^^^^^^

The Platform Admin creates the categories for the Operators. Entity categories are used to classify operators (depending on the terminology used in different regulations, operators, companies, and entities may be used to refer to the same thing). 

Click the **Entity categories** link in the **Governance** section to go to the **Select entity category to change** screen. Here, you can see a list of categories (if any have been set up). You can create new categories by clicking the **Add Entity Category** button in the top right corner.

To **delete a category**, first select it by checking the box next to the category. Then, open the **Action** drop-down menu and choose the **Delete selected entity categories** option, and click Go.

.. figure:: _static/platform_admin_images/PLAT_ADM_05.png
   :alt: Delete selected entity categories
   :target: _static/platform_admin_images/PLAT_ADM_05.png

There are two columns on the **Change Entity category** screen. The **Code** column on the left displays the code you assigned to the entity when you set it up. The **Label** column indicates the type of classification you want to create for different entities in the **SERIMA** system. This is also defined when you create a new entity category or modify an existing one.

.. figure:: _static/platform_admin_images/PLAT_ADM_10.png
   :alt: Delete selected entity categories
   :target: _static/platform_admin_images/PLAT_ADM_10.png

Functionalities
^^^^^^^^^^^^^^^^^^^^^

The **Functionalities** section shows which modules are enabled in the platform. As per the screenshot below, there are two modules set up in the system: **Reporting** and **Security Objective**.

To **create a new Functionality**, click the **Add Functionality** button in the top right corner. To **delete a Functionality**, first select it by checking the box next to the functionality. Then, open the Action drop-down menu and choose the **Delete selected Functionalities** option, and click **Go**.

.. figure:: _static/platform_admin_images/PLAT_ADM_06.png
   :alt: Delete selected Functionalities
   :target: _static/platform_admin_images/PLAT_ADM_06.png

Observers
^^^^^^^^^^^^^^^^^^^^^

An observer is a type of regulator with limited permissions. Observers cannot edit incidents on the platform; they have read-only access and can only view incidents. 

As a Platform Admin, you can create an Observer either by clicking the **Add Observer** button in the top-right corner or by selecting the **Add** link in the Governance section. The **Change Observer** screen appears, where you can set up a new Observer.

When creating a new Observer, provide its name, description, country, and address. Then configure its functionalities by selecting and adding them to the **Chosen Functionalities** list:

.. figure:: _static/platform_admin_images/PLAT_ADM_11.png
   :alt: Observers - Chosen Functionalities
   :target: _static/platform_admin_images/PLAT_ADM_11.png

Finally, add observer users and observer regulations (legal basis) to the Observer. Use the down-pointing arrows to open the dropdown menus and select a different user or regulation. 

If you cannot find the item you are looking for, use the **Add another Observer user** and **Add another Observer regulation** links to create new entries.











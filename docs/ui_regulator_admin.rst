Regulator Admin
-------------------------
  
In Luxembourg, the regulator is **ILR**. `ILR <https://www.ilr.lu/>`_ can have two types of roles: **Regulator Admin** and **Regulator User**.

The //Regulator Admin** role has permission to create workflows (covering all NIS/EECC-related questionnaires) for users who are required to complete these reports, such as preliminary reports, notifications, and final assessments.

In the user interface, click the **Settings** link to go to the **Site Administration** screen (the Administration Console). 
To return to the user interface, click the **Return to user interface** link in the upper right-hand corner (circled in red in the screenshot below).

.. figure:: _static/regulator_admin_images/Reg_Admin_01.png
   :alt: Regulator Admin - Site administration
   :target: _static/regulator_admin_images/OpAdmin_01.png

The **Site Administration screen** (the Administration Interface) offers the most extensive set of features compared with the **Operator Admin**, 
**Regulator User**, and **Platform Admin** user types.

The Site administration screen has the following parts: Administration, Governance, Incident Notification, Reporting, Security Objectives, and Recent Actions. In the rest of this chapter, each feature will be discussed in detail.

.. figure:: _static/regulator_admin_images/Reg_Admin_02.png
   :alt: Regulator Admin - Site administration
   :target: _static/regulator_admin_images/Reg_Admin_02.png

Administration
~~~~~~~~~~~~~~~~~~~

In the Administration section, you can check the **Log entries** and the **Script execution logs**. 

.. figure:: _static/regulator_admin_images/Reg_Admin_03.png
   :alt: Regulator Admin - Log entries
   :target: _static/regulator_admin_images/Reg_Admin_03.png

Log entries
^^^^^^^^^^^^^^^^^^^^^^^^

Click either the **Log Entries** or **View links** to go to the **Select log entry view** screen. On this screen, you can check and filter what activity was performed, when the change occurred, which user made it, and what content type was updated. Use the **Search** field or the **Filter** section to narrow down the list.

.. figure:: _static/regulator_admin_images/Reg_Admin_04.png
   :alt: Regulator Admin - Select log entry view
   :target: _static/regulator_admin_images/Reg_Admin_04.png

By default, the list items are sorted by **Action Time** in descending order, with the most recent entry at the top and the oldest at the bottom. In this default view, there are no up or down arrows on the right side of the columns.

To sort the list items, first, select the column you want to sort and choose the **sorting order** (ascending or descending). To refine the sorting further, you can select additional columns and specify their sorting order. 

When more than one column is used for sorting, numbers appear next to the up or down arrows to indicate the **sorting sequence**. In the example below, the list of entries is sorted first by **Action Time** (descending), then by **User** (ascending), and finally by **Content Type** (descending).

.. figure:: _static/regulator_admin_images/Reg_Admin_05.png
   :alt: Select log entry view - sorting
   :target: _static/regulator_admin_images/Reg_Admin_05.png

To remove a column from sorting, hover your mouse over the number until an up-and-down triangle appears (see screenshot above). A tooltip saying **Remove from sorting** will be displayed. Click the up-and-down triangle, and the selected column will no longer be used for sorting.

Script execution logs
^^^^^^^^^^^^^^^^^^^^^^^^

The **script execution logs** screen shows the logs from your SERIMA server. The screen shows the log entries in a table format with the columns **Timestamp, Action, Object Representation**, and **Additional information**.

Click the header of any column to sort the entries by that column. An upward-facing triangle in the top-right corner of the column indicates that the entries are sorted in descending order, with older entries at the top and newer ones at the bottom.

.. figure:: _static/platform_admin_images/PLAT_ADM_21.png
   :alt: script execution logs
   :target: _static/platform_admin_images/PLAT_ADM_21.png

Clicking the triangle again reverses the sorting order. When you hover the cursor over the triangle, a pop-up labeled **Toggle Sorting** appears. A downward-facing triangle then indicates that the newest entries are at the top, and older entries are below.

.. figure:: _static/platform_admin_images/PLAT_ADM_22.png
   :alt: script execution logs
   :target: _static/platform_admin_images/PLAT_ADM_22.png

You can sort items by multiple columns. The column headers indicate the sort order, showing which column is first, second, or third in the sequence (and whether the sorting is in ascending or descending order).

.. figure:: _static/platform_admin_images/PLAT_ADM_23.png
   :alt: script execution logs
   :target: _static/platform_admin_images/PLAT_ADM_23.png

The **Object Representation** column shows what activity the script performed. In most cases, this involves deletions: typically of inactive users, users who registered but were not assigned to any company, or users who did not confirm their registration.

Governance
~~~~~~~~~~~~~~~~~~~

In the Governance section, you can find the following functionalities:

.. figure:: _static/regulator_admin_images/Reg_Admin_06.png
   :alt: Governance
   :target: _static/regulator_admin_images/Reg_Admin_06.png

On the left panel, you can see the functionalities and their links. To the right, you can see whether the Regulator Admin has write access (**Add/Change**) or only read access (**View**) for each functionality. **These permissions are set by the Platform Admin.**

Entity categories
^^^^^^^^^^^^^^^^^^^^^^^^

Click the **Entity categories** link to go to the **Select entity category view** screen. On this screen, you can see what kind of entities are defined in your system. You can view an entity on the **View Entity category** screen by clicking on its link. You can set up an entity in four different languages.

.. figure:: _static/regulator_admin_images/Reg_Admin_07.png
   :alt: Select entity category view
   :target: _static/regulator_admin_images/Reg_Admin_07.png

You only have read-only access to the Entity categories. Once you click the name of the Entity Category in the **Code** column, you will be directed to the **View Entity Category** screen:

.. figure:: _static/regulator_admin_images/Reg_Admin_09.png
   :alt: View Entity Category
   :target: _static/regulator_admin_images/Reg_Admin_09.png

Functionalities
^^^^^^^^^^^^^^^^^^^^^^^^

Click the **Functionalities** link to go to the **Select Functionality to view** screen. On this screen, you can check what kind of functionalities are defined in your system. The screenshot below shows two configured functionalities (Reporting and Security Objective):

.. figure:: _static/regulator_admin_images/Reg_Admin_08.png
   :alt: Select Functionality to view
   :target: _static/regulator_admin_images/Reg_Admin_08.png

You only have read-only access to the **Functionalities**. Once you click the name of the Functionality in the **Type** column, you will be directed to the **View Functionality** screen:

.. figure:: _static/regulator_admin_images/Reg_Admin_10.png
   :alt: View Functionality
   :target: _static/regulator_admin_images/Reg_Admin_10.png

Observers
^^^^^^^^^^^^^^^^^^^^^^^^

Click the **Observers** link to go to the **Select Observers to change** screen. On this screen, you can see what kind of Observers are defined in your system. You only have view access to the Observers screen.

.. figure:: _static/regulator_admin_images/Reg_Admin_11.png
   :alt: Select Observers to change
   :target: _static/regulator_admin_images/Reg_Admin_11.png

Click the name of the Observer in the **Name** column to view it. Once you click the name of an Observer, you will be directed to the **View Observer** screen. At the top, you can see the contact information of the chosen Observer, whereas further down, you can see the linked Observer Users and Observer Regulations.

Operators
^^^^^^^^^^^^^^^^^^^^^^^^
20






Incident Notification
~~~~~~~~~~~~~~~~~~~~~~~

Use this section to create your incident notification workflow.

Emails
^^^^^^^^^^^^^^^^^^^^^

By clicking the **Emails** link in the **Incident Notification** section, you can view the email templates that have been set up in your **SERIMA** instance. These email templates are available on the **Select Email to Change** screen and are used during the incident notification workflow.

The email templates are shown as a list in a table with the columns Name, **Subject**, and **Content**.

.. figure:: /_static/regulator_admin_images/Reg_Admin_23.png
   :alt: Select Email to Change
   :target: /_static/regulator_admin_images/Reg_Admin_23.png

Click the name of the template to see its content. The screenshot below shows an example of the **New Incident Notification** template. You can see the Name, the Subject, and the Content of the email:

.. figure:: /_static/regulator_admin_images/Reg_Admin_24.png
   :alt: New Incident Notification
   :target: /_static/regulator_admin_images/Reg_Admin_24.png

Beneath the Content area, you can see the usable placeholders you can use to replace the relevant information in your template.

.. figure:: /_static/regulator_admin_images/Reg_Admin_64.png
   :alt: New Incident Notification
   :target: /_static/regulator_admin_images/Reg_Admin_64.png

These placeholders are automatically populated and replace the relevant information whenever the email is sent. You can set up your template emails in four languages: English, French, Dutch, and German. English is the platform’s default language, so email templates are typically created in English and translated into other languages when needed.

You can switch between these four languages on the platform using the **language selector dropdown** in the top-right corner of the application. The default language is English. If you switch to another language, but the email template has not been translated into that language, the platform will fall back to English and display the English version of the email.

.. figure:: /_static/regulator_admin_images/Reg_Admin_25.png
   :alt: language selector dropdown
   :target: /_static/regulator_admin_images/Reg_Admin_25.png

Impact
^^^^^^^^^^^^^^^^^^^^^

Click the **Impact** link to go to the **Select Impacts to change** screen. On this screen, you can check which impacts are defined in your system. On the Select Impacts to change screen, you can see the impacts list in a table format with the columns **Regulations, Sector, Sub-sector**, and **Title**.

.. figure:: /_static/regulator_admin_images/Reg_Admin_26.png
   :alt: Select Impacts to change
   :target: /_static/regulator_admin_images/Reg_Admin_26.png

Depending on your needs (such as the regulations you are subject to or the sectors you operate in), you can set up different impacts. As shown in the screenshot above, you can configure impacts for the same regulation, sector, and sub-sector, with variations based on the number of users.

You can set up an impact named **DNS 1h** for a one-hour DNS service outage and add the following description (as can be seen in the screenshot below): *Moderate impact on DNS service for at least 1 hour (e.g., between 2 and 5 percent of domains unresolved or a decrease of 5 to 10 percent in DNS traffic or unavailability of 2 name servers)*.

.. figure:: /_static/regulator_admin_images/Reg_Admin_63.png
   :alt: Change Impacts
   :target: /_static/regulator_admin_images/Reg_Admin_63.png

If you have many impacts, you can use the **Search** and **Filter** features to find specific ones. In the Filter section on the right side of the screen, you can narrow down your impacts by sector or legal basis.



Select the impact or impacts you want to export by checking the box next to each relevant impact. If you want to select all impacts at once, use the first checkbox on the left of the Regulations column header.

Then, open the **Action** dropdown menu, choose **Export Selected Impact**, and click **Go**. The selected impacts will be exported to a CSV file.

.. figure:: /_static/regulator_admin_images/Reg_Admin_27.png
   :alt: Export Selected Impact
   :target: /_static/regulator_admin_images/Reg_Admin_27.png

Select the impact or impacts you want to delete by checking the box next to each relevant impact. Then, open the **Action** dropdown menu, choose **Delete Selected Impact**, and click **Go**. The selected impacts will be deleted.

.. figure:: /_static/regulator_admin_images/Reg_Admin_28.png
   :alt: Delete Selected Impact
   :target: /_static/regulator_admin_images/Reg_Admin_28.png


Incident notification workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The incident notification workflow is the most important part of the application. It allows you to set up the **environment** (entities, observers, operators, regulators, and more) and define the building blocks of a **workflow** (emails, impacts, reports, questions, and more) to create a mechanism for managing reported incidents and maintaining communication among all system stakeholders. This mechanism is the heart of the process and is called the **incident notification workflow**.

Based on the above, you can create a workflow only after the required components (essentially the entire system) have been set up, including regulators, operators, and email templates.

Click the **Incident notification workflows** link to go to the **Select Incident notification workflow to change** screen. On this screen, you can check what kind of incident notification workflows are defined in your system.

.. figure:: /_static/regulator_admin_images/Reg_Admin_30.png
   :alt: Select Incident notification workflow to change
   :target: /_static/regulator_admin_images/Reg_Admin_30.png

Click the name of the workflow you want to open. The **Change Incident Notification Workflow** screen is complex and contains several sections.

At the top is the **General** section, which displays the workflow name. Below it is the **Supervision** section, showing the **Legal basis** (regulation) and the **Regulator** (in this case, ILR). The third section (**Sectors**) lists the sectors selected for this workflow.

.. figure:: /_static/regulator_admin_images/Reg_Admin_31.png
   :alt: NIS Workflow
   :target: /_static/regulator_admin_images/Reg_Admin_31.png

When you set up a new workflow, you can select a different regulation (Legal basis) or regulator using the dropdown menus, provided these options have already been configured in your **SERIMA** instance.

The fourth section is **Notification Email**. This section contains the email templates you set up on the **Select Email to Change** screen (Incident Notification -> Emails). In a typical workflow, there are at least three email templates you should use: an opening email, a status update email, and a closing email.

.. figure:: /_static/regulator_admin_images/Reg_Admin_32.png
   :alt: Notification Email
   :target: /_static/regulator_admin_images/Reg_Admin_32.png

When an operator reports an incident, they will receive an opening email confirming that the incident has been successfully reported. An example template for an **Opening email** can be seen below:

.. figure:: /_static/regulator_admin_images/Reg_Admin_22.png
   :alt: Change Email screen
   :target: /_static/regulator_admin_images/Reg_Admin_22.png

When the status of the incident changes, the **Status update email** is sent out. When the incident is closed, the **Closing email** is used. When you set up a new workflow (or change an existing one), use the dropdown menus next to the email templates and choose a different email template –if needed:

.. figure:: /_static/regulator_admin_images/Reg_Admin_33.png
   :alt: Available email templates
   :target: /_static/regulator_admin_images/Reg_Admin_33.png

Next to the dropdown menus, you can see the following icons,

.. figure:: /_static/regulator_admin_images/Reg_Admin_65.png
   :alt: Notification email icons
   :target: /_static/regulator_admin_images/Reg_Admin_65.png

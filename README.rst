|Project continuation| |Pypi package| |Pypi status| |Python versions| |License|

================
Aldryn Forms App
================

Continuation of the deprecated project `Divio Aldryn Forms <https://github.com/divio/aldryn-forms>`_.

Aldryn Forms allows you to build flexible HTML forms for your `Aldryn <http://aldryn.com>`_ and `django CMS
<http://www.django-cms.org>`_ projects, and to integrate them directly in your pages.

Forms can be assembled using the form builder, with the familiar simple drag-and-drop interface of the django CMS
plugin system.

Submitted data is stored in the Django database, and can be explored and exported using the admin, while forms can
be configured to send a confirmation message to users.

Contributing
============

This is a an open-source project. We'll be delighted to receive your
feedback in the form of issues and pull requests. Before submitting your
pull request, please review our `contribution guidelines
<http://docs.django-cms.org/en/latest/contributing/index.html>`_.

We're grateful to all contributors who have helped create and maintain this package.
Contributors are listed at the `contributors <https://github.com/divio/aldryn-forms/graphs/contributors>`_
section.

Installation
============

Aldryn Platform Users
---------------------

Choose a site you want to install the add-on to from the dashboard. Then go to ``Apps -> Install app`` and click ``Install`` next to ``Forms`` app.

Redeploy the site.

Upgrading from < 2.0
====================
Version 2.0 introduced a new model for form data storage called ``FormSubmission``.
The old ``FormData`` model has been deprecated.
Although the ``FormData`` model's data is still accessible through the admin, all new form data will be stored in the new
``FormSubmission`` model.

Manuall Installation
--------------------

Run ``pip install djangocms-aldryn-forms``.

Update ``INSTALLED_APPS`` with ::

    INSTALLED_APPS = [
        ...
        'aldryn_forms',
        'aldryn_forms.contrib.email_notifications',
        'captcha',
        ...
    ]

Also ensure you define an `e-mail backend <https://docs.djangoproject.com/en/dev/topics/email/#dummy-backend>`_ for your app.


Creating a Form
===============

You can create forms in the admin interface now. Search for the label ``Aldryn_Forms``.

Create a CMS page and install the ``Forms`` app there (choose ``Forms`` from the ``Advanced Settings -> Application`` dropdown).

Now redeploy/restart the site again.

The above CMS site has become a forms POST landing page - a place where submission errors get displayed if there are any.


Available Plug-ins
==================

- ``FormPlugin`` plugin lets you embed certain forms on a CMS page.
- ``Fieldset`` groups fields.
- ``TextField`` renders text input.
- ``TextAreaField`` renders text input.
- ``HiddenField``
- ``PhoneField``
- ``DateField``
- ``DateTimeLocalField``
- ``TimeField``
- ``NumberField``
- ``EmailField``
- ``FileField`` renders a file upload input.
- ``MultipleFilesField``
- ``ImageField`` same as ``FileField`` but validates that the uploaded file is an image.
- ``BooleanField`` renders checkbox.
- ``SelectField`` renders single select input.
- ``MultipleSelectField``
- ``MultipleCheckboxSelectField`` renders multiple checkboxes.
- ``CaptchaField``
- ``HoneypotField``
- ``HideContentWhenPostPlugin``


Custom submissions list
=======================

To display data in the submissions list, enter in settings: ::

    ALDRYN_FORMS_SUBMISSION_LIST_DISPLAY_FIELD = "aldryn_forms.admin.display_form_submission_data"


Link to API Root
================

To set link to API Root Site, enter in settings: ::

    SITE_API_ROOT = "/api/v1/"


Middleware
==========

The standard processing of the form is that after submitting it, the form page is reloaded with a javascript redirect to the next page.
Before the redirection takes place, the user is shown the text "You will be redirected shortly".
You activate the direct redirect by adding middleware into settings.

Add middleware in settings.py: ::

    MIDDLEWARE = [
        ...
        "aldryn_forms.middleware.handle_post.HandleHttpPost"
    ]


If the HTTP request contains the ``X-Requested-With`` header with the ``XMLHttpRequest`` value, the middleware returns a JSON response.

    ::

    {'status': 'SUCCESS', 'post_ident': None, 'message': 'OK'}

or

    ::

    {'status': 'ERROR', 'form': {'name': ['This field is required.']}}


Multiple saving to the same post
================================

To activate multiple saving to the same post, use the ``ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION`` switch.
This also specifies how long the user can write to the post.
To make the whole process work, you need to run the ``aldryn_forms_send_emails`` and ``aldryn_forms_remove_expired_post_idents`` commands regularly.
The first command sends emails if it was set to do so in the form plugin. The second resets the submit identifier so that it can no longer be written to.

Activation of repeated saving to the same post.

Write in settings.py: ::

    # Send email after 30 minutes. Remove post_ident after 30 minutes.
    ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION = 30


After this entry, the ``post_ident`` parameter is added to the success url for redirection. For example ::

    /thank-you/?post_ident=HErQ2TunSAU0AhTKrNSVDtSVBoYr9gTvUCUsdpMg6AZVqzExXCK06Tm7XIznf1sw

If this identifier is added to another post, a new post is not created, but it is added to an existing post.
For this case you can use the ``Form with Ident field`` plugin, which contains a hidden field where the value is stored via javascript.


Submit form by javascript
=========================

Activating form submission via javascript ``fetch``: Add class ``submit-by-fetch`` into element ``form``.

Example: ::

    <form class="submit-by-fetch">
        ...
    </form>


Run next submit
===============

Use the ``Form with Ident field`` plugin in the administration.
In the ``run_next`` dataset parameter, enter the name of the function to be executed after receiving the response
from javascript ``fetch`` command.

Example: ::

    <form data-run_next="runNext">
        ...
    </form>

Example of ``runNext`` javascript function: ::

    function runNext(form, data) {
        ...
        for (const input of document.querySelectorAll('input.aldryn-forms-field-ident')) {
            input.value = data.post_ident
        }
        ...
    }

Submit button
=============

Before submitting the form, the browser checks by default that all mandatory fields of the form are filled in and their values are of the given type.
You can add deactivating and activating the Submit button to this behavior.
If the form is in a state where not all values are correct, the Submit button is deactivated.
If the form is in the correct state, the button is activated.
To enable this functionality, add the ``toggle-submit`` class to the ``Form`` plugin.

In the ``Form`` plugin, in the ``data-toggle_submit`` attribute, you can define your own function to handle the form state.
The function must have one boolean parameter, which determines whether the form is valid or not.

After submitting the form, the Submit button is automatically deactivated to prevent clicking the button repeatedly and submitting the form multiple times.
This behavior can be disabled by specifying the ``skip-disable-submit`` class in the ``Form`` plugin.

Input type File
===============

For the File form field, you can display the names of the attached files using javascript.
This feature is activated in the ``File upload field`` or ``Multiple files upload field`` plugin by activating the ``Enable js`` switch.
It is also possible to use the ``drag-and-drop`` class to add an area to drag and drop files onto this field.
The drop icon, placeholder text, and text for the maximum size allowed, if specified, will be displayed on the area.
In the case of a field of type ``multiple``, the maximum number of items allowed, if specified, will also be displayed.
If the form is submitted asynchronously (enabled by the ``submit-by-fetch`` class), the trash icon for removing
the file from the list will automatically appear next to the attached files.
This makes it possible for the ``multiple`` field type to insert files multiple times.

You can style the form fields with your own css styles. You can replace the default icons with your own. Define the data in the Form plugin:
data-icon_upload, data-icon_attach, data-icon_error, data-icon_trash.


Multiple post save commands
===========================

The command ``aldryn_forms_send_emails`` will send all emails that are waiting to be sent.

The command ``aldryn_forms_remove_expired_post_idents`` deletes the ``post_ident`` values for all records older than the value in ``ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION``.

Add these commands to crontab: ::

    1/10 * * * * django-admin aldryn_forms_send_emails; django-admin aldryn_forms_remove_expired_post_idents


Webhooks
========

After submitting the form it is possible to send the form data to some url using webhook. For example:


Webhook example: ::

    https://webhook.example/67d5fbee-fc40-8012-880b-ed4f8fb0491c/


Example of sent data: ::

    {
        "hostname": "example.com",
        "name": "The form name",
        "language": "en",
        "sent_at": "2025-03-17T09:39:18.202231Z",
        "form_recipients": [
            {
                "name": "Dave",
                "email": "dave@dwarf.red"
            }
        ],
        "form_data": [
            {
                "name": "name",
                "label": "Name",
                "field_occurrence": 1,
                "value": "Rimmer"
            },
            ...
        ]
    }


.. |Project continuation| image:: https://img.shields.io/badge/Continuation-Divio_Aldryn_Froms-blue
    :target: https://github.com/CZ-NIC/djangocms-aldryn-forms
    :alt: Continuation of the deprecated project "Divio Aldryn forms"
.. |Pypi package| image:: https://img.shields.io/pypi/v/djangocms-aldryn-forms.svg
    :target: https://pypi.python.org/pypi/djangocms-aldryn-forms/
    :alt: Pypi package
.. |Pypi status| image:: https://img.shields.io/pypi/status/djangocms-aldryn-forms.svg
   :target: https://pypi.python.org/pypi/djangocms-aldryn-forms
   :alt: status
.. |Python versions| image:: https://img.shields.io/pypi/pyversions/djangocms-aldryn-forms.svg
   :target: https://pypi.python.org/pypi/djangocms-aldryn-forms
   :alt: Python versions
.. |License| image:: https://img.shields.io/pypi/l/djangocms-aldryn-forms.svg
    :target: https://github.com/CZ-NIC/djangocms-aldryn-forms/blob/master/LICENSE.txt
    :alt: BSD License

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
- ``HideContentWhenPostPlugin``


Middleware
==========

Dispatch submitted form by middleware. If the HTTP header ``HTTP_X_REQUESTED_WITH`` is ``XMLHttpRequest`` a json response is returned.

Write in settings.py: ::

    MIDDLEWARE = [
        ...
        "aldryn_forms.middleware.handle_post.HandleHttpPost"
    ]

Saving to the same post
=======================

Activation of repeated saving to the same post.

Write in settings.py: ::

    # Send email after 30 minutes. Remove post_ident after 30 minutes.
    ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION = 30


After this entry, the ``post_ident`` parameter is added to the success url for redirection. For example ::

    /thank-you/?post_ident=HErQ2TunSAU0AhTKrNSVDtSVBoYr9gTvUCUsdpMg6AZVqzExXCK06Tm7XIznf1sw


Submit form by javascript
=========================

Activating form submission via javascript ``fetch``: Add class ``submit-by-fetch`` into element ``form``.

Example: ::

    <form class="submit-by-fetch">
        ...
    </form>


Run next submit
===============

Running the next function after submitting the form via js ``fetch`` is done by defining the function name in the ``run_next`` parameter:

Example: ::

    <form class="submit-by-fetch" data-run_next="runNext">
        ...
    </form>

Example of ``runNext`` javascript function: ::

    function runNext(form, data) {
        ...
        const input = form.querySelector('input[name="aldryn_form_post_ident"]')
        if (!input.value) {
            input.value = data.post_ident
            form.submit()
        }
        ...
    }


Commands
========

The command ``aldryn_forms_remove_expired_post_idents`` deletes the ``post_ident`` values for all records older than the value in ``ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION``.

The command ``aldryn_forms_send_emails`` will send all emails that are waiting to be sent.

Add these commands to crontab: ::


    1/10 * * * * django-admin aldryn_forms_remove_expired_post_idents
    1/10 * * * * django-admin aldryn_forms_send_emails



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

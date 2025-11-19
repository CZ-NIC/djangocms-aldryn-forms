=========
Changelog
=========

Unreleased
==========

8.6.0 (2025-11-19)
==================

- Append attachments into email.
- Fix links to MultipleFilesField.

8.5.0 (2025-11-14)
==================

- Add templatetag display_field_value.
- Add command aldryn_forms_set_plugin_type.

8.4.1 (2025-11-12)
==================

- Setting dependencies on lower versions.

8.4.0 (2025-11-12)
==================

- Add attribute is_private into plugins FileField, MultipleFilesField and ImageField.
- Add settings ALDRYN_FORMS_SUBMISSION_EXTRA_FIELDS for BaseFormSubmissionAdmin.get_data_for_display in admin/base.py.

8.3.1 (2025-10-22)
==================

- Expand alias version to djangocms-alias>=2.0,<4.

8.3.0 (2025-10-21)
==================

- Upgrade install_requires in setup for django-cms>=4.1,<6.
- Update tests for attribute language.
- Fix plugin_pool.get_plugin Alias.
- Remove default from field language in model FormSubmissionBase.
- FormSubmissionBase.language: avoid migrations from settings-changes.
- Changing settings.ALDRYN_FORMS_ACTION_BACKENDS would result in new migrations.
- fixate "auto_field" on app-level.
- Use plugin_pool.get_plugin() over importing from .cms_plugins directly.

8.2.0 (2025-10-02)
==================

* Render e-mail subject from constace ALDRYN_FORMS_EMAIL_SUBJECT_LANG.
* Remove HoneypotField from serialized fields.
* Remove text "Form name" from mail body and subject.

8.1.1 (2025-09-23)
==================

* Fix get_response in handle_post.
* Add default message, if form is not valid.

8.1.0 (2025-09-02)
==================

* Merge branch with tags 7.8.0 and 7.9.0.

8.0.0 (2025-06-05)
==================

* Add support of CMS 4.0
* Remove support of CMS 3.x
* Replace fields redirect_type, url and redirect_page by redirect_to in model BaseFormPlugin.
* Use djangocms_text instead of djangocms_text_ckeditor.
* Restrict python version >= 3.10.

7.9.0 (2025-07-31)
==================

* Add plugin URLField.
* Remove redundant templates.

7.8.0 (2025-06-12)
==================

* Better formatting of the html part of the sent email.
* Add header reply-to into send (postponed) notifications.

7.7.0 (2025-04-22)
==================

* Add drag-and-drop functionality.
* Add templatetag media_filer_public_link to display links to upload files.

7.6.2 (2025-04-01)
==================

* Better form submission data formatting.

7.6.1 (2025-03-28)
==================

* Use icon for toggling visibility of submitted data in the list of form posts.

7.6.0 (2025-03-26)
==================

* Add REST API support.
* Add Honeypot Field.
* Add Webhook and its transformation.
* Add field honeypot_filled into Form Submission.
* Add Admin filters.
* Add Admin search field.
* Add Admin actions: export_webhook, send_webhook, honeypot_filled_on, honeypot_filled_off.
* Add aldryn_forms.admin.display_form_submission_data.

7.5.2 (2025-02-20)
==================

* Fix commands aldryn_forms_send_emails and aldryn_forms_remove_expired_post_idents.
* Fix middleware HandleHttpPost.

7.5.1 (2025-02-20)
==================

* Fix saving form.

7.5.0 (2025-02-19)
==================

* Add support of multiple submits into one post.
* Fix double rendering of hidden input type.

7.4.2 (2025-02-05)
==================

* Fix child_plugins in get_nested_plugins.

7.4.1 (2024-08-02)
==================

* Display success message only if it is set in the form. Fix typo "Form action attribute".

7.4.0 (2024-08-02)
==================

* Add middleware HandleHttpPost.

7.3.0 (2024-08-01)
==================

* Add field use_form_action for using Absolute URL or CMS Page url in attribute form.action.

7.2.1 (2024-07-15)
==================

* Add support for Python 3.11 and 3.12.
* Fix get descendants in get_form_elements. Fix plugin attribute in get_nested_plugins.

7.2.0 (2024-06-19)
==================

* Add ALDRYN_FORMS_EMAIL_AVAILABILITY_CHECKER_CLASS for checking email availability.

7.1.0 (2024-06-18)
==================

* Add HideContentWhenPostPlugin.
* Fix finding nested plugins in function get_nested_plugins - replace AliasPlugin by descendants.

7.0.5 (2023-10-04)
==================

* Add upload svg type file.
* Fix attr multipe in RestrictedMultipleFilesField.

7.0.4 (2023-09-26)
==================

* Restrict versions in requirements. Add import django-import-export and django-formtools.

7.0.3 (2023-08-22)
==================

* Fix double class in element form.

7.0.2 (2023-08-22)
==================

* Fix order of 0013, 0014 and 0015 migrations.

7.0.1 (2023-07-31)
==================

* Do not use CaptchaField when module "captcha" is not in INSTALLED_APPS.

7.0.0 (2023-07-25)
==================

* Update code to python >= 3.7 and Django >= 3.2.


6.2.0 (2020-11-14)
==================

* Scroll the page to the submitted form success text (before the page would just reload without a success message)
* Allow to autofill the form using url parameters, eg as https://example.com/sub-page/?email=hello@example.com&name=Alex
* Fix the render of the file url in the email notifications, were just the file name was rendered before
* Fix the email notification variables render (it wasn't working for a year)
* Fix `reply_to_email` field - it wasn't possible to configure before
* Fix the form submission success message that was appearing on a non-related to the form page
* Fix a bug that would break the form when the user added spaces to a field's name
* Fix the caching bug that was breaking the page when a field was added outside of a form plugin
* Drop Python 2 support, make compatible with Django 3
* Drop the form plugin that doesn't allow to send email notifications


5.0.4 (2020-05-19)
==================

* Fix admin panel export in Django 2


5.0.1 (2020-01-06)
==================

* Add autoescape to users emails template


5.0.0 (2019-12-06)
==================

* Added support for Django 2.2
* Dropped support for Django 1.11 and Python 2
* Made django-simple-captcha package optional


4.0.1 (2019-02-12)
==================

* Fixed issue with not working validation on apphooked pages


4.0.0 (2019-02-05)
==================

* Removed multi-boilerplate support
* Added support for Django 2.0 and 2.1
* Removed support for Django < 1.11
* Adapted testing infrastructure (tox/travis) to incorporate django CMS 3.6


3.0.5 (2019-02-04)
==================

* Fixed issue with sending multiple instead of only one form on page


3.0.4 (2018-07-25)
==================

* Fixed ``ImportError`` on apphook endpoint in django CMS >= 3.5
* Fixed missing migration error on Python 3


3.0.3 (2018-04-05)
==================

* Removed some redundant code in ``BooleanFieldForm``


3.0.2 (2018-04-05)
==================

* Added missing migration dependency
* Introduced django CMS 3.5 support


3.0.1 (2018-02-19)
==================

* Add missing schema migrations


3.0.0 (2018-02-01)
==================

* New fields were added to the ``FieldPluginBase`` class, as a result, any model
  that inherits from it will need to update its migrations.
* Added new ``name`` field to customize a field's name attribute.
* Added a ``position`` field to the ``Option`` model for ordered choices support.
* Renamed the form's ``page`` field to ``redirect_page``.
* Introduced the ``BaseForm`` class to make it easier to create custom form types.
* Introduced support for customizing the input's tag ``type`` attribute.
* Introduced new ``Phone``, ``Number`` and ``Hidden`` fields.
* Introduced custom attributes support for the forms and fields.
* Refactored storage backends engine to be 'action backends'


2.3.0 (2017-12-19)
==================

* Fixed bootstrap3 templates missing custom classes
* Added support for custom storage per form


2.2.9 (2017-10-09)
==================

* Added reply-to email header support to advanced form.
* Updated translations


2.2.8 (2017-09-04)
==================

* Fixed a bug in the bootstrap3 template which prevented the multiselectfield
  from submitting values to the server.


2.2.7 (2017-08-29)
==================

* Updated translations


2.2.6 (2017-08-22)
==================

* Updated translations


2.2.5 (2017-08-21)
==================

* Marked several strings as translatable
* Updated translations


2.2.4 (2017-07-05)
==================

* Fixed AttributeError introduced by new migration
* Fixed a python 3 compatibility issue


2.2.3 (2017-07-04)
==================

* Fixed django 1.10 incompatibility in form submit view
* Add missing permissions for contrib.EmailNotificationFormPlugin


2.2.2 (2017-05-16)
==================

* Fix multiple checkbox option widget template


2.2.1 (2017-03-20)
==================

* Allow FieldPlugins to set a max_length of more than 255 chars
* Allow various fields (name, label, ..,) to be longer (255 chars)


2.2.0 (2017-03-15)
==================

* Django 1.10 support
* Dropped Django < 1.7 support (south migrations removed)


2.1.3 (2016-09-05)
==================

* Added missing ``control-label`` classes in bootstrap templates
* Fixed related_name inconsistency with django CMS 3.3.1
* Dropped support for djangoCMS < 3.2
* Introduced support for djangoCMS 3.4.0


2.1.2 (2016-06-17)
==================

* Added Transifex support
* Pulled translations from Transifex (German)
* Adapted translation strings in templates


2.1.1 (2016-03-09)
==================

* Fixed image upload field on Django >= 1.8


2.1.0 (2016-02-18)
==================

* Removed deprecated ``formdata``
* Renamed ``Email Notification Form`` to ``Form (Advanced)``
* Optimized admin export templates
* Add stripped default django templates to ``/aldryn_forms/templates``
* Implement "Advanced Settings" when configuring plugins
* Adapt default setting ``show_all_recipients`` for aldryn users
* Removed not required options from form fields
* Set default for "Field is required" to ``False``
* Fix Django 1.9 issues


2.0.4 (2016-01-20)
==================

* Show label when using radio fields
* Show help text when using radio fields
* Python 3 compatibility fixes


2.0.3 (2016-01-04)
==================

* Refactored form data and form submission export logic.
* Fixes bug in email notifications not respecting confirmation flag.
* Updates po files.


2.0.2 (2015-12-17)
==================

* Remove "South" dependency from setup.py


2.0.1 (2015-12-14)
==================

* Fixes minor bug in form data export redirect.


2.0.0 (2015-12-14)
==================

* Refactor the FormData model into FormSubmission.
* FormData is now a deprecated model.
* Form exports are now limited to one language at a time.


1.0.3 (2015-12-08)
==================

* Fixes critical bug with nested plugins.


1.0.2 (2015-12-08)
==================

* Fixes plugin ordering bug.
* Fixes TypeError on some fields because of the validator.
* Marks some strings as translatable.


1.0.1 (2015-11-26)
==================

* Allows for custom forms to opt out of a success message.


1.0.0 (2015-11-03)
==================

* Stable release


0.6.0 (2015-10-14)
==================

* adds validator on max_length fields
* cms 3.1 migration compatibility fix


0.5.1 (2015-09-29)
==================

* cms 3.1 compatibility fix


0.5.0 (2015-08-19)
==================

* added django 1.7 & 1.8 compatibility
* fixes AttributeError with orphan plugins


0.4.1 (2015-07-10)
==================

* added notification config class to support custom text variables
* allow disabling email html version
* allow hiding of email body txt format field
* fixed bug with serialized boolean value


0.4.0 (2015-07-02)
==================

* added email notification contrib app which includes new email notification form
* added html version to admin notification email text
* changed the users_notified field to a text field to support non user recipients
* hides the captcha field/value from serialized data
* cleaned up field serialization logic.


0.3.3 (2015-05-29)
==================

* added support for default values in selectfields, multiselectfields and radioselects (bootstrap).
* fixed empty values in select options


0.3.2 (2015-05-19)
==================

* bootstrap3 support
* added bootstrap markup templates for all field-types


0.3.0 (2015-03-02)
==================

* multi-boilerplate support
* new requirement: aldryn-boilerplates (needs configuration)

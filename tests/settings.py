#!/usr/bin/env python
import sys


HELPER_SETTINGS = {
    'INSTALLED_APPS': [
        'tests',
        'aldryn_forms.contrib.email_notifications',
        'djangocms_text',
        'captcha',
        'easy_thumbnails',
        'emailit',
        'filer',
    ],
    'CMS_LANGUAGES': {
        1: [{
            'code': 'en',
            'name': 'English',
        }]
    },
    'CMS_TEMPLATES': (
        ('test_fullwidth.html', 'Fullwidth'),
        ('test_page.html', 'Normal page'),
    ),
    'LANGUAGE_CODE': 'en',
    'EMAIL_BACKEND': 'django.core.mail.backends.dummy.EmailBackend',
    'CMS_CONFIRM_VERSION4': True,
}


def run():
    from djangocms_helper import runner
    extra_args = sys.argv[1:] if len(sys.argv) > 1 else []
    runner.cms('aldryn_forms', [sys.argv[0]], extra_args=extra_args)


if __name__ == '__main__':
    run()

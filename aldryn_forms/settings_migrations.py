INSTALLED_APPS = [
    "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.auth",
    "django.contrib.admin",
    "cms",
    "djangocms_alias",
    "menus",
    "easy_thumbnails",
    "treebeard",
    "filer",
    "aldryn_forms",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.i18n',
            'cms.context_processors.cms_settings',
        ],
        'loaders': [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader'
        ]
    }
}]

LANGUAGES = [
    ("en", "English"),
]
LANGUAGE_CODE = "en"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

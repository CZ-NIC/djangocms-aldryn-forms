APP = aldryn_forms
LANG_CODE ?= cs
FILEPATH = ${APP}/locale/${LANG_CODE}/LC_MESSAGES/django
TRANSLATIONS = ${FILEPATH}.po
TRANSLATIONS_JS = ${FILEPATH}js.po
COMPILATIONS = ${FILEPATH}.mo
COMPILATIONS_JS = ${FILEPATH}js.mo

.PHONY: default msg msg-compile msg-py msg-make-py msg-sort-py msg-js msg-make-js msg-sort-js test isort check-css

default: test

# Translations
msg: msg-py msg-js

msg-py: msg-make-py msg-sort-py

msg-make-py:
	unset -v DJANGO_SETTINGS_MODULE; cd ${APP} && django-admin makemessages -l cs

msg-sort-py:
	msgattrib --sort-output --no-location --no-obsolete -o ${TRANSLATIONS} ${TRANSLATIONS}

msg-js: msg-make-js msg-sort-js

msg-make-js:
	unset -v DJANGO_SETTINGS_MODULE; cd ${APP} && django-admin makemessages -l cs -d djangojs

msg-sort-js:
	msgattrib --sort-output --no-location --no-obsolete -o ${TRANSLATIONS_JS} ${TRANSLATIONS_JS}

msg-compile:
	msgfmt ${TRANSLATIONS} -o ${COMPILATIONS}
	msgfmt ${TRANSLATIONS_JS} -o ${COMPILATIONS_JS}

test:
	tox --parallel all --parallel-live

test-coverage:
	LANG=en_US.UTF-8 PYTHONPATH='./tests:${PYTHONPATH}' DJANGO_SETTINGS_MODULE='settings' coverage run --source=${APP} --branch -m django test ${APP}

isort:
	isort ${APP}

check-css:
	npm run check-css

check-js:
	npm run check-js

build-js-css:
	npm run build
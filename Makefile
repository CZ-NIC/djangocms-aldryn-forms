APP = aldryn_forms
CODES ?= cs de en fa fr it lt nl

.PHONY: help msg-make msg-compile test check-js build-js-css

help:
	@echo "make msg-make"
	@echo "    Make translations."
	@echo "make msg-compile"
	@echo "    Compile translations. Use CODES in the same way as for the msg-make."
	@echo "make test"
	@echo "    Run tests."
	@echo "make check-js:"
	@echo "    Check javascript code. Run npm -i manually before the command."
	@echo "make build-js-css"
	@echo "    Build js and css. Run npm -i manually if node_modules isn't installed yet."
	@echo ""
	@echo "Run tests in docker:"
	@echo "    docker run -t -w /app -v .:/app python:3.8 bash -c 'pip install tox; tox -e py38'"
	@echo "    sudo chown -R \$$(id -u):\$$(id -g) .tox"

# Translations
msg-make:
	@unset -v DJANGO_SETTINGS_MODULE;
	@cd ${APP} && for CODE in ${CODES}; \
	do \
		django-admin makemessages -l $$CODE; \
		django-admin makemessages -l $$CODE -d djangojs; \
		msgattrib --sort-output --no-location --no-obsolete --no-fuzzy --output-file=locale/$$CODE/LC_MESSAGES/django.po locale/$$CODE/LC_MESSAGES/django.po; \
		msgattrib --sort-output --no-location --no-obsolete --no-fuzzy --output-file=locale/$$CODE/LC_MESSAGES/djangojs.po locale/$$CODE/LC_MESSAGES/djangojs.po; \
	done

msg-compile:
	@cd ${APP}/locale && for CODE in ${CODES}; \
	do \
		echo "compile locale $$CODE"; \
		msgfmt $$CODE/LC_MESSAGES/django.po -o $$CODE/LC_MESSAGES/django.mo; \
		if [ -r $$CODE/LC_MESSAGES/djangojs.po ]; then \
			msgfmt $$CODE/LC_MESSAGES/djangojs.po -o $$CODE/LC_MESSAGES/djangojs.mo; \
		fi; \
	done

test:
	tox --parallel all --parallel-live

check-js:
	npm run check-js

build-js-css:
	npm run build

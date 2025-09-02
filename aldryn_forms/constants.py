DEFAULT_ALDRYN_FORMS_ACTION_BACKENDS = {
    'default': 'aldryn_forms.action_backends.DefaultAction',
    'email_only': 'aldryn_forms.action_backends.EmailAction',
    'none': 'aldryn_forms.action_backends.NoAction',
}
ALDRYN_FORMS_ACTION_BACKEND_KEY_MAX_SIZE = 15

ALDRYN_FORMS_POST_IDENT_NAME = "aldryn_form_post_ident"
MAX_IDENT_SIZE = 64

ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION = "ALDRYN_FORMS_MULTIPLE_SUBMISSION_DURATION"

EMAIL_REPLY_TO = "email_reply_to"

WEBHOOK_METHODS = (
    ('post', 'POST'),
    ('json', 'JSON'),
)

TRANSFORM_SCHEMA = {
    "type": "array",
    "items": {
        "$ref": "#/$defs/field"
    },
    "$defs": {
        "field": {
            "type": "object",
            "required": ["dest"],
            "oneOf": [
                {"required": ["src"]},
                {"required": ["value"]},
                {"required": ["fnc"]},
            ],
            "properties": {
                "dest": {"type": "string"},
                "value": {"type": "string"},
                "src": {"type": ["string", "array"]},
                "match": {"type": ["string", "array"]},
                "fetcher": {"enum": ["first", "all", "text"]},
                "sep": {"type": "string"},
                "fnc": {"type": "string"},
                "params": {"type": "object"},
            }
        }
    }
}

from django.core.serializers.json import DjangoJSONEncoder


class PrettyJsonEncoder(DjangoJSONEncoder):

    def __init__(self, *args, **kwargs):
        kwargs["indent"] = 2
        kwargs["sort_keys"] = False
        super().__init__(*args, **kwargs)

from django.contrib import admin

from ..models import FormSubmission, Webhook
from .options import FormSubmissionAdmin, WebhookAdmin


admin.site.register(FormSubmission, FormSubmissionAdmin)
admin.site.register(Webhook, WebhookAdmin)

# Generated by Django 4.2.6 on 2025-02-11 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aldryn_forms', '0018_formplugin_use_form_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='formsubmission',
            name='post_uuid',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]

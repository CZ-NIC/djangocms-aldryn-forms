# Generated by Django 2.2.13 on 2023-01-26 13:16

import django.db.models.deletion
from django.db import migrations, models

import djangocms_attributes_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('aldryn_forms', '0015_add_field_is_enable_autofill_from_url_params'),
    ]

    operations = [
        migrations.CreateModel(
            name='DateFieldPlugin',
            fields=[
                ('name', models.CharField(blank=True, help_text='Used to set the field name', max_length=255, verbose_name='Name')),
                ('label', models.CharField(blank=True, max_length=255, verbose_name='Label')),
                ('required', models.BooleanField(default=False, verbose_name='Field is required')),
                ('required_message', models.TextField(blank=True, help_text='Error message displayed if the required field is left empty. Default: "This field is required".', null=True, verbose_name='Error message')),
                ('placeholder_text', models.CharField(blank=True, help_text='Default text in a form. Disappears when user starts typing. Example: "email@example.com"', max_length=255, verbose_name='Placeholder text')),
                ('help_text', models.TextField(blank=True, help_text='Explanatory text displayed next to input field. Just like this one.', null=True, verbose_name='Help text')),
                ('attributes', djangocms_attributes_field.fields.AttributesField(blank=True, default=dict, verbose_name='Attributes')),
                ('min_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Min value')),
                ('max_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Max value')),
                ('initial_value', models.CharField(blank=True, help_text='Default value of field.', max_length=255, verbose_name='Initial value')),
                ('custom_classes', models.CharField(blank=True, max_length=255, verbose_name='custom css classes')),
                ('cmsplugin_ptr', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='aldryn_forms_datefieldplugin', serialize=False, to='cms.CMSPlugin')),
                ('earliest_date', models.DateField(blank=None, help_text='The earliest date to accept.', null=True, verbose_name='Earliest date')),
                ('latest_date', models.DateField(blank=None, help_text='The latest date to accept.', null=True, verbose_name='Latest date')),
                ('input_step', models.PositiveIntegerField(blank=True, help_text='The granularity numnber.', null=True, verbose_name='Step')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='DateTimeLocalFieldPlugin',
            fields=[
                ('name', models.CharField(blank=True, help_text='Used to set the field name', max_length=255, verbose_name='Name')),
                ('label', models.CharField(blank=True, max_length=255, verbose_name='Label')),
                ('required', models.BooleanField(default=False, verbose_name='Field is required')),
                ('required_message', models.TextField(blank=True, help_text='Error message displayed if the required field is left empty. Default: "This field is required".', null=True, verbose_name='Error message')),
                ('placeholder_text', models.CharField(blank=True, help_text='Default text in a form. Disappears when user starts typing. Example: "email@example.com"', max_length=255, verbose_name='Placeholder text')),
                ('help_text', models.TextField(blank=True, help_text='Explanatory text displayed next to input field. Just like this one.', null=True, verbose_name='Help text')),
                ('attributes', djangocms_attributes_field.fields.AttributesField(blank=True, default=dict, verbose_name='Attributes')),
                ('min_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Min value')),
                ('max_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Max value')),
                ('initial_value', models.CharField(blank=True, help_text='Default value of field.', max_length=255, verbose_name='Initial value')),
                ('custom_classes', models.CharField(blank=True, max_length=255, verbose_name='custom css classes')),
                ('cmsplugin_ptr', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='aldryn_forms_datetimelocalfieldplugin', serialize=False, to='cms.CMSPlugin')),
                ('earliest_datetime', models.DateTimeField(blank=None, help_text='The earliest datetime to accept.', null=True, verbose_name='Earliest datetime')),
                ('latest_datetime', models.DateTimeField(blank=None, help_text='The latest datetime to accept.', null=True, verbose_name='Latest datetime')),
                ('input_step', models.PositiveIntegerField(blank=True, help_text='The granularity numnber.', null=True, verbose_name='Step')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='TimeFieldPlugin',
            fields=[
                ('name', models.CharField(blank=True, help_text='Used to set the field name', max_length=255, verbose_name='Name')),
                ('label', models.CharField(blank=True, max_length=255, verbose_name='Label')),
                ('required', models.BooleanField(default=False, verbose_name='Field is required')),
                ('required_message', models.TextField(blank=True, help_text='Error message displayed if the required field is left empty. Default: "This field is required".', null=True, verbose_name='Error message')),
                ('placeholder_text', models.CharField(blank=True, help_text='Default text in a form. Disappears when user starts typing. Example: "email@example.com"', max_length=255, verbose_name='Placeholder text')),
                ('help_text', models.TextField(blank=True, help_text='Explanatory text displayed next to input field. Just like this one.', null=True, verbose_name='Help text')),
                ('attributes', djangocms_attributes_field.fields.AttributesField(blank=True, default=dict, verbose_name='Attributes')),
                ('min_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Min value')),
                ('max_value', models.PositiveIntegerField(blank=True, null=True, verbose_name='Max value')),
                ('initial_value', models.CharField(blank=True, help_text='Default value of field.', max_length=255, verbose_name='Initial value')),
                ('custom_classes', models.CharField(blank=True, max_length=255, verbose_name='custom css classes')),
                ('cmsplugin_ptr', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='aldryn_forms_timefieldplugin', serialize=False, to='cms.CMSPlugin')),
                ('earliest_time', models.TimeField(blank=None, help_text='The earliest time to accept.', null=True, verbose_name='Earliest time')),
                ('latest_time', models.TimeField(blank=None, help_text='The latest time to accept.', null=True, verbose_name='Latest time')),
                ('input_step', models.PositiveIntegerField(blank=True, help_text='The granularity numnber.', null=True, verbose_name='Step')),
                ('data_list', models.SlugField(blank=True, help_text='Datalist id of html element datalist with options.', null=True, verbose_name='Datalist')),
                ('readonly', models.BooleanField(default=False, help_text='The field cannot be edited by the user.', verbose_name='Read only')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.AlterField(
            model_name='formplugin',
            name='action_backend',
            field=models.CharField(choices=[('none', 'None'), ('email_only', 'Email only'), ('default', 'Default')], default='default', max_length=15, verbose_name='Action backend'),
        ),
    ]

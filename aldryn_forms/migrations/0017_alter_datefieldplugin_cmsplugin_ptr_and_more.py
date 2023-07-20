# Generated by Django 4.2.3 on 2023-07-24 09:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0022_auto_20180620_1551"),
        ("aldryn_forms", "0016_date_time_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datefieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="datetimelocalfieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="emailfieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="fieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="fieldsetplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="fileuploadfieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="fileuploadfieldplugin",
            name="enable_js",
            field=models.BooleanField(
                blank=True,
                help_text="Enable javascript to view files for upload.",
                null=True,
                verbose_name="Enable js",
            ),
        ),
        migrations.AlterField(
            model_name="formbuttonplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="formplugin",
            name="action_backend",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("email_only", "Email only"),
                    ("none", "None"),
                ],
                default="default",
                max_length=15,
                verbose_name="Action backend",
            ),
        ),
        migrations.AlterField(
            model_name="formplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="formsubmission",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="imageuploadfieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="imageuploadfieldplugin",
            name="enable_js",
            field=models.BooleanField(
                blank=True,
                help_text="Enable javascript to view files for upload.",
                null=True,
                verbose_name="Enable js",
            ),
        ),
        migrations.AlterField(
            model_name="multiplefilesuploadfieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="multiplefilesuploadfieldplugin",
            name="enable_js",
            field=models.BooleanField(
                blank=True,
                help_text="Enable javascript to view files for upload.",
                null=True,
                verbose_name="Enable js",
            ),
        ),
        migrations.AlterField(
            model_name="option",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="textareafieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
        migrations.AlterField(
            model_name="timefieldplugin",
            name="cmsplugin_ptr",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="%(app_label)s_%(class)s",
                serialize=False,
                to="cms.cmsplugin",
            ),
        ),
    ]

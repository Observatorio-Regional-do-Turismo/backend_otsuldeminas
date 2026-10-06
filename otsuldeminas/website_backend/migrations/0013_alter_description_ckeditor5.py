import django_ckeditor_5.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("website_backend", "0012_remove_contato_address_alter_contato_label_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cidade",
            name="description",
            field=django_ckeditor_5.fields.CKEditor5Field(blank=True, config_name="default"),
        ),
        migrations.AlterField(
            model_name="estado",
            name="description",
            field=django_ckeditor_5.fields.CKEditor5Field(blank=True, config_name="default"),
        ),
        migrations.AlterField(
            model_name="evento",
            name="description",
            field=django_ckeditor_5.fields.CKEditor5Field(blank=True, config_name="default"),
        ),
        migrations.AlterField(
            model_name="igr",
            name="description",
            field=django_ckeditor_5.fields.CKEditor5Field(blank=True, config_name="default"),
        ),
        migrations.AlterField(
            model_name="pontoturistico",
            name="description",
            field=django_ckeditor_5.fields.CKEditor5Field(blank=True, config_name="default"),
        ),
    ]
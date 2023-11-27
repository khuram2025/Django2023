# Generated by Django 3.2.16 on 2023-11-26 10:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0017_customfield_is_searchable'),
        ('companies', '0003_auto_20231125_1222'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='location',
            name='city',
        ),
        migrations.RemoveField(
            model_name='location',
            name='country',
        ),
        migrations.AlterField(
            model_name='location',
            name='branch',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.city'),
        ),
    ]
# Generated by Django 3.2.16 on 2023-11-19 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0016_auto_20231108_1425'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='is_searchable',
            field=models.BooleanField(default=False, verbose_name='Available for Search'),
        ),
    ]
# Generated by Django 3.2.16 on 2023-12-15 10:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0006_storeproductstockentry'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='condition',
        ),
    ]
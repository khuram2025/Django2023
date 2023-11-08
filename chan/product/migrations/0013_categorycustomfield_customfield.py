# Generated by Django 3.2.16 on 2023-11-08 11:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0012_auto_20231108_0953'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('field_type', models.CharField(choices=[('number', 'Number'), ('email', 'Email'), ('phone', 'Phone'), ('url', 'URL'), ('color', 'Color'), ('textarea', 'Textarea'), ('select', 'Select Box'), ('checkbox', 'Checkbox'), ('radio', 'Radio Button'), ('date', 'Date'), ('date_interval', 'Date Interval')], max_length=50, verbose_name='Type')),
                ('options', models.TextField(blank=True, help_text='Comma-separated values', verbose_name='Options')),
            ],
        ),
        migrations.CreateModel(
            name='CategoryCustomField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_fields', to='product.category')),
                ('custom_field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.customfield')),
            ],
        ),
    ]

# Generated by Django 5.0.6 on 2024-08-29 18:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0040_topic_category'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='should_display',
        ),
        migrations.RemoveField(
            model_name='category',
            name='user_friendly_name',
        ),
        migrations.RemoveField(
            model_name='category',
            name='user_friendly_parent_name',
        ),
        migrations.AlterField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='web.category'),
        ),
    ]

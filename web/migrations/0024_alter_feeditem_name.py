# Generated by Django 5.0.6 on 2024-07-19 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0023_alter_feed_topic_embedding'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feeditem',
            name='name',
            field=models.CharField(max_length=2000),
        ),
    ]

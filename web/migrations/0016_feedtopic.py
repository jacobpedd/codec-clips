# Generated by Django 5.0.6 on 2024-07-17 19:51

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0015_alter_userfeedfollow_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeedTopic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=1000)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('feed', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='topics', to='web.feed')),
            ],
            options={
                'unique_together': {('feed', 'text')},
            },
        ),
    ]

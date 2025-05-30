# Generated by Django 5.0.6 on 2024-08-28 01:28

import django.contrib.postgres.fields
import django.utils.timezone
import pgvector.django.indexes
import pgvector.django.vector
import web.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0037_alter_category_should_display'),
    ]

    operations = [
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('keywords', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), blank=True, null=True, size=None)),
                ('description', models.TextField(blank=True, null=True)),
                ('embedding', pgvector.django.vector.VectorField(default=web.models.default_vector, dimensions=768)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'indexes': [models.Index(fields=['name'], name='web_topic_name_862a4e_idx'), pgvector.django.indexes.HnswIndex(ef_construction=64, fields=['embedding'], m=16, name='topic_embedding_idx', opclasses=['vector_cosine_ops'])],
            },
        ),
    ]

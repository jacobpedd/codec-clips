# Generated by Django 5.0.6 on 2024-07-19 17:40

from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0019_feed_popularity_percentile"),
    ]

    operations = [VectorExtension()]

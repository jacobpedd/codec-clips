from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0009_feed_description"),
    ]

    operations = [
        TrigramExtension(),
    ]

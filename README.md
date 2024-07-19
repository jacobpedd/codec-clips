## Guides I used to setup this project:

- [Deploying django on fly with postgres](https://fly.io/django-beats/deploying-django-to-production/)
- [Setting up celery on fly](https://fly.io/django-beats/celery-async-tasks-on-fly-machines/)

## Commands

Run the django server:

```bash
python manage.py runserver
```

Run the celery redis worker:

```bash
celery -A codec worker -B -l info
```

## Setup

Need to use PostgreSQL for the database with the pg-vector extension installed to develop locally.

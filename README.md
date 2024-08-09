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

## Migrate prod DB to local DB

PG DUMP

# Proxy to local

```
fly proxy 5433 -a codec-vector-d
```

# Dump PG DB

If the connection string changes, you can change it in this command.

```
pg_dump "postgres://codec:bxoACwq4RLoELPA@localhost:5433/codec" -F c -b -v --no-owner -f db.dump
```

# Setup new local DB

```
psql
createdb codec
createuser codec
psql -c "ALTER USER codec WITH PASSWORD 'codec';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE codec TO codec;"
```

# Restore dump to local DB

```
pg_restore --clean -h localhost -p 5432 -U codec -d codec -v db.dump
```

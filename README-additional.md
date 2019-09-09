# OffenesParlament

An open-data framework for the public data of the Austrian Parliament.

Alternate README (focus on scraping)

## Installation

Create a virtualenv:

        python -m virtualenv -p python2 env

Install dependencies

        env/bin/pip install -r requirements.txt
        env/bin/pip install -r requirements.production.txt
        env/bin/pip install -r requirements.dev.txt

TODO: requirements need some fixing (?). Conflicts here and there, and e.g.
for postgres package, a binary package has to be chosen instead of the
specified one.

###  Run django admin and management commands

Run it from the virtualenv

        env/bin/python offenesparlament manage.py


### Database via docker

Start database (and optionally web interface) with the docker-compose.yml .
Either use the webinterface of the adminer tool (port 8080, user = postgres,
password = example), or open a psql shell in the container:

        docker-compose exec -u postgres db psql

        # Examples: choose database, show schema
        # More help:
        # https://www.postgresql.org/docs/10/app-psql.html
        \c database_name
        \dt

Create a database by the name of 'op'.

Create the model tables:

        env/bin/python offenesparlament manage.py migrate


### Scraping

Ready to scrape:

        # Show list of available spiders
        env/bin/python offenesparlament/manage.py scrape list

        # Run a spider, e.g. 'llp'
        env/bin/python offenesparlament/manage.py scrape crawl llp



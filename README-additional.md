# OffenesParlament

An open-data framework for the public data of the Austrian Parliament.

Alternate README (focus on scraping)

## Installation

Create a virtualenv:

        python -m virtualenv -p python2 py

Install dependencies

        py/bin/pip install -r requirements.txt
        py/bin/pip install -r requirements.production.txt
        py/bin/pip install -r requirements.dev.txt

TODO: requirements need some fixing (?). Conflicts here and there, and e.g.
for postgres package, a binary package has to be chosen instead of the
specified one.

###  Run django admin and management commands

Run it from the virtualenv

        py/bin/python offenesparlament/manage.py


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

        # Create database a by the name `op`:
        create database op;

Create a database by the name of 'op'.

Create the model tables:

        py/bin/python offenesparlament/manage.py migrate

### Notes

django and scrapy are pinned to lower versions due to depreactions:

  - django (<1.9) due to use of remove_tags
  - scrapy (<1.7) due to use of scrapy.log


### Scraping

Ready to scrape:

        # Show list of available spiders
        py/bin/python offenesparlament/manage.py scrape list

        # Run a spider, e.g. 'llp'
        py/bin/python offenesparlament/manage.py scrape crawl llp


        # Example, crawl statements of 23rd legislative perdiod
        py/bin/python offenesparlament/manage.py scrape crawl statement -a llp=23


### Quick Reference / Clipboard

Join person to party via political mandate:

        select full_name, pp.short from op_scraper_mandate m join op_scraper_person p on m.id = p.latest_mandate_id join op_scraper_party pp on m.party_id = pp.id;

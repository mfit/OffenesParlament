python remove_migrations.py && rm -f db.sqlite3 && python manage.py makemigrations && python manage.py migrate && python manage.py createsuperuser --email loki@fsinf.at --username admin

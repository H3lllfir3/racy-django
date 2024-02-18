#!/bin/bash
set -e

python scripts/wait_for_mysql.py
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata data.json
daphne -e ssl:443:privateKey=privkey.pem:certKey=cert.pem project.asgi:application 
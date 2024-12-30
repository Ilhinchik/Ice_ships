source env/bin/activate
docker compose up -d
cd bmstu
python manage.py flush
python manage.py fill_db 10
python manage.py runserver 0.0.0.0:8000
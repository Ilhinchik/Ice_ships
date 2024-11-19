source env/bin/activate
docker compose up -d
cd bmstu
sudo service redis-server start
python manage.py runserver
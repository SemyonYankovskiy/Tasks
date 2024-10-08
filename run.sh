python manage.py migrate --no-input;

export DJANGO_COLLECT_STATIC=1;
python manage.py collectstatic --no-input;
export DJANGO_COLLECT_STATIC=0;

python manage.py createsuperuser --noinput;

gunicorn --workers 5 --bind 0.0.0.0:8000 djangoProject.wsgi:application

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.development
ENV SECRET_KEY=build-only-key

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py shell -c \"from apps.users.models import CustomUser; CustomUser.objects.filter(username='admin').exists() or CustomUser.objects.create_superuser('admin', 'admin@admin.com', 'Admin1234!')\" && python manage.py runserver 0.0.0.0:8000"]

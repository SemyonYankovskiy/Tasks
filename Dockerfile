FROM python:3.12.5-alpine

ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN pip install --upgrade --no-cache-dir pip && pip install poetry --no-cache-dir;

COPY pyproject.toml poetry.lock /app/

RUN poetry config virtualenvs.create false && \
    poetry install --with dev --no-interaction --no-ansi --no-cache;

COPY . .

EXPOSE 8000

RUN chmod +x run.sh

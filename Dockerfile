ARG PYTHON_VERSION=3.10-slim

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /code

WORKDIR /code

COPY requirements.txt /tmp/requirements.txt
RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/
COPY . /code

ENV SECRET_KEY "ZuhVrLKY5AwawSFucVQwHYoGawjLVDBfMPcJZ3gKapTgjbvGCU"
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn","--bind",":8000","--workers","2","--worker-class","uvicorn.workers.UvicornWorker","fuelupy.asgi"]

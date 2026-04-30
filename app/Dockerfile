FROM tiangolo/uvicorn-gunicorn:python3.11-slim

ENV HOME=/home/fast \
    APP_HOME=/home/fast/app \
    PYTHONPATH="$PYTHONPATH:/home/fast" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir -p $APP_HOME \
 && groupadd -r fast\
 && useradd -r -g fast fast

WORKDIR $HOME

COPY app app
COPY media media
COPY requirements.txt alembic.ini .env .

RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && chown -R fast:fast .

USER fast


#  Online Shop API

Backend интернет-магазина на **FastAPI** с асинхронной работой с PostgreSQL, JWT-аутентификацией, ролевой моделью пользователей, Docker-контейнеризацией и REST API.

Проект построен как модульное backend-приложение: бизнес-логика разделена между роутерами, SQLAlchemy-моделями, Pydantic-схемами и отдельным слоем авторизации.

##  Возможности

### Пользователи и авторизация

* регистрация и авторизация пользователей;
* JWT Access Token;
* JWT Refresh Token;
* хеширование паролей с помощью `bcrypt`;
* проверка активности пользователя;
* разграничение доступа по ролям;
* роли:

  * `buyer` — покупатель;
  * `seller` — продавец;
  * `admin` — администратор.

Access Token действует 30 минут, Refresh Token — 7 дней.

### Каталог

* управление товарами;
* категории товаров;
* работа с изображениями товаров;
* получение информации о товарах через REST API.

### Корзина

* добавление товаров в корзину;
* работа с позициями корзины;
* изменение содержимого корзины.

### Заказы

* создание заказов;
* работа с заказами пользователей;
* разделение доступа к операциям в зависимости от роли пользователя.

### Отзывы

* создание отзывов;
* получение отзывов;
* работа отзывами пользователей.

Основные API-модули проекта представлены роутерами `users`, `products`, `categories`, `cart`, `orders` и `reviews`.

---

##  Технологический стек

| Технология                  | Назначение                     |
| --------------------------- | ------------------------------ |
| **Python**                  | основной язык                  |
| **FastAPI**                 | REST API                       |
| **Uvicorn**                 | ASGI-сервер                    |
| **Gunicorn**                | production process manager     |
| **PostgreSQL 16**           | база данных                    |
| **SQLAlchemy 2**            | ORM                            |
| **asyncpg**                 | асинхронный PostgreSQL-драйвер |
| **Alembic**                 | миграции базы данных           |
| **Pydantic 2**              | валидация данных               |
| **JWT**                     | аутентификация                 |
| **Passlib / bcrypt**        | хеширование паролей            |
| **Docker / Docker Compose** | контейнеризация                |
| **Nginx**                   | reverse proxy и раздача media  |
| **Loguru**                  | логирование                    |
| **Pytest**                  | тестирование                   |

Актуальные версии Python-зависимостей зафиксированы в `requirements.txt`. В частности, проект использует FastAPI 0.121.0, SQLAlchemy 2.0.44, Alembic 1.17.1, PostgreSQL-драйверы `asyncpg` и `psycopg2-binary`, PyJWT и pytest.

---

##  Архитектура проекта

```text
online_shop/
├── app/
│   ├── migrations/          # Миграции Alembic
│   │
│   ├── models/              # SQLAlchemy-модели
│   │   ├── cart_items.py
│   │   ├── categories.py
│   │   ├── orders.py
│   │   ├── products.py
│   │   ├── reviews.py
│   │   └── users.py
│   │
│   ├── routers/             # REST API endpoints
│   │   ├── cart.py
│   │   ├── categories.py
│   │   ├── orders.py
│   │   ├── products.py
│   │   ├── reviews.py
│   │   └── users.py
│   │
│   ├── auth.py              # JWT и проверка ролей
│   ├── config.py            # Конфигурация приложения
│   ├── database.py          # Подключение к БД
│   ├── db_depends.py        # DB dependencies
│   ├── main.py              # Точка входа FastAPI
│   ├── schemas.py           # Pydantic-схемы
│   └── Dockerfile
│
├── nginx/
│   └── ...                  # Конфигурация Nginx
│
├── tests/                   # Тесты
│
├── docker-compose.yml       # Production-like окружение
├── sample_docker-compose.yml
├── requirements.txt
├── alembic.ini
├── pytest.ini
├── conftest.py
└── .gitlab-ci.yml
```

Структура `models` и `routers` непосредственно отражает основные домены приложения: пользователи, товары, категории, корзина, заказы и отзывы.

---

##  Аутентификация

Для авторизации используется JWT.

Пароли пользователей не хранятся в открытом виде — перед сохранением они хешируются с использованием `bcrypt`.

JWT содержит данные пользователя и используется для проверки доступа к защищённым endpoint'ам. Для разных ролей предусмотрены отдельные зависимости:

```python
get_current_user()
get_current_buyer()
get_current_seller()
get_current_admin()
```

Таким образом, endpoint может быть ограничен не только фактом авторизации, но и конкретной ролью пользователя.

### Алгоритм JWT

```text
HS256
```

Секретный ключ загружается из переменной окружения `SECRET_KEY`.

>  Никогда не добавляйте реальный `SECRET_KEY`, пароли PostgreSQL и другие секреты в Git-репозиторий.

---

##  Запуск через Docker Compose

Рекомендуемый способ запуска проекта — Docker Compose.

### 1. Клонирование

```bash
git clone https://github.com/ivandeev93/online_shop.git
cd online_shop
```

### 2. Создание `.env`

Создайте файл `.env` в корне проекта.

Минимально необходимы параметры, используемые Docker Compose и приложением:

```env
SECRET_KEY=change-me-to-a-long-random-secret

POSTGRES_USER=shop_user
POSTGRES_PASSWORD=change-me
POSTGRES_DB=shop_db
```

Значения переменных PostgreSQL используются контейнером базы данных, а `SECRET_KEY` — приложением для подписи JWT.

### 3. Запуск контейнеров

```bash
docker compose up -d --build
```

В основном `docker-compose.yml` используются три сервиса:

```text
nginx
  │
  ▼
web (FastAPI + Gunicorn + Uvicorn)
  │
  ▼
PostgreSQL 16
```

Кроме основной базы данных, Compose также содержит отдельный PostgreSQL-контейнер для тестовой среды. Media-файлы сохраняются в отдельном Docker volume.

### 4. Проверка контейнеров

```bash
docker compose ps
```

Логи приложения:

```bash
docker compose logs -f web
```

Логи Nginx:

```bash
docker compose logs -f nginx
```

---

##  Миграции базы данных

Проект использует **Alembic** для управления схемой PostgreSQL.

После запуска окружения примените миграции:

```bash
docker compose exec web alembic upgrade head
```

Для локального запуска Alembic:

```bash
alembic upgrade head
```

Создание новой миграции:

```bash
alembic revision --autogenerate -m "describe changes"
```

Применение всех миграций:

```bash
alembic upgrade head
```

Откат последней миграции:

```bash
alembic downgrade -1
```

> Перед использованием `--autogenerate` убедитесь, что модели SQLAlchemy импортируются в metadata Alembic.

---

##  API

После запуска приложение предоставляет REST API.

FastAPI автоматически генерирует интерактивную документацию:

```text
http://localhost/docs
```

Swagger UI:

```text
http://localhost/docs
```

OpenAPI JSON:

```text
http://localhost/openapi.json
```

В исходном README проекта API также указан как endpoint на порту `8000`, однако в текущем Docker Compose production-like схема предусматривает доступ через Nginx на `80` порту.

Если запускаете FastAPI напрямую на `8000`, документация будет доступна по:

```text
http://localhost:8000/docs
```

---

##  Локальный запуск без Docker

Для разработки приложение можно запускать непосредственно из Python-окружения.

### 1. Создание virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте `.env`:

```env
SECRET_KEY=change-me-to-a-long-random-secret

POSTGRES_USER=shop_user
POSTGRES_PASSWORD=change-me
POSTGRES_DB=shop_db
```

Также необходимо, чтобы PostgreSQL был доступен приложению с соответствующими параметрами подключения.

### 4. Миграции

```bash
alembic upgrade head
```

### 5. Запуск FastAPI

```bash
uvicorn app.main:app --reload
```

После запуска:

```text
API:  http://localhost:8000
Docs: http://localhost:8000/docs
```

---

##  Тестирование

В проекте предусмотрены `pytest`, `pytest.ini`, `conftest.py` и отдельный PostgreSQL-контейнер для тестов.

Запуск тестов:

```bash
pytest
```

Запуск с подробным выводом:

```bash
pytest -v
```

Запуск конкретного теста:

```bash
pytest tests/path/to/test_file.py -v
```

Для тестового окружения в `sample_docker-compose.yml` предусмотрена отдельная база:

```text
shop_db_test
```

и PostgreSQL доступен на локальном порту `5433`.

---

##  Docker Compose: production-like окружение

В репозитории присутствуют два Compose-файла:

### `docker-compose.yml`

Основной вариант запуска. Использует:

* FastAPI;
* Gunicorn;
* Uvicorn workers;
* PostgreSQL 16;
* Nginx;
* Docker volumes для PostgreSQL и media.

### `sample_docker-compose.yml`

Более подробный пример окружения, включающий:

* healthcheck PostgreSQL;
* отдельную тестовую БД;
* Docker network;
* Nginx;
* persistent volumes;
* зависимость приложения от готовности PostgreSQL.

Пример production-команды запуска приложения:

```bash
gunicorn app.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

Эта команда соответствует конфигурации Compose в репозитории.

---

##  Работа с изображениями

Приложение создаёт директорию:

```text
media/products/
```

для изображений товаров.

В Docker media-файлы вынесены в отдельный volume:

```text
media_data
```

и подключаются одновременно к backend и Nginx. Это позволяет сохранять изображения независимо от жизненного цикла контейнера приложения.

---

##  Логирование

Для логирования используется **Loguru**.

Каждому HTTP-запросу назначается уникальный `log_id`, что позволяет связать сообщения одного запроса между собой.

Логи приложения:

```text
info.log
```

Настроены:

* уровень `INFO`;
* ротация при достижении 10 MB;
* хранение логов в течение 7 дней;
* gzip-сжатие архивов;
* асинхронная постановка записей в очередь.

Также middleware логирует HTTP-метод и путь запроса, а ошибки обрабатываются отдельно.

---

##  Middleware

В приложении используются следующие middleware:

### GZip

Сжимает HTTP-ответы размером от 1000 байт.

### TrustedHost

Ограничивает список разрешённых host'ов.

### CORS

Настроена работа с разрешёнными frontend origins.

### Request logging

Каждому запросу присваивается уникальный идентификатор для логирования.

Эти настройки находятся в `app/main.py`.

---

##  CI/CD

В репозитории присутствует `.gitlab-ci.yml` с тремя стадиями:

```text
build
  ↓
test
  ↓
deploy
```

На текущий момент pipeline содержит демонстрационные job'ы для build/test/deploy, поэтому перед использованием в production CI/CD-конфигурацию рекомендуется адаптировать под реальную инфраструктуру проекта.

---

##  Основные директории

### `app/routers`

REST API endpoints:

```text
cart.py
categories.py
orders.py
products.py
reviews.py
users.py
```

### `app/models`

SQLAlchemy-модели:

```text
cart_items.py
categories.py
orders.py
products.py
reviews.py
users.py
```

### `app/auth.py`

Отвечает за:

* хеширование паролей;
* проверку паролей;
* создание Access Token;
* создание Refresh Token;
* получение текущего пользователя;
* проверку ролей `buyer`, `seller` и `admin`.

### `app/main.py`

Точка входа приложения:

```python
app = FastAPI(...)
```

Здесь подключаются роутеры, middleware, логирование и директория media.

---

##  Быстрый старт

Если Docker уже установлен:

```bash
git clone https://github.com/ivandeev93/online_shop.git
cd online_shop
```

Создайте `.env`:

```env
SECRET_KEY=change-me-to-a-long-random-secret
POSTGRES_USER=shop_user
POSTGRES_PASSWORD=change-me
POSTGRES_DB=shop_db
```

Запустите проект:

```bash
docker compose up -d --build
```

Примените миграции:

```bash
docker compose exec web alembic upgrade head
```

После этого API будет доступно через Nginx:

```text
http://localhost
```

Документация:

```text
http://localhost/docs
```

---

##  Важные замечания

Перед использованием проекта в production рекомендуется:

* использовать длинный криптографически стойкий `SECRET_KEY`;
* не хранить `.env` в Git;
* настроить HTTPS;
* включить `HTTPSRedirectMiddleware` после корректной настройки reverse proxy;
* заменить development/test значения PostgreSQL;
* проверить и ограничить `TrustedHostMiddleware` актуальными доменами;
* настроить полноценный CI/CD вместо демонстрационных job'ов;
* добавить полноценные healthcheck'и приложения;
* настроить резервное копирование PostgreSQL;
* определить стратегию хранения media-файлов;
* проверить CORS для production frontend;
* настроить централизованный сбор логов.

---

##  Разработка

1. Создайте fork репозитория.
2. Создайте отдельную ветку:

```bash
git checkout -b feature/my-feature
```

3. Внесите изменения.
4. Добавьте/обновите тесты.
5. Проверьте:

```bash
pytest
```

6. Создайте Pull Request.

---

##  License

Информация о лицензии в текущем репозитории не представлена.

Если проект предполагается публиковать как open-source, рекомендуется добавить файл `LICENSE` и указать лицензию в этом разделе.

---

##  Автор

**ivandeev93**

Репозиторий:

https://github.com/ivandeev93/online_shop

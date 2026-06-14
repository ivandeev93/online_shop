from fastapi import FastAPI, Request
from app.routers import cart, categories, orders, products, users, reviews
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from uuid import uuid4
from fastapi.responses import JSONResponse
from loguru import logger
import os


# Папка для изображений товаров
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "..", "media")

os.makedirs(os.path.join(MEDIA_DIR, "products"), exist_ok=True)


# Добавление логирования
logger.add("info.log", format="Log: [{extra[log_id]}:{time} - {level} - {message}]",
           level="INFO", rotation="10 MB", retention="7 days", compression="zip", enqueue = True)


# Создаём приложение FastAPI
app = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    log_id = str(uuid4())

    logger_with_id = logger.bind(log_id=log_id)

    try:
        response = await call_next(request)

        if response.status_code >= 400:
            logger_with_id.warning(f"{request.method} {request.url.path}")
        else:
            logger_with_id.info(f"{request.method} {request.url.path}")

        return response

    except Exception as ex:
        logger_with_id.error(f"{request.method} {request.url.path} failed: {ex}")
        return JSONResponse(content={"success": False}, status_code=500)


app.add_middleware(GZipMiddleware, minimum_size=1000)     # Сжатие ответов приложения
#app.add_middleware(HTTPSRedirectMiddleware)               # Перенаправление с HTTP на HTTPS
app.add_middleware(
    TrustedHostMiddleware,          # Перечисление своих доменов, для защиты от DNS-атак
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "31.56.240.45",
    ]
)

# Список разрешенных источников
origins = [
    "http://31.56.240.45:3000",
    "http://31.56.240.45",
    "http://127.0.0.1:3000",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,      # - чтобы браузер мог распознавать совпадения
    allow_methods=["*"],         # адресов домена и отправлять файл cookie авторизации для разрешения запроса
    allow_headers=["*"],
)


# Подключаем маршруты категорий
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(reviews.router)
app.include_router(cart.router)
app.include_router(orders.router)

# Для обслуживания медиа файлов
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
#Теперь любой файл из media/products/ будет доступен по URL: http://localhost:8000/media/products/abc123.jpg


# Корневой эндпоинт для проверки
@app.get("/")
async def root():
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API интернет-магазина!"}

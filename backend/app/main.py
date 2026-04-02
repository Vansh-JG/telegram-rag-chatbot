from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.telegram import router as telegram_router
from app.db.weaviate_client import client as weaviate_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    weaviate_client.close()


app = FastAPI(lifespan=lifespan)

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello Bots, this is from your backend"}


app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(telegram_router, prefix="/telegram")

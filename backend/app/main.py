import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, wait_for_db
from app.routers import cadastro

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
)

wait_for_db()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Atualização Cadastral CODEGO",
    description="API para recebimento de solicitações de atualização cadastral (dados + CNPJ + Contrato Social).",
    version="0.1.0",
    # Documentação interativa (/docs, /redoc, /openapi.json) só em
    # desenvolvimento: em produção ela entregaria um mapa completo da API.
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
    openapi_url="/openapi.json" if settings.app_env == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # O site não usa cookies/credenciais; com "*" não faz sentido permitir.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(cadastro.router, prefix="/api/atualizacao-cadastral", tags=["Atualização Cadastral"])

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import Base, engine, wait_for_db
from app.routers import cadastro

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
)

logger = logging.getLogger("codego.api")

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


def _para_log(texto) -> str:
    """Uma linha só e sem caracteres de controle (o texto pode vir do formulário)."""
    return "".join(c if c.isprintable() else "?" for c in str(texto))[:300]


# O log de acesso do uvicorn só diz "422 Unprocessable Entity", sem o motivo.
# Estes handlers registram POR QUE o envio foi recusado, sem gravar o conteúdo
# digitado (só o texto da mensagem e os nomes dos campos), e mantêm exatamente
# a mesma resposta de antes para quem enviou.
@app.exception_handler(StarletteHTTPException)
async def registrar_recusa(request: Request, exc: StarletteHTTPException):
    # 404 fica de fora: é ruído de robôs varrendo rotas inexistentes.
    if exc.status_code >= 400 and exc.status_code != 404:
        logger.warning(
            "Recusado %s %s -> %s: %s",
            request.method,
            request.url.path,
            exc.status_code,
            _para_log(exc.detail),
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def registrar_validacao(request: Request, exc: RequestValidationError):
    problemas = ", ".join(
        f"{'.'.join(str(parte) for parte in erro['loc'])}:{erro['type']}" for erro in exc.errors()
    )
    logger.warning(
        "Recusado %s %s -> 422 (campos): %s", request.method, request.url.path, _para_log(problemas)
    )
    return await request_validation_exception_handler(request, exc)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(cadastro.router, prefix="/api/atualizacao-cadastral", tags=["Atualização Cadastral"])

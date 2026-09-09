import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(cadastro.router, prefix="/api/atualizacao-cadastral", tags=["Atualização Cadastral"])

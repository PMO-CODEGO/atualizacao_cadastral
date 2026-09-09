import os

from fastapi import UploadFile, HTTPException

from app.config import settings

EXTENSAO_PERMITIDA = ".pdf"
MIME_PERMITIDO = "application/pdf"


def validar_pdf(file: UploadFile, conteudo: bytes, nome_campo: str):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != EXTENSAO_PERMITIDA:
        raise HTTPException(status_code=422, detail=f"O arquivo de {nome_campo} deve ser um PDF.")
    if file.content_type != MIME_PERMITIDO:
        raise HTTPException(status_code=422, detail=f"Tipo de arquivo inválido para {nome_campo}.")

    limite = settings.max_upload_size_mb * 1024 * 1024
    if len(conteudo) > limite:
        raise HTTPException(
            status_code=413,
            detail=f"O arquivo de {nome_campo} excede o limite de {settings.max_upload_size_mb}MB.",
        )


def salvar_arquivo(conteudo: bytes, diretorio: str, nome_arquivo: str) -> str:
    os.makedirs(diretorio, exist_ok=True)
    caminho = os.path.join(diretorio, nome_arquivo)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho

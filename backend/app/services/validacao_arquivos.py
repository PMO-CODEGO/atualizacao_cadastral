import os
import zipfile

from fastapi import UploadFile, HTTPException

from app.config import settings

# Extensão -> tipos MIME aceitos para essa extensão (alguns navegadores/SOs
# enviam variações do MIME para o mesmo tipo de arquivo, por isso a lista)
TIPOS_PERMITIDOS = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # alguns navegadores relatam .docx como zip genérico
    },
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
}

EXTENSOES_DESCRICAO = "PDF, Word (.doc/.docx) ou Excel (.xls/.xlsx)"


def validar_arquivo(file: UploadFile, conteudo: bytes, nome_campo: str):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=422, detail=f"O arquivo de {nome_campo} deve ser {EXTENSOES_DESCRICAO}."
        )
    if file.content_type not in TIPOS_PERMITIDOS[ext]:
        raise HTTPException(status_code=422, detail=f"Tipo de arquivo inválido para {nome_campo}.")

    limite = settings.max_upload_size_mb * 1024 * 1024
    if len(conteudo) > limite:
        raise HTTPException(
            status_code=413,
            detail=f"O arquivo de {nome_campo} excede o limite de {settings.max_upload_size_mb}MB.",
        )


def extensao_de(file: UploadFile) -> str:
    return os.path.splitext(file.filename or "")[1].lower()


def salvar_arquivo(conteudo: bytes, diretorio: str, nome_arquivo: str) -> str:
    os.makedirs(diretorio, exist_ok=True)
    caminho = os.path.join(diretorio, nome_arquivo)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    return caminho


def criar_zip_documentos(caminhos_com_nomes: list[tuple[str, str]], diretorio: str, nome_zip: str) -> str:
    """
    Compacta os arquivos em caminhos_com_nomes (lista de (caminho_no_disco,
    nome_dentro_do_zip)) num único arquivo .zip, e retorna o caminho do zip.
    """
    os.makedirs(diretorio, exist_ok=True)
    caminho_zip = os.path.join(diretorio, nome_zip)
    with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for caminho_arquivo, nome_no_zip in caminhos_com_nomes:
            zf.write(caminho_arquivo, arcname=nome_no_zip)
    return caminho_zip

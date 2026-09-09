from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.orm import AtualizacaoCadastral
from app.schemas.atualizacao_cadastral import (
    AtualizacaoCadastralResponse,
    validar_cnpj,
    validar_cpf,
    validar_telefone,
)
from app.services.protocolo import gerar_protocolo
from app.services.validacao_arquivos import validar_pdf, salvar_arquivo
from app.services.email_service import enviar_email_atualizacao_cadastral

router = APIRouter()


@router.post("", response_model=AtualizacaoCadastralResponse, status_code=201)
async def criar_atualizacao_cadastral(
    nome_empresarial: str = Form(...),
    cnpj: str = Form(...),
    endereco: str = Form(...),
    distrito: str = Form(...),
    telefone: str = Form(...),
    email: str = Form(...),
    representante_nome: str = Form(...),
    representante_cpf: str = Form(...),
    representante_cargo: str = Form(...),
    termo_empresa_aceito: bool = Form(...),
    termo_codego_aceito: bool = Form(...),
    arquivo_cnpj: UploadFile = File(...),
    arquivo_contrato_social: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Recebe a solicitação de atualização cadastral (dados + 2 PDFs), valida tudo,
    gera um protocolo único, salva os arquivos, grava no banco e envia o e-mail
    de confirmação (com os PDFs em anexo) para o e-mail fixo da empresa.
    """
    # Validação dos campos de texto
    campos_obrigatorios = {
        "nome_empresarial": nome_empresarial,
        "endereco": endereco,
        "distrito": distrito,
        "representante_nome": representante_nome,
        "representante_cargo": representante_cargo,
    }
    for nome_campo, valor in campos_obrigatorios.items():
        if not valor or not valor.strip():
            raise HTTPException(status_code=422, detail=f"O campo '{nome_campo}' é obrigatório.")

    try:
        cnpj_digits = validar_cnpj(cnpj)
        representante_cpf_digits = validar_cpf(representante_cpf)
        telefone_digits = validar_telefone(telefone)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))

    if not termo_empresa_aceito or not termo_codego_aceito:
        raise HTTPException(
            status_code=422,
            detail="É necessário aceitar os dois termos para enviar a atualização cadastral.",
        )

    # Validação dos arquivos
    conteudo_cnpj = await arquivo_cnpj.read()
    validar_pdf(arquivo_cnpj, conteudo_cnpj, "CNPJ")

    conteudo_contrato = await arquivo_contrato_social.read()
    validar_pdf(arquivo_contrato_social, conteudo_contrato, "Contrato Social")

    # Protocolo único
    protocolo = gerar_protocolo()
    while db.query(AtualizacaoCadastral).filter(AtualizacaoCadastral.protocolo == protocolo).first():
        protocolo = gerar_protocolo()

    # Salva os arquivos
    caminho_cnpj = salvar_arquivo(conteudo_cnpj, settings.upload_dir, f"{protocolo}_cnpj.pdf")
    caminho_contrato = salvar_arquivo(
        conteudo_contrato, settings.upload_dir, f"{protocolo}_contrato_social.pdf"
    )

    # Grava no banco
    registro = AtualizacaoCadastral(
        protocolo=protocolo,
        nome_empresarial=nome_empresarial.strip(),
        cnpj=cnpj_digits,
        endereco=endereco.strip(),
        distrito=distrito.strip(),
        telefone=telefone_digits,
        email=email.strip(),
        representante_nome=representante_nome.strip(),
        representante_cpf=representante_cpf_digits,
        representante_cargo=representante_cargo.strip(),
        termo_empresa_aceito=termo_empresa_aceito,
        termo_codego_aceito=termo_codego_aceito,
        caminho_pdf_cnpj=caminho_cnpj,
        caminho_pdf_contrato_social=caminho_contrato,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    # E-mail de confirmação (sempre para o e-mail fixo da empresa, com os 2 PDFs em anexo)
    destinatario = settings.notification_email or email.strip()
    email_enviado, email_erro = enviar_email_atualizacao_cadastral(
        destinatario_email=destinatario,
        nome_empresarial=registro.nome_empresarial,
        protocolo=protocolo,
        caminhos_anexos=[caminho_cnpj, caminho_contrato],
    )

    registro.email_enviado = email_enviado
    db.commit()
    db.refresh(registro)

    return AtualizacaoCadastralResponse(
        processo=registro,
        email_enviado=email_enviado,
        email_destinatario=destinatario,
        email_erro=email_erro,
    )


@router.get("/{protocolo}")
def consultar_por_protocolo(protocolo: str, db: Session = Depends(get_db)):
    registro = (
        db.query(AtualizacaoCadastral).filter(AtualizacaoCadastral.protocolo == protocolo).first()
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")
    return registro

import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
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
from app.services.validacao_arquivos import validar_arquivo, extensao_de, salvar_arquivo
from app.services.pdf_generator import gerar_pdf_formulario
from app.services.email_service import enviar_email_atualizacao_cadastral
from app.services.recaptcha import verificar_recaptcha

router = APIRouter()

# (campo do formulário, sufixo do nome salvo, nome amigável dentro do zip)
CAMPOS_ARQUIVO = [
    ("arquivo_cnpj", "cnpj", "Comprovante_CNPJ"),
    ("arquivo_contrato_social", "contrato_social", "Contrato_Social"),
    ("arquivo_certidao_matricula", "certidao_matricula", "Certidao_Matricula_Imovel"),
    ("arquivo_contrato_ou_procuracao", "contrato_ou_procuracao", "Contrato_Social_ou_Procuracao"),
    ("arquivo_documento_identidade", "documento_identidade", "Documento_Identidade"),
]


@router.post("", response_model=AtualizacaoCadastralResponse, status_code=201)
async def criar_atualizacao_cadastral(
    nome_empresarial: str = Form(...),
    cnpj: str = Form(...),
    endereco: str = Form(...),
    email: str = Form(...),
    telefone: str = Form(...),
    ramo_atividade: str = Form(...),
    previsao_geracao_empregos: str = Form(...),
    representante_nome: str = Form(...),
    representante_cpf: str = Form(...),
    representante_telefone: str = Form(...),
    representante_email: str = Form(...),
    termo_empresa_aceito: bool = Form(...),
    termo_codego_aceito: bool = Form(...),
    g_recaptcha_response: str = Form(default=""),
    arquivo_cnpj: UploadFile = File(...),
    arquivo_contrato_social: UploadFile = File(...),
    arquivo_certidao_matricula: UploadFile = File(...),
    arquivo_contrato_ou_procuracao: UploadFile = File(...),
    arquivo_documento_identidade: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Recebe a solicitação de atualização cadastral (dados + 5 arquivos), valida
    tudo, gera um protocolo único, gera o PDF timbrado do formulário
    preenchido, salva os arquivos, compacta tudo (os 5 anexos + o PDF do
    formulário) num único .zip, grava no banco e envia o e-mail de
    confirmação (com o .zip em anexo) para o e-mail fixo da empresa.
    """
    campos_obrigatorios = {
        "nome_empresarial": nome_empresarial,
        "endereco": endereco,
        "ramo_atividade": ramo_atividade,
        "previsao_geracao_empregos": previsao_geracao_empregos,
        "representante_nome": representante_nome,
    }
    for nome_campo, valor in campos_obrigatorios.items():
        if not valor or not valor.strip():
            raise HTTPException(status_code=422, detail=f"O campo '{nome_campo}' é obrigatório.")

    try:
        cnpj_digits = validar_cnpj(cnpj)
        representante_cpf_digits = validar_cpf(representante_cpf)
        telefone_digits = validar_telefone(telefone)
        representante_telefone_digits = validar_telefone(representante_telefone)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))

    if not termo_empresa_aceito or not termo_codego_aceito:
        raise HTTPException(
            status_code=422,
            detail="É necessário aceitar os dois termos para enviar a atualização cadastral.",
        )

    recaptcha_ok, recaptcha_erro = verificar_recaptcha(g_recaptcha_response)
    if not recaptcha_ok:
        raise HTTPException(status_code=422, detail=recaptcha_erro)

    arquivos_recebidos = {
        "arquivo_cnpj": arquivo_cnpj,
        "arquivo_contrato_social": arquivo_contrato_social,
        "arquivo_certidao_matricula": arquivo_certidao_matricula,
        "arquivo_contrato_ou_procuracao": arquivo_contrato_ou_procuracao,
        "arquivo_documento_identidade": arquivo_documento_identidade,
    }
    nomes_amigaveis = {
        "arquivo_cnpj": "Comprovante de Inscrição CNPJ",
        "arquivo_contrato_social": "Cópia do Contrato Social",
        "arquivo_certidao_matricula": "Certidão de Matrícula do Imóvel",
        "arquivo_contrato_ou_procuracao": "Contrato Social ou Procuração",
        "arquivo_documento_identidade": "Documento de Identidade",
    }

    conteudos = {}
    for campo, arquivo in arquivos_recebidos.items():
        conteudo = await arquivo.read()
        validar_arquivo(arquivo, conteudo, nomes_amigaveis[campo])
        conteudos[campo] = conteudo

    # Protocolo único
    protocolo = gerar_protocolo()
    while db.query(AtualizacaoCadastral).filter(AtualizacaoCadastral.protocolo == protocolo).first():
        protocolo = gerar_protocolo()

    # Gera o PDF timbrado do formulário preenchido
    nome_empresarial_strip = nome_empresarial.strip()
    endereco_strip = endereco.strip()
    email_strip = email.strip()
    ramo_atividade_strip = ramo_atividade.strip()
    previsao_geracao_empregos_strip = previsao_geracao_empregos.strip()
    representante_nome_strip = representante_nome.strip()
    representante_email_strip = representante_email.strip()

    caminho_pdf_formulario = gerar_pdf_formulario(
        protocolo=protocolo,
        nome_empresarial=nome_empresarial_strip,
        cnpj=cnpj_digits,
        endereco=endereco_strip,
        email=email_strip,
        telefone=telefone_digits,
        ramo_atividade=ramo_atividade_strip,
        previsao_geracao_empregos=previsao_geracao_empregos_strip,
        representante_nome=representante_nome_strip,
        representante_cpf=representante_cpf_digits,
        representante_telefone=representante_telefone_digits,
        representante_email=representante_email_strip,
    )

    # Salva cada arquivo enviado com a extensão original (pdf/doc/docx/xls/xlsx)
    caminhos = {}
    for campo, sufixo, _ in CAMPOS_ARQUIVO:
        arquivo = arquivos_recebidos[campo]
        ext = extensao_de(arquivo)
        caminhos[campo] = salvar_arquivo(
            conteudos[campo], settings.upload_dir, f"{protocolo}_{sufixo}{ext}"
        )

    # Lista dos 6 arquivos (PDF do formulário + os 5 anexos) para enviar como
    # anexos separados no e-mail -- sem compactar em .zip.
    caminhos_para_email = [caminho_pdf_formulario] + [
        caminhos[campo] for campo, _, _ in CAMPOS_ARQUIVO
    ]

    # Grava no banco
    registro = AtualizacaoCadastral(
        protocolo=protocolo,
        nome_empresarial=nome_empresarial_strip,
        cnpj=cnpj_digits,
        endereco=endereco_strip,
        email=email_strip,
        telefone=telefone_digits,
        ramo_atividade=ramo_atividade_strip,
        previsao_geracao_empregos=previsao_geracao_empregos_strip,
        representante_nome=representante_nome_strip,
        representante_cpf=representante_cpf_digits,
        representante_telefone=representante_telefone_digits,
        representante_email=representante_email_strip,
        termo_empresa_aceito=termo_empresa_aceito,
        termo_codego_aceito=termo_codego_aceito,
        caminho_pdf_formulario=caminho_pdf_formulario,
        caminho_pdf_cnpj=caminhos["arquivo_cnpj"],
        caminho_pdf_contrato_social=caminhos["arquivo_contrato_social"],
        caminho_pdf_certidao_matricula=caminhos["arquivo_certidao_matricula"],
        caminho_pdf_contrato_ou_procuracao=caminhos["arquivo_contrato_ou_procuracao"],
        caminho_pdf_documento_identidade=caminhos["arquivo_documento_identidade"],
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    # E-mail de confirmação (sempre para o e-mail fixo da empresa, com os 6
    # arquivos como anexos separados)
    destinatario = settings.notification_email or email_strip
    email_enviado, email_erro = enviar_email_atualizacao_cadastral(
        destinatario_email=destinatario,
        nome_empresarial=registro.nome_empresarial,
        protocolo=protocolo,
        caminhos_anexos=caminhos_para_email,
    )

    registro.email_enviado = email_enviado
    db.commit()
    db.refresh(registro)

    return AtualizacaoCadastralResponse(
        processo=registro,
        email_enviado=email_enviado,
        email_destinatario=destinatario,
        email_erro=email_erro,
        pdf_download_url=f"/api/atualizacao-cadastral/{protocolo}/pdf",
    )


@router.get("/{protocolo}")
def consultar_por_protocolo(protocolo: str, db: Session = Depends(get_db)):
    registro = (
        db.query(AtualizacaoCadastral).filter(AtualizacaoCadastral.protocolo == protocolo).first()
    )
    if registro is None:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado.")
    return registro


@router.get("/{protocolo}/pdf")
def baixar_pdf_formulario(protocolo: str, db: Session = Depends(get_db)):
    """Disponibiliza o PDF timbrado do formulário preenchido para download."""
    registro = (
        db.query(AtualizacaoCadastral).filter(AtualizacaoCadastral.protocolo == protocolo).first()
    )
    if registro is None or not registro.caminho_pdf_formulario:
        raise HTTPException(status_code=404, detail="PDF não encontrado para este protocolo.")
    if not os.path.exists(registro.caminho_pdf_formulario):
        raise HTTPException(status_code=404, detail="Arquivo do PDF não está mais disponível no servidor.")

    return FileResponse(
        registro.caminho_pdf_formulario,
        media_type="application/pdf",
        filename=f"{protocolo}_formulario_atualizacao_cadastral.pdf",
    )

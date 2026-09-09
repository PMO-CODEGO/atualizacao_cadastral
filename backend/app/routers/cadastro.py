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
    email: str = Form(...),
    telefone: str = Form(...),
    ramo_atividade: str = Form(...),
    representante_nome: str = Form(...),
    representante_cpf: str = Form(...),
    representante_telefone: str = Form(...),
    representante_email: str = Form(...),
    termo_empresa_aceito: bool = Form(...),
    termo_codego_aceito: bool = Form(...),
    arquivo_cnpj: UploadFile = File(...),
    arquivo_contrato_social: UploadFile = File(...),
    arquivo_certidao_matricula: UploadFile = File(...),
    arquivo_contrato_ou_procuracao: UploadFile = File(...),
    arquivo_documento_identidade: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Recebe a solicitação de atualização cadastral (dados + 5 PDFs), valida tudo,
    gera um protocolo único, salva os arquivos, grava no banco e envia o e-mail
    de confirmação (com os PDFs em anexo) para o e-mail fixo da empresa.
    """
    campos_obrigatorios = {
        "nome_empresarial": nome_empresarial,
        "endereco": endereco,
        "ramo_atividade": ramo_atividade,
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

    # Validação dos 5 arquivos
    arquivos_para_validar = [
        (arquivo_cnpj, "Comprovante de Inscrição CNPJ"),
        (arquivo_contrato_social, "Cópia do Contrato Social"),
        (arquivo_certidao_matricula, "Certidão de Matrícula do Imóvel"),
        (arquivo_contrato_ou_procuracao, "Contrato Social ou Procuração"),
        (arquivo_documento_identidade, "Documento de Identidade"),
    ]
    conteudos = {}
    for arquivo, nome_campo in arquivos_para_validar:
        conteudo = await arquivo.read()
        validar_pdf(arquivo, conteudo, nome_campo)
        conteudos[nome_campo] = conteudo

    # Protocolo único
    protocolo = gerar_protocolo()
    while db.query(AtualizacaoCadastral).filter(AtualizacaoCadastral.protocolo == protocolo).first():
        protocolo = gerar_protocolo()

    # Salva os arquivos
    caminho_cnpj = salvar_arquivo(
        conteudos["Comprovante de Inscrição CNPJ"], settings.upload_dir, f"{protocolo}_cnpj.pdf"
    )
    caminho_contrato_social = salvar_arquivo(
        conteudos["Cópia do Contrato Social"], settings.upload_dir, f"{protocolo}_contrato_social.pdf"
    )
    caminho_certidao = salvar_arquivo(
        conteudos["Certidão de Matrícula do Imóvel"],
        settings.upload_dir,
        f"{protocolo}_certidao_matricula.pdf",
    )
    caminho_contrato_ou_procuracao = salvar_arquivo(
        conteudos["Contrato Social ou Procuração"],
        settings.upload_dir,
        f"{protocolo}_contrato_ou_procuracao.pdf",
    )
    caminho_documento_identidade = salvar_arquivo(
        conteudos["Documento de Identidade"],
        settings.upload_dir,
        f"{protocolo}_documento_identidade.pdf",
    )

    # Grava no banco
    registro = AtualizacaoCadastral(
        protocolo=protocolo,
        nome_empresarial=nome_empresarial.strip(),
        cnpj=cnpj_digits,
        endereco=endereco.strip(),
        email=email.strip(),
        telefone=telefone_digits,
        ramo_atividade=ramo_atividade.strip(),
        representante_nome=representante_nome.strip(),
        representante_cpf=representante_cpf_digits,
        representante_telefone=representante_telefone_digits,
        representante_email=representante_email.strip(),
        termo_empresa_aceito=termo_empresa_aceito,
        termo_codego_aceito=termo_codego_aceito,
        caminho_pdf_cnpj=caminho_cnpj,
        caminho_pdf_contrato_social=caminho_contrato_social,
        caminho_pdf_certidao_matricula=caminho_certidao,
        caminho_pdf_contrato_ou_procuracao=caminho_contrato_ou_procuracao,
        caminho_pdf_documento_identidade=caminho_documento_identidade,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    # E-mail de confirmação (sempre para o e-mail fixo da empresa, com os 5 PDFs em anexo)
    destinatario = settings.notification_email or email.strip()
    email_enviado, email_erro = enviar_email_atualizacao_cadastral(
        destinatario_email=destinatario,
        nome_empresarial=registro.nome_empresarial,
        protocolo=protocolo,
        caminhos_anexos=[
            caminho_cnpj,
            caminho_contrato_social,
            caminho_certidao,
            caminho_contrato_ou_procuracao,
            caminho_documento_identidade,
        ],
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

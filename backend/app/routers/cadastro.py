import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.orm import AtualizacaoCadastral
from app.schemas.atualizacao_cadastral import (
    AtualizacaoCadastralResponse,
    validar_cnpj,
    validar_cpf,
    validar_email,
    validar_telefone,
    validar_texto_seguro,
)
from app.services.seguranca import gerar_token_download, token_download_valido
from app.services.protocolo import gerar_protocolo
from app.services.validacao_arquivos import (
    MAX_ARQUIVOS_POR_CAMPO,
    SEPARADOR_CAMINHOS,
    validar_arquivo,
    extensao_de,
    salvar_arquivo,
)
from app.services.pdf_generator import gerar_pdf_formulario
from app.services.email_service import enviar_email_atualizacao_cadastral
from app.services.recaptcha import verificar_recaptcha

router = APIRouter()

# (campo do formulário, sufixo do nome salvo, nome amigável dentro do zip)
CAMPOS_ARQUIVO = [
    ("arquivo_cnpj", "cnpj", "Comprovante_CNPJ"),
    ("arquivo_contrato_social", "contrato_social", "Contrato_Social"),
    ("arquivo_certidao_matricula", "certidao_matricula", "Certidao_Matricula_Escritura_Contrato"),
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
    arquivo_cnpj: List[UploadFile] = File(...),
    arquivo_contrato_social: List[UploadFile] = File(...),
    arquivo_certidao_matricula: List[UploadFile] = File(...),
    arquivo_contrato_ou_procuracao: List[UploadFile] = File(...),
    arquivo_documento_identidade: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Recebe a solicitação de atualização cadastral (dados + documentos; cada
    campo aceita mais de um arquivo), valida
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
        # E-mails com formato válido (também impede HTML/código no campo, que
        # iria parar dentro do PDF e do e-mail enviados).
        email = validar_email(email, "E-mail da empresa")
        representante_email = validar_email(representante_email, "E-mail do representante")

        # Os limites de tamanho espelham as colunas String(N) de models/orm.py.
        nome_empresarial = validar_texto_seguro(nome_empresarial, "Nome Empresarial", tamanho_max=255)
        endereco = validar_texto_seguro(endereco, "Endereço", tamanho_max=500)
        ramo_atividade = validar_texto_seguro(ramo_atividade, "Ramo de Atividade", tamanho_max=255)
        previsao_geracao_empregos = validar_texto_seguro(
            previsao_geracao_empregos, "Previsão de geração de empregos", tamanho_max=255
        )
        representante_nome = validar_texto_seguro(
            representante_nome, "Nome do representante", tamanho_max=255
        )
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
        "arquivo_certidao_matricula": "Certidão de Matrícula ou Escritura ou Contrato de Compra e Venda ou Escritura Pública",
        "arquivo_contrato_ou_procuracao": "Contrato Social ou Procuração",
        "arquivo_documento_identidade": "Documento de Identidade",
    }

    # Cada campo recebe uma lista de arquivos: valida todos antes de salvar.
    # Os anexos seguem juntos num único e-mail, e o provedor recusa mensagens
    # acima de 20MB (o base64 aumenta o tamanho em ~33%), então o total dos
    # anexos também tem limite -- além do limite por arquivo.
    limite_total = settings.max_total_upload_size_mb * 1024 * 1024
    total_bytes = 0
    conteudos = {}
    for campo, lista in arquivos_recebidos.items():
        if not lista:
            raise HTTPException(
                status_code=422, detail=f"Envie pelo menos um arquivo em '{nomes_amigaveis[campo]}'."
            )
        if len(lista) > MAX_ARQUIVOS_POR_CAMPO:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No campo '{nomes_amigaveis[campo]}' envie no máximo "
                    f"{MAX_ARQUIVOS_POR_CAMPO} arquivos."
                ),
            )
        conteudos[campo] = []
        for arquivo in lista:
            conteudo = await arquivo.read()
            validar_arquivo(arquivo, conteudo, nomes_amigaveis[campo])
            total_bytes += len(conteudo)
            if total_bytes > limite_total:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"O total dos anexos excede o limite de "
                        f"{settings.max_total_upload_size_mb}MB. Reduza o tamanho ou a "
                        f"quantidade de arquivos e tente novamente."
                    ),
                )
            conteudos[campo].append(conteudo)

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

    # Salva cada arquivo enviado com a extensão original (pdf/doc/docx/xls/xlsx).
    # Com mais de um arquivo no campo, o nome ganha um número (_1, _2, ...).
    caminhos = {}  # campo -> lista de caminhos
    for campo, sufixo, _ in CAMPOS_ARQUIVO:
        lista = arquivos_recebidos[campo]
        caminhos[campo] = []
        for indice, arquivo in enumerate(lista, start=1):
            ext = extensao_de(arquivo)
            numero = f"_{indice}" if len(lista) > 1 else ""
            caminhos[campo].append(
                salvar_arquivo(
                    conteudos[campo][indice - 1], settings.upload_dir, f"{protocolo}_{sufixo}{numero}{ext}"
                )
            )

    # Lista de todos os arquivos (PDF do formulário + todos os anexos) para
    # enviar como anexos separados no e-mail -- sem compactar em .zip.
    caminhos_para_email = [caminho_pdf_formulario] + [
        caminho for campo, _, _ in CAMPOS_ARQUIVO for caminho in caminhos[campo]
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
        caminho_pdf_cnpj=SEPARADOR_CAMINHOS.join(caminhos["arquivo_cnpj"]),
        caminho_pdf_contrato_social=SEPARADOR_CAMINHOS.join(caminhos["arquivo_contrato_social"]),
        caminho_pdf_certidao_matricula=SEPARADOR_CAMINHOS.join(caminhos["arquivo_certidao_matricula"]),
        caminho_pdf_contrato_ou_procuracao=SEPARADOR_CAMINHOS.join(caminhos["arquivo_contrato_ou_procuracao"]),
        caminho_pdf_documento_identidade=SEPARADOR_CAMINHOS.join(caminhos["arquivo_documento_identidade"]),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    # E-mail de confirmação (sempre para o e-mail fixo da empresa, com todos os
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
        # Link assinado: sem o token (que só quem enviou o formulário recebe)
        # não dá para baixar o PDF só adivinhando o protocolo.
        pdf_download_url=(
            f"/api/atualizacao-cadastral/{protocolo}/pdf?token={gerar_token_download(protocolo)}"
        ),
    )


# A consulta pública por protocolo (GET /{protocolo}) foi removida de propósito:
# devolvia todos os dados cadastrais (CNPJ, CPF, telefones, e-mails) para
# qualquer pessoa que adivinhasse um protocolo.


@router.get("/{protocolo}/pdf")
def baixar_pdf_formulario(
    protocolo: str,
    token: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """Disponibiliza o PDF timbrado do formulário preenchido para download (só com o link assinado)."""
    # Mesma resposta para "token errado" e "protocolo inexistente", para não
    # revelar quais protocolos existem.
    if not token_download_valido(protocolo, token):
        raise HTTPException(status_code=404, detail="PDF não encontrado para este protocolo.")

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

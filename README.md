# Atualização Cadastral CODEGO

Sistema para recebimento de solicitações de atualização cadastral de empresas
vinculadas aos distritos geridos pela Companhia de Desenvolvimento Econômico
de Goiás (CODEGO).

Diferente do [sistema_cadastral_codego](../sistema_cadastral_codego) (que gera
um documento para download → assinatura → reenvio), este projeto é de
**etapa única**: a empresa preenche os dados, anexa os dois documentos exigidos
(CNPJ e Contrato Social, em PDF) e envia direto — sem precisar gerar e assinar
nenhum documento depois.

## Stack

- **Front-end:** HTML + CSS puro
- **Back-end:** Python (FastAPI)
- **Banco de Dados:** MySQL
- **Infraestrutura:** Docker Compose
- **E-mail:** SMTP genérico (Brevo, Gmail) ou Outlook/Hotmail via Microsoft Graph API

## Fluxo da aplicação

1. A empresa acessa o formulário e lê os dois termos de compromisso (o da
   própria empresa, sobre veracidade das informações, e o da CODEGO, sobre uso
   e proteção dos dados — LGPD).
2. Marca os dois checkboxes de concordância.
3. Anexa os PDFs do CNPJ e do Contrato Social.
4. Preenche os demais dados: nome empresarial, CNPJ, endereço, distrito
   vinculado, telefone, e-mail, e os dados do representante legal (nome, CPF,
   cargo).
5. Envia. O sistema valida tudo, gera um protocolo único, salva os arquivos e
   envia um e-mail de confirmação — com os dois PDFs em anexo — para o e-mail
   fixo da empresa (`NOTIFICATION_EMAIL`), não para o e-mail preenchido no
   formulário.

## Estrutura do projeto

```
atualizacao_cadastral/
├── backend/
│   └── app/
│       ├── routers/       # Endpoint de cadastro
│       ├── models/        # Modelo ORM (SQLAlchemy)
│       ├── schemas/       # Validação (Pydantic)
│       └── services/      # Protocolo, validação de arquivos, e-mail
├── frontend/
│   ├── index.html          # Formulário único
│   ├── css/
│   ├── js/
│   └── assets/
├── database/migrations/
│   └── 001_schema_inicial.sql
├── docker/
│   └── Dockerfile
└── docker-compose.yml
```

## Campos do formulário

**Termos (checkboxes obrigatórios):**
- Termo da empresa (compromisso de veracidade das informações)
- Termo da CODEGO (uso e proteção dos dados, conforme LGPD)

**Uploads (PDF, obrigatórios):**
1. CNPJ
2. Contrato Social

**Dados (todos obrigatórios):**
- Nome Empresarial / Razão Social
- CNPJ (número)
- Endereço completo
- Distrito/Loteamento vinculado
- Telefone
- E-mail
- Nome do representante legal
- CPF do representante legal
- Cargo/função do representante

## Setup local

```bash
cp .env.example .env
docker compose up --build
```

- Front-end: `http://localhost:8081`
- API: `http://localhost:8000` (dentro do container) / `http://localhost:8001` (do host)
- MySQL exposto em `localhost:3308` (evita conflito com o sistema_cadastral_codego, que usa 3307)

> Portas diferentes do sistema_cadastral_codego de propósito, para os dois
> projetos poderem rodar ao mesmo tempo na mesma máquina, se necessário.

## Configuração de e-mail

Mesmo processo do sistema_cadastral_codego — veja o README daquele projeto
para o passo a passo completo (Brevo, ou Outlook/Hotmail via Microsoft Graph
API com OAuth2, incluindo o cadastro do app no Azure e o login único).

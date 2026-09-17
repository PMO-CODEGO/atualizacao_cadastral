// Local (Docker) usa localhost:8001. Publicado (Netlify), aponta pro back-end
// real no Render.
const RENDER_API_URL = 'https://atualizacao-cadastral-0cay.onrender.com';

const EH_AMBIENTE_LOCAL = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE_URL = window.CODEGO_API_BASE_URL || (EH_AMBIENTE_LOCAL ? 'http://localhost:8001' : RENDER_API_URL);
const MAX_UPLOAD_SIZE_MB = 10;

const form = document.getElementById('form-atualizacao');
const submitButton = document.getElementById('btn-submit');
const feedbackEl = document.getElementById('feedback');

const ARQUIVOS = [
  'arquivo_cnpj',
  'arquivo_contrato_social',
  'arquivo_certidao_matricula',
  'arquivo_contrato_ou_procuracao',
  'arquivo_documento_identidade',
];

function onlyDigits(value) {
  return value.replace(/\D/g, '');
}

function maskCnpj(digits) {
  return digits
    .slice(0, 14)
    .replace(/(\d{2})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1/$2')
    .replace(/(\d{4})(\d{1,2})$/, '$1-$2');
}

function maskCpf(digits) {
  return digits
    .slice(0, 11)
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
}

function maskTelefone(digits) {
  const d = digits.slice(0, 11);
  if (d.length <= 10) {
    return d
      .replace(/(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{4})(\d{1,4})$/, '$1-$2');
  }
  return d
    .replace(/(\d{2})(\d)/, '($1) $2')
    .replace(/(\d{5})(\d{1,4})$/, '$1-$2');
}

function maskCep(digits) {
  return digits.slice(0, 8).replace(/(\d{5})(\d{1,3})$/, '$1-$2');
}

document.getElementById('cnpj').addEventListener('input', (e) => {
  e.target.value = maskCnpj(onlyDigits(e.target.value));
});
document.getElementById('representante_cpf').addEventListener('input', (e) => {
  e.target.value = maskCpf(onlyDigits(e.target.value));
});
document.getElementById('telefone').addEventListener('input', (e) => {
  e.target.value = maskTelefone(onlyDigits(e.target.value));
});
document.getElementById('representante_telefone').addEventListener('input', (e) => {
  e.target.value = maskTelefone(onlyDigits(e.target.value));
});
document.getElementById('endereco_cep').addEventListener('input', (e) => {
  e.target.value = maskCep(onlyDigits(e.target.value));
});

function setupFilePreview(inputId) {
  const input = document.getElementById(inputId);
  const selecionadoEl = document.getElementById(`${inputId}-selecionado`);
  input.addEventListener('change', () => {
    const file = input.files[0];
    if (!file) {
      selecionadoEl.hidden = true;
      return;
    }
    selecionadoEl.textContent = `Selecionado: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)`;
    selecionadoEl.hidden = false;
    clearError(inputId);
  });
}
ARQUIVOS.forEach(setupFilePreview);

function setError(fieldName, message) {
  const errorEl = document.querySelector(`[data-error-for="${fieldName}"]`);
  if (!errorEl) return;
  const field = document.getElementById(fieldName);
  if (field) field.closest('.field')?.classList.add('field--invalid');
  errorEl.textContent = message;
}

function clearError(fieldName) {
  const errorEl = document.querySelector(`[data-error-for="${fieldName}"]`);
  if (!errorEl) return;
  const field = document.getElementById(fieldName);
  if (field) field.closest('.field')?.classList.remove('field--invalid');
  errorEl.textContent = '';
}

function validateEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

const EXTENSOES_PERMITIDAS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx'];
const MIME_PERMITIDOS = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/zip', // alguns navegadores relatam .docx/.xlsx como zip genérico
];

function validarArquivo(inputId) {
  const input = document.getElementById(inputId);
  const file = input.files[0];
  if (!file) {
    setError(inputId, 'Selecione o arquivo (PDF, Word ou Excel).');
    return false;
  }
  const nomeArquivo = file.name.toLowerCase();
  const extensaoValida = EXTENSOES_PERMITIDAS.some((ext) => nomeArquivo.endsWith(ext));
  const mimeValido = MIME_PERMITIDOS.includes(file.type) || file.type === '';
  if (!extensaoValida || !mimeValido) {
    setError(inputId, 'O arquivo deve ser PDF, Word (.doc/.docx) ou Excel (.xls/.xlsx).');
    return false;
  }
  if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    setError(inputId, `O arquivo excede o limite de ${MAX_UPLOAD_SIZE_MB}MB.`);
    return false;
  }
  clearError(inputId);
  return true;
}

const CAMPOS_TEXTO_OBRIGATORIOS = [
  ['nome_empresarial', 'Informe o nome da empresa.'],
  ['endereco_distrito', 'Informe o distrito.'],
  ['endereco_logradouro', 'Informe o logradouro.'],
  ['endereco_quadra', 'Informe a quadra.'],
  ['endereco_lote_modulo', 'Informe o lote/módulo.'],
  ['ramo_atividade', 'Informe o ramo de atividade.'],
  ['previsao_geracao_empregos', 'Informe a previsão de geração de empregos.'],
  ['representante_nome', 'Informe o nome do representante ou procurador.'],
];

function validateForm() {
  let valid = true;

  for (const [id, mensagem] of CAMPOS_TEXTO_OBRIGATORIOS) {
    const el = document.getElementById(id);
    if (!el.value.trim()) {
      setError(id, mensagem);
      valid = false;
    } else {
      clearError(id);
    }
  }

  const cnpjDigits = onlyDigits(document.getElementById('cnpj').value);
  if (cnpjDigits.length !== 14) {
    setError('cnpj', 'CNPJ deve ter 14 dígitos.');
    valid = false;
  } else {
    clearError('cnpj');
  }

  const cepDigits = onlyDigits(document.getElementById('endereco_cep').value);
  if (cepDigits.length !== 8) {
    setError('endereco_cep', 'CEP deve ter 8 dígitos.');
    valid = false;
  } else {
    clearError('endereco_cep');
  }

  const emailValue = document.getElementById('email').value.trim();
  if (!validateEmail(emailValue)) {
    setError('email', 'Informe um e-mail válido.');
    valid = false;
  } else {
    clearError('email');
  }

  const telDigits = onlyDigits(document.getElementById('telefone').value);
  if (telDigits.length < 10) {
    setError('telefone', 'Informe um telefone válido, com DDD.');
    valid = false;
  } else {
    clearError('telefone');
  }

  const cpfDigits = onlyDigits(document.getElementById('representante_cpf').value);
  if (cpfDigits.length !== 11) {
    setError('representante_cpf', 'CPF deve ter 11 dígitos.');
    valid = false;
  } else {
    clearError('representante_cpf');
  }

  const repTelDigits = onlyDigits(document.getElementById('representante_telefone').value);
  if (repTelDigits.length < 10) {
    setError('representante_telefone', 'Informe um telefone válido, com DDD.');
    valid = false;
  } else {
    clearError('representante_telefone');
  }

  const repEmailValue = document.getElementById('representante_email').value.trim();
  if (!validateEmail(repEmailValue)) {
    setError('representante_email', 'Informe um e-mail válido.');
    valid = false;
  } else {
    clearError('representante_email');
  }

  if (!document.getElementById('termo_empresa_aceito').checked) {
    setError('termo_empresa_aceito', 'É necessário concordar com este termo.');
    valid = false;
  } else {
    clearError('termo_empresa_aceito');
  }

  if (!document.getElementById('termo_codego_aceito').checked) {
    setError('termo_codego_aceito', 'É necessário concordar com este termo.');
    valid = false;
  } else {
    clearError('termo_codego_aceito');
  }

  ARQUIVOS.forEach((inputId) => {
    if (!validarArquivo(inputId)) {
      valid = false;
    }
  });

  if (typeof grecaptcha !== 'undefined' && !grecaptcha.getResponse()) {
    setError('recaptcha', 'Confirme que você não é um robô.');
    valid = false;
  } else {
    clearError('recaptcha');
  }

  return valid;
}

function showFeedback(html, type) {
  feedbackEl.innerHTML = html;
  feedbackEl.className = `feedback feedback--${type}`;
  feedbackEl.hidden = false;
  feedbackEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideFeedback() {
  feedbackEl.hidden = true;
  feedbackEl.innerHTML = '';
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? 'Enviando…' : 'Enviar atualização cadastral';
}

function extrairMensagemErro(payload) {
  if (!payload) return 'Não foi possível enviar a solicitação. Tente novamente.';
  if (typeof payload.detail === 'string') return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((erro) => erro.msg || 'Campo inválido.').join(' ');
  }
  return 'Não foi possível enviar a solicitação. Tente novamente.';
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  hideFeedback();

  if (!validateForm()) {
    return;
  }

  const distrito = document.getElementById('endereco_distrito').value.trim();
  const logradouro = document.getElementById('endereco_logradouro').value.trim();
  const quadra = document.getElementById('endereco_quadra').value.trim();
  const loteModulo = document.getElementById('endereco_lote_modulo').value.trim();
  const cep = document.getElementById('endereco_cep').value.trim();
  const enderecoCompleto = `Distrito ${distrito}, ${logradouro}, Quadra ${quadra}, Lote/Módulo ${loteModulo}, CEP ${cep}`;

  const formData = new FormData();
  formData.append('nome_empresarial', document.getElementById('nome_empresarial').value.trim());
  formData.append('cnpj', document.getElementById('cnpj').value);
  formData.append('endereco', enderecoCompleto);
  formData.append('email', document.getElementById('email').value.trim());
  formData.append('telefone', document.getElementById('telefone').value);
  formData.append('ramo_atividade', document.getElementById('ramo_atividade').value.trim());
  formData.append('previsao_geracao_empregos', document.getElementById('previsao_geracao_empregos').value.trim());
  formData.append('representante_nome', document.getElementById('representante_nome').value.trim());
  formData.append('representante_cpf', document.getElementById('representante_cpf').value);
  formData.append('representante_telefone', document.getElementById('representante_telefone').value);
  formData.append('representante_email', document.getElementById('representante_email').value.trim());
  formData.append('termo_empresa_aceito', document.getElementById('termo_empresa_aceito').checked);
  formData.append(
    'g_recaptcha_response',
    typeof grecaptcha !== 'undefined' ? grecaptcha.getResponse() : ''
  );
  formData.append('termo_codego_aceito', document.getElementById('termo_codego_aceito').checked);
  ARQUIVOS.forEach((inputId) => {
    formData.append(inputId, document.getElementById(inputId).files[0]);
  });

  setLoading(true);

  try {
    const response = await fetch(`${API_BASE_URL}/api/atualizacao-cadastral`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      showFeedback(
        `<p class="feedback__title">Não foi possível enviar a solicitação</p><p>${extrairMensagemErro(data)}</p>`,
        'error'
      );
      return;
    }

    const protocolo = data.processo.protocolo;
    const avisoEmail = data.email_enviado
      ? `<p class="feedback__email-status feedback__email-status--ok">✓ Uma cópia foi enviada para ${data.email_destinatario}.</p>`
      : `<p class="feedback__email-status feedback__email-status--warn">Os dados foram salvos, mas não foi possível enviar a confirmação por e-mail.${data.email_erro ? ` <code>${data.email_erro}</code>` : ''}</p>`;

    const pdfUrl = `${API_BASE_URL}${data.pdf_download_url}`;

    showFeedback(
      `<p class="feedback__title">Atualização cadastral enviada com sucesso</p>
       <p class="feedback__protocolo">Protocolo: ${protocolo}</p>
       ${avisoEmail}
       <div class="feedback__actions">
         <a class="feedback__link" href="${pdfUrl}" target="_blank" rel="noopener">Baixar PDF do cadastro</a>
       </div>`,
      'success'
    );

    form.reset();
    document.querySelectorAll('.file-drop__selected').forEach((el) => (el.hidden = true));
  } catch (error) {
    showFeedback(
      `<p class="feedback__title">Falha de conexão</p><p>Não foi possível falar com o servidor. Verifique se a API está em execução e tente novamente.</p>`,
      'error'
    );
  } finally {
    setLoading(false);
    if (typeof grecaptcha !== 'undefined') {
      grecaptcha.reset();
    }
  }
});

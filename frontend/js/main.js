const API_BASE_URL = window.CODEGO_API_BASE_URL || 'http://localhost:8001';
const MAX_UPLOAD_SIZE_MB = 10;

const form = document.getElementById('form-atualizacao');
const submitButton = document.getElementById('btn-submit');
const feedbackEl = document.getElementById('feedback');

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

document.getElementById('cnpj').addEventListener('input', (e) => {
  e.target.value = maskCnpj(onlyDigits(e.target.value));
});
document.getElementById('representante_cpf').addEventListener('input', (e) => {
  e.target.value = maskCpf(onlyDigits(e.target.value));
});
document.getElementById('telefone').addEventListener('input', (e) => {
  e.target.value = maskTelefone(onlyDigits(e.target.value));
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
setupFilePreview('arquivo_cnpj');
setupFilePreview('arquivo_contrato_social');

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

function validarArquivo(input, fieldName) {
  const file = input.files[0];
  if (!file) {
    setError(fieldName, 'Selecione o arquivo em PDF.');
    return false;
  }
  const nomeArquivo = file.name.toLowerCase();
  if (!nomeArquivo.endsWith('.pdf') || file.type !== 'application/pdf') {
    setError(fieldName, 'O arquivo deve estar no formato PDF.');
    return false;
  }
  if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    setError(fieldName, `O arquivo excede o limite de ${MAX_UPLOAD_SIZE_MB}MB.`);
    return false;
  }
  clearError(fieldName);
  return true;
}

const CAMPOS_TEXTO_OBRIGATORIOS = [
  ['nome_empresarial', 'Informe o nome empresarial.'],
  ['endereco', 'Informe o endereço da empresa.'],
  ['distrito', 'Informe o distrito/loteamento vinculado.'],
  ['representante_nome', 'Informe o nome do representante legal.'],
  ['representante_cargo', 'Informe o cargo/função do representante.'],
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

  const telDigits = onlyDigits(document.getElementById('telefone').value);
  if (telDigits.length < 10) {
    setError('telefone', 'Informe um telefone válido, com DDD.');
    valid = false;
  } else {
    clearError('telefone');
  }

  const emailValue = document.getElementById('email').value.trim();
  if (!validateEmail(emailValue)) {
    setError('email', 'Informe um e-mail válido.');
    valid = false;
  } else {
    clearError('email');
  }

  const cpfDigits = onlyDigits(document.getElementById('representante_cpf').value);
  if (cpfDigits.length !== 11) {
    setError('representante_cpf', 'CPF deve ter 11 dígitos.');
    valid = false;
  } else {
    clearError('representante_cpf');
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

  const arquivoCnpjValido = validarArquivo(document.getElementById('arquivo_cnpj'), 'arquivo_cnpj');
  const arquivoContratoValido = validarArquivo(
    document.getElementById('arquivo_contrato_social'),
    'arquivo_contrato_social'
  );
  if (!arquivoCnpjValido || !arquivoContratoValido) {
    valid = false;
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

  const formData = new FormData();
  formData.append('nome_empresarial', document.getElementById('nome_empresarial').value.trim());
  formData.append('cnpj', document.getElementById('cnpj').value);
  formData.append('endereco', document.getElementById('endereco').value.trim());
  formData.append('distrito', document.getElementById('distrito').value.trim());
  formData.append('telefone', document.getElementById('telefone').value);
  formData.append('email', document.getElementById('email').value.trim());
  formData.append('representante_nome', document.getElementById('representante_nome').value.trim());
  formData.append('representante_cpf', document.getElementById('representante_cpf').value);
  formData.append('representante_cargo', document.getElementById('representante_cargo').value.trim());
  formData.append('termo_empresa_aceito', document.getElementById('termo_empresa_aceito').checked);
  formData.append('termo_codego_aceito', document.getElementById('termo_codego_aceito').checked);
  formData.append('arquivo_cnpj', document.getElementById('arquivo_cnpj').files[0]);
  formData.append('arquivo_contrato_social', document.getElementById('arquivo_contrato_social').files[0]);

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

    showFeedback(
      `<p class="feedback__title">Atualização cadastral enviada com sucesso</p>
       <p class="feedback__protocolo">Protocolo: ${protocolo}</p>
       ${avisoEmail}`,
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
  }
});

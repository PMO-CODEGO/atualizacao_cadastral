// Local (Docker) usa localhost:8001. Publicado (Netlify), aponta pro back-end
// real no Render.
const RENDER_API_URL = 'https://atualizacao-cadastral-34di.onrender.com';

const EH_AMBIENTE_LOCAL = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE_URL = window.CODEGO_API_BASE_URL || (EH_AMBIENTE_LOCAL ? 'http://localhost:8001' : RENDER_API_URL);
const MAX_UPLOAD_SIZE_MB = 10;
// Sem resposta do servidor em 5 minutos (upload lento + servidor iniciando +
// processamento), a tela mostra o erro em vez de ficar presa em "Enviando…".
const TIMEOUT_ENVIO_MS = 5 * 60 * 1000;

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

function maskCep(digits) {
  return digits.slice(0, 8).replace(/(\d{5})(\d{1,3})$/, '$1-$2');
}

const cepInput = document.getElementById('cep_busca');
const cepStatusEl = document.getElementById('cep_busca-status');
const enderecoInput = document.getElementById('endereco');

cepInput.addEventListener('input', (e) => {
  e.target.value = maskCep(onlyDigits(e.target.value));
  cepStatusEl.textContent = '';
  cepStatusEl.className = 'field__hint';
});

cepInput.addEventListener('blur', async () => {
  const cepDigits = onlyDigits(cepInput.value);
  if (cepDigits.length !== 8) {
    return;
  }

  cepStatusEl.textContent = 'Buscando endereço...';
  cepStatusEl.className = 'field__hint';

  try {
    const response = await fetch(`https://viacep.com.br/ws/${cepDigits}/json/`);
    const dados = await response.json();

    if (dados.erro) {
      cepStatusEl.textContent = 'CEP não encontrado. Preencha o endereço manualmente.';
      cepStatusEl.className = 'field__hint field__hint--warn';
      return;
    }

    const partes = [dados.logradouro, dados.bairro, `${dados.localidade}-${dados.uf}`]
      .filter((parte) => parte && parte.trim());
    const enderecoEncontrado = partes.join(', ');

    if (!enderecoInput.value.trim()) {
      enderecoInput.value = `${enderecoEncontrado}, CEP ${maskCep(cepDigits)}`;
    }

    cepStatusEl.textContent = `Endereço encontrado: ${enderecoEncontrado}. Complete com Distrito/Quadra/Módulo, se necessário.`;
    cepStatusEl.className = 'field__hint field__hint--ok';
    clearError('endereco');
  } catch (error) {
    cepStatusEl.textContent = 'Não foi possível consultar o CEP agora. Preencha o endereço manualmente.';
    cepStatusEl.className = 'field__hint field__hint--warn';
  }
});

// Cada campo aceita vários arquivos. O <input type="file"> só guarda a última
// seleção, então a lista de arquivos de cada campo fica aqui e vai crescendo a
// cada "Escolher arquivos" (dá para juntar arquivos de pastas diferentes).
const MAX_ARQUIVOS_POR_CAMPO = 5;
const arquivosPorCampo = {};
ARQUIVOS.forEach((id) => { arquivosPorCampo[id] = []; });

function formatarTamanho(bytes) {
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
}

function renderizarListaArquivos(inputId) {
  const listaEl = document.getElementById(`${inputId}-selecionado`);
  const arquivos = arquivosPorCampo[inputId];
  listaEl.innerHTML = '';
  if (!arquivos.length) {
    listaEl.hidden = true;
    return;
  }
  arquivos.forEach((file, indice) => {
    const item = document.createElement('li');
    const nome = document.createElement('span');
    nome.textContent = `${file.name} (${formatarTamanho(file.size)})`;
    const remover = document.createElement('button');
    remover.type = 'button';
    remover.className = 'file-list__remove';
    remover.textContent = 'Remover';
    remover.setAttribute('aria-label', `Remover ${file.name}`);
    remover.addEventListener('click', () => {
      arquivosPorCampo[inputId].splice(indice, 1);
      renderizarListaArquivos(inputId);
    });
    item.append(nome, remover);
    listaEl.appendChild(item);
  });
  listaEl.hidden = false;
}

function setupFilePreview(inputId) {
  const input = document.getElementById(inputId);
  input.addEventListener('change', () => {
    const novos = Array.from(input.files);
    // Limpa o input para o mesmo arquivo poder ser escolhido de novo depois.
    input.value = '';
    let excedeuLimite = false;
    novos.forEach((file) => {
      const jaExiste = arquivosPorCampo[inputId].some(
        (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified
      );
      if (jaExiste) return;
      if (arquivosPorCampo[inputId].length >= MAX_ARQUIVOS_POR_CAMPO) {
        excedeuLimite = true;
        return;
      }
      arquivosPorCampo[inputId].push(file);
    });
    renderizarListaArquivos(inputId);
    if (excedeuLimite) {
      setError(inputId, `Limite de ${MAX_ARQUIVOS_POR_CAMPO} arquivos neste campo. Remova algum para adicionar outro.`);
    } else {
      clearError(inputId);
    }
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
  const arquivos = arquivosPorCampo[inputId];
  if (!arquivos.length) {
    setError(inputId, 'Selecione pelo menos um arquivo (PDF, Word ou Excel).');
    return false;
  }
  for (const file of arquivos) {
    const nomeArquivo = file.name.toLowerCase();
    const extensaoValida = EXTENSOES_PERMITIDAS.some((ext) => nomeArquivo.endsWith(ext));
    const mimeValido = MIME_PERMITIDOS.includes(file.type) || file.type === '';
    if (!extensaoValida || !mimeValido) {
      setError(inputId, `"${file.name}" não é válido. Use PDF, Word (.doc/.docx) ou Excel (.xls/.xlsx).`);
      return false;
    }
    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      setError(inputId, `"${file.name}" excede o limite de ${MAX_UPLOAD_SIZE_MB}MB.`);
      return false;
    }
  }
  clearError(inputId);
  return true;
}

const PADRAO_TEXTO_SEGURO = /^[A-Za-zÀ-ÖØ-öø-ÿ0-9\s.,\-/&()'ºª]+$/;
const TAMANHO_MAX_PALAVRA = 40;

function validarTextoSeguro(valor) {
  if (!PADRAO_TEXTO_SEGURO.test(valor)) {
    return 'Não use caracteres especiais (@, #, $, %, etc.) neste campo.';
  }
  if (valor.split(/\s+/).some((palavra) => palavra.length > TAMANHO_MAX_PALAVRA)) {
    return 'Este campo contém um texto muito longo sem espaços.';
  }
  return null;
}

const CAMPOS_TEXTO_OBRIGATORIOS = [
  ['nome_empresarial', 'Informe o nome da empresa.'],
  ['endereco', 'Informe o endereço completo.'],
  ['ramo_atividade', 'Informe o ramo de atividade.'],
  ['previsao_geracao_empregos', 'Informe a previsão de geração de empregos.'],
  ['representante_nome', 'Informe o nome do representante ou procurador.'],
];

function validateForm() {
  let valid = true;

  for (const [id, mensagem] of CAMPOS_TEXTO_OBRIGATORIOS) {
    const el = document.getElementById(id);
    const valor = el.value.trim();
    if (!valor) {
      setError(id, mensagem);
      valid = false;
      continue;
    }
    const erroTexto = validarTextoSeguro(valor);
    if (erroTexto) {
      setError(id, erroTexto);
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

function extrairMensagemErro(payload, status) {
  if (!payload) {
    return status
      ? `O servidor respondeu com erro (HTTP ${status}). Tente novamente em instantes.`
      : 'Não foi possível enviar a solicitação. Tente novamente.';
  }
  if (typeof payload.detail === 'string') return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((erro) => erro.msg || 'Campo inválido.').join(' ');
  }
  return 'Não foi possível enviar a solicitação. Tente novamente.';
}

function formatarTempo(segundos) {
  return `${Math.floor(segundos / 60)}:${String(segundos % 60).padStart(2, '0')}`;
}

// Mostra o andamento do envio: tempo corrido e, depois de 20s, um aviso de que
// arquivos grandes, conexão lenta ou servidor iniciando podem demorar.
// Retorna a função que para o contador.
function iniciarAndamentoEnvio() {
  const inicio = performance.now();
  showFeedback(
    '<p class="feedback__title">Enviando…</p><p class="feedback__espera"></p>',
    'info'
  );
  const textoEl = feedbackEl.querySelector('.feedback__espera');

  const atualizar = () => {
    const segundos = Math.floor((performance.now() - inicio) / 1000);
    submitButton.textContent = `Enviando… ${formatarTempo(segundos)}`;
    textoEl.textContent = segundos < 20
      ? 'Enviando os dados e documentos. Aguarde e não feche esta página.'
      : 'Ainda enviando. Arquivos grandes ou uma conexão lenta podem levar alguns minutos, e o servidor pode estar iniciando (na primeira vez leva até 1 minuto). Não feche nem recarregue esta página.';
  };

  atualizar();
  const timer = setInterval(atualizar, 1000);
  return () => clearInterval(timer);
}

function escapeHtml(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// Dados do momento do erro, para a gente descobrir a causa sem depender de log.
function linhasContexto(inicioEnvio, arquivos) {
  const totalBytes = arquivos.reduce((soma, file) => soma + file.size, 0);
  const conexao = navigator.connection ? navigator.connection.effectiveType : 'n/d';
  return [
    `Data/hora: ${new Date().toLocaleString('pt-BR')}`,
    `Servidor: ${API_BASE_URL}`,
    `Tempo até o erro: ${((performance.now() - inicioEnvio) / 1000).toFixed(1)}s`,
    `Anexos: ${arquivos.length} arquivo(s), ${formatarTamanho(totalBytes)}`,
    `Internet do navegador: ${navigator.onLine ? 'conectado' : 'sem conexão'} (tipo: ${conexao})`,
    `Navegador: ${navigator.userAgent}`,
  ];
}

// Bloco "Detalhes técnicos" que acompanha qualquer erro: a pessoa pode copiar
// e mandar para o suporte. Montado com textContent (nada vira HTML).
function mostrarDetalhesTecnicos(linhas) {
  const texto = linhas.join('\n');

  const detalhes = document.createElement('details');
  detalhes.className = 'feedback__details';
  detalhes.open = true;

  const resumo = document.createElement('summary');
  resumo.textContent = 'Detalhes técnicos (envie ao suporte se o erro continuar)';

  const bloco = document.createElement('pre');
  bloco.textContent = texto;

  const copiar = document.createElement('button');
  copiar.type = 'button';
  copiar.className = 'feedback__copy';
  copiar.textContent = 'Copiar detalhes';
  copiar.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(texto);
      copiar.textContent = 'Copiado!';
    } catch (erro) {
      copiar.textContent = 'Selecione o texto acima e copie';
    }
  });

  detalhes.append(resumo, bloco, copiar);
  feedbackEl.appendChild(detalhes);
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
  // Mesmo nome de campo repetido: o servidor recebe a lista de arquivos.
  ARQUIVOS.forEach((inputId) => {
    arquivosPorCampo[inputId].forEach((file) => formData.append(inputId, file));
  });

  const arquivosEnviados = ARQUIVOS.flatMap((inputId) => arquivosPorCampo[inputId]);
  const inicioEnvio = performance.now();

  setLoading(true);
  const pararAndamento = iniciarAndamentoEnvio();
  const controlador = new AbortController();
  const temporizador = setTimeout(() => controlador.abort(), TIMEOUT_ENVIO_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/api/atualizacao-cadastral`, {
      method: 'POST',
      body: formData,
      signal: controlador.signal,
    });

    // Lê como texto e tenta JSON: respostas de erro de proxy/servidor (500,
    // 502...) nem sempre são JSON e antes sumiam sem nenhuma pista.
    const corpo = await response.text();
    let data = null;
    try {
      data = JSON.parse(corpo);
    } catch (erroJson) {
      data = null;
    }

    if (!response.ok) {
      showFeedback(
        `<p class="feedback__title">Não foi possível enviar a solicitação</p><p>${escapeHtml(extrairMensagemErro(data, response.status))}</p>`,
        'error'
      );
      mostrarDetalhesTecnicos([
        `Erro: o servidor respondeu HTTP ${response.status} ${response.statusText}`.trim(),
        `Resposta do servidor: ${data ? JSON.stringify(data).slice(0, 500) : (corpo.slice(0, 300) || '(vazia)')}`,
        ...linhasContexto(inicioEnvio, arquivosEnviados),
      ]);
      return;
    }

    const protocolo = data.processo.protocolo;
    const avisoEmail = data.email_enviado
      ? `<p class="feedback__email-status feedback__email-status--ok">✓ Uma cópia foi enviada para ${escapeHtml(data.email_destinatario)}.</p>`
      : `<p class="feedback__email-status feedback__email-status--warn">Os dados foram salvos, mas não foi possível enviar a confirmação por e-mail.${data.email_erro ? ` <code>${escapeHtml(data.email_erro)}</code>` : ''}</p>`;

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
    ARQUIVOS.forEach((inputId) => {
      arquivosPorCampo[inputId] = [];
      renderizarListaArquivos(inputId);
    });
  } catch (error) {
    const tempoEsgotado = error && error.name === 'AbortError';
    const minutos = TIMEOUT_ENVIO_MS / 60000;
    showFeedback(
      tempoEsgotado
        ? `<p class="feedback__title">O servidor demorou demais para responder</p><p>Não recebemos resposta em ${minutos} minutos. O cadastro pode ter sido recebido mesmo assim: antes de enviar de novo, entre em contato com a CODEGO e informe os detalhes técnicos abaixo.</p>`
        : `<p class="feedback__title">Falha de conexão</p><p>O navegador não conseguiu receber a resposta do servidor. Pode ser instabilidade na internet, ou o servidor estar iniciando ou com erro interno. Aguarde um minuto e tente novamente.</p>`,
      'error'
    );
    mostrarDetalhesTecnicos([
      tempoEsgotado
        ? `Erro: tempo esgotado (${minutos} min) sem resposta do servidor`
        : `Erro: ${error && error.name ? error.name : 'Error'}: ${error && error.message ? error.message : String(error)}`,
      ...linhasContexto(inicioEnvio, arquivosEnviados),
    ]);
  } finally {
    pararAndamento();
    clearTimeout(temporizador);
    setLoading(false);
    if (typeof grecaptcha !== 'undefined') {
      grecaptcha.reset();
    }
  }
});

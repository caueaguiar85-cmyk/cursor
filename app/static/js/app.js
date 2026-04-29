/* ══════════════════════════════════════��════════════════════════════════════
   Stoken Advisory — Platform JS
   Client-side routing, sidebar, theme toggle
   ════════════════════���══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function() {
  initThemeToggle();
  initSidebar();
  initRouter();
  initTimeline();
  initNovaEntrevista();
  initLogout();
  initUserManagement();
  initCurrentUser();
  initFormExportImport();
  initOnlineForm();
  initAreaFilter();
  initStrategy();
  initRoadmap();
  try { initAgents(); } catch(e) { console.warn('Agents init:', e); }
  initVexia();
});

/* ── Toast Notification ────────────────────────────────────────────── */
function showToast(message, type) {
  type = type || 'info';
  var toast = document.createElement('div');
  toast.className = 'toast-notification toast-' + type;
  toast.textContent = message;
  toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:10000;padding:14px 24px;border-radius:10px;font-size:0.95rem;font-weight:500;color:#fff;box-shadow:0 4px 24px rgba(0,0,0,.18);opacity:0;transition:opacity .3s ease;max-width:420px;';
  if (type === 'info') toast.style.background = 'var(--accent, #6366f1)';
  else if (type === 'success') toast.style.background = '#22c55e';
  else if (type === 'warning') toast.style.background = '#f59e0b';
  else toast.style.background = '#ef4444';
  document.body.appendChild(toast);
  requestAnimationFrame(function() { toast.style.opacity = '1'; });
  setTimeout(function() {
    toast.style.opacity = '0';
    setTimeout(function() { toast.remove(); }, 400);
  }, 4000);
}

/* ── Theme Toggle ──────��───────────────────────────────────────────────── */
function initThemeToggle() {
  var btn = document.getElementById('theme-toggle');
  if (!btn) return;

  btn.addEventListener('click', function() {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var next = isDark ? 'light' : 'dark';

    if (next === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    localStorage.setItem('theme', next);
  });
}

/* ── Sidebar ──────���────────────────────────────────────────────────────── */
function initSidebar() {
  var sidebar = document.getElementById('sidebar');
  var collapseBtn = document.getElementById('sidebar-collapse');
  var mobileBtn = document.getElementById('sidebar-mobile-btn');

  if (collapseBtn && sidebar) {
    collapseBtn.addEventListener('click', function() {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
    });

    // Restore collapsed state
    if (localStorage.getItem('sidebar-collapsed') === 'true') {
      sidebar.classList.add('collapsed');
    }
  }

  // Mobile toggle
  if (mobileBtn && sidebar) {
    mobileBtn.addEventListener('click', function() {
      sidebar.classList.toggle('mobile-open');
    });

    // Close on click outside
    document.addEventListener('click', function(e) {
      if (sidebar.classList.contains('mobile-open') &&
          !sidebar.contains(e.target) &&
          !mobileBtn.contains(e.target)) {
        sidebar.classList.remove('mobile-open');
      }
    });
  }
}

/* ── Client-side Router ────────────────────────────────────────────────── */
function initRouter() {
  // Navigate on sidebar click
  var items = document.querySelectorAll('.sidebar-item[data-page]');
  items.forEach(function(item) {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      var page = item.getAttribute('data-page');
      navigateTo(page);

      // Close mobile sidebar
      var sidebar = document.getElementById('sidebar');
      if (sidebar) sidebar.classList.remove('mobile-open');
    });
  });

  // Handle initial hash
  var hash = window.location.hash.replace('#', '');
  if (hash && document.getElementById('page-' + hash)) {
    navigateTo(hash);
  } else {
    navigateTo('projeto');
  }

  // Handle browser back/forward
  window.addEventListener('hashchange', function() {
    var hash = window.location.hash.replace('#', '');
    if (hash) navigateTo(hash, true);
  });
}

var PAGE_NAMES = {
  'projeto': 'Projeto',
  'entrevistas': 'Entrevistas',
  'roadmap': 'Roadmap',
  'agentes': 'Agentes IA',
  'vexia': 'Vexia',
  'usuarios': 'Usu\u00e1rios',
  'configuracoes': 'Configura\u00e7\u00f5es',
  'estrategia': 'Estrat\u00e9gia'
};

function navigateTo(page, fromPopstate) {
  // Hide all pages
  var pages = document.querySelectorAll('.page');
  pages.forEach(function(p) { p.style.display = 'none'; });

  // Show target page
  var target = document.getElementById('page-' + page);
  if (target) {
    target.style.display = 'block';
  }

  // Update sidebar active state
  var items = document.querySelectorAll('.sidebar-item[data-page]');
  items.forEach(function(item) {
    item.classList.toggle('active', item.getAttribute('data-page') === page);
  });

  // Update breadcrumb
  var breadcrumb = document.getElementById('breadcrumb-page');
  if (breadcrumb && PAGE_NAMES[page]) {
    breadcrumb.textContent = PAGE_NAMES[page];
  }

  // Update URL hash (without triggering hashchange loop)
  if (!fromPopstate) {
    history.pushState(null, '', '#' + page);
  }

  // Update page title
  document.title = 'Stoken Advisory \u2014 ' + (PAGE_NAMES[page] || page);

  // Load data for specific pages
  if (page === 'usuarios') loadUsersTable();
}

/* ── Timeline — interactive expand, checkboxes, status, notes ──────────── */
function initTimeline() {
  var items = document.querySelectorAll('.timeline-item[data-tl-id]');
  if (!items.length) return;

  // Load saved state from localStorage
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem('tl-state') || '{}'); } catch(e) {}

  items.forEach(function(item) {
    var id = item.getAttribute('data-tl-id');
    var detail = item.querySelector('.timeline-detail');
    var headerLabel = item.querySelector('.timeline-label');
    var select = item.querySelector('[data-tl-select]');

    // Restore saved checkbox states
    if (saved[id]) {
      var checkboxes = item.querySelectorAll('.tl-checkbox');
      if (saved[id].checks) {
        checkboxes.forEach(function(cb, i) {
          if (typeof saved[id].checks[i] !== 'undefined') cb.checked = saved[id].checks[i];
        });
      }
      if (saved[id].status && select) {
        select.value = saved[id].status;
        applyTimelineStatus(item, saved[id].status);
      }
      if (saved[id].note) {
        var noteInput = item.querySelector('.tl-note-input');
        if (noteInput) noteInput.value = saved[id].note;
      }
      updateTimelineProgress(item);
    }

    // Click header to expand/collapse (but not on select or buttons)
    if (headerLabel && detail) {
      headerLabel.addEventListener('click', function() {
        var isOpen = detail.style.display !== 'none';
        items.forEach(function(other) {
          var od = other.querySelector('.timeline-detail');
          if (od && other !== item) od.style.display = 'none';
        });
        detail.style.display = isOpen ? 'none' : 'block';
      });
    }

    // Status select change
    if (select) {
      select.addEventListener('click', function(e) { e.stopPropagation(); });
      select.addEventListener('change', function() {
        applyTimelineStatus(item, select.value);
        saveTimelineState();
      });
    }

    // Checkbox toggle
    var checkboxes = item.querySelectorAll('.tl-checkbox');
    checkboxes.forEach(function(cb) {
      cb.addEventListener('click', function(e) { e.stopPropagation(); });
      cb.addEventListener('change', function() {
        updateTimelineProgress(item);
        saveTimelineState();
      });
    });

    // Date input — stopPropagation + auto-save
    var dateInput = item.querySelector('[data-tl-date]');
    if (dateInput) {
      dateInput.addEventListener('click', function(e) { e.stopPropagation(); });
      dateInput.addEventListener('blur', function() { saveTimelineState(); });
      if (saved[id] && saved[id].date) {
        dateInput.value = saved[id].date;
      }
    }

    // Notes auto-save on blur
    var noteInput = item.querySelector('.tl-note-input');
    if (noteInput) {
      noteInput.addEventListener('click', function(e) { e.stopPropagation(); });
      noteInput.addEventListener('blur', function() { saveTimelineState(); });
    }
  });

  function applyTimelineStatus(item, status) {
    item.className = 'timeline-item' + (status === 'done' ? ' timeline-item--done' : (status === 'active' ? ' timeline-item--active' : ''));
    item.setAttribute('data-tl-status', status);
    // Update marker
    var marker = item.querySelector('.timeline-marker');
    if (marker) marker.className = 'timeline-marker';
  }

  function updateTimelineProgress(item) {
    var checkboxes = item.querySelectorAll('.tl-checkbox');
    var total = checkboxes.length;
    var done = 0;
    checkboxes.forEach(function(cb) { if (cb.checked) done++; });
    var progressText = item.querySelector('.tl-progress-text');
    if (progressText) {
      progressText.textContent = done + '/' + total + ' conclu\u00eddos';
    }
    // Update global progress in sidebar
    updateGlobalProgress();
  }

  function saveTimelineState() {
    var state = {};
    items.forEach(function(item) {
      var id = item.getAttribute('data-tl-id');
      var checks = [];
      item.querySelectorAll('.tl-checkbox').forEach(function(cb) { checks.push(cb.checked); });
      var select = item.querySelector('[data-tl-select]');
      var noteInput = item.querySelector('.tl-note-input');
      var dateInput = item.querySelector('[data-tl-date]');
      state[id] = {
        checks: checks,
        status: select ? select.value : 'pending',
        note: noteInput ? noteInput.value : '',
        date: dateInput ? dateInput.value : ''
      };
    });
    localStorage.setItem('tl-state', JSON.stringify(state));
  }

  function updateGlobalProgress() {
    var allChecks = document.querySelectorAll('#project-timeline .tl-checkbox');
    var total = allChecks.length;
    var done = 0;
    allChecks.forEach(function(cb) { if (cb.checked) done++; });
    var pct = total > 0 ? Math.round((done / total) * 100) : 0;
    // Update sidebar progress
    var progressValue = document.querySelector('.sidebar-progress-value');
    var progressFill = document.querySelector('.sidebar-progress-fill');
    if (progressValue) progressValue.textContent = pct + '%';
    if (progressFill) progressFill.style.width = pct + '%';
  }

  // Initial global progress update
  updateGlobalProgress();
}

/* ══════════════════════════════════════════════════════════════════════════
   NOVA ENTREVISTA — Modal + dynamic card creation
   ══════════════════════════════════════════════════════════════════════════ */

/* ── Perguntas por Area/Departamento ────────────────────────────────────── */
var AREA_QUESTIONS = {
  'supply-chain': {
    title: 'Supply Chain',
    questions: [
      'Como funciona o processo de S&OP atualmente? Existe valida\u00e7\u00e3o estrat\u00e9gica de demanda?',
      'Qual o n\u00edvel de integra\u00e7\u00e3o entre as \u00e1reas (Comercial, PCP, Financeiro)?',
      'Como s\u00e3o definidos, acompanhados e revisados os KPIs da \u00e1rea?',
      'Quais s\u00e3o os maiores gargalos da cadeia de suprimentos hoje?',
      'Existe visibilidade end-to-end da cadeia? Quais ferramentas s\u00e3o usadas?',
      'Como \u00e9 feita a gest\u00e3o de riscos da cadeia (fornecedores, log\u00edstica, demanda)?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'producao': {
    title: 'Produ\u00e7\u00e3o / PCP',
    questions: [
      'O planejamento de produ\u00e7\u00e3o \u00e9 feito em sistema ou em Excel? Por qu\u00ea?',
      'Existe controle de acur\u00e1cia do cronograma de produ\u00e7\u00e3o?',
      'Como funciona o custeio de produtos? Qual a granularidade dispon\u00edvel?',
      'Qual o OEE m\u00e9dio das linhas? Como \u00e9 medido?',
      'Como s\u00e3o tratadas as paradas n\u00e3o planejadas? Existe manuten\u00e7\u00e3o preventiva?',
      'Como \u00e9 feito o sequenciamento de produ\u00e7\u00e3o? Quais crit\u00e9rios de prioriza\u00e7\u00e3o?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'comercial': {
    title: 'Comercial / Vendas',
    questions: [
      'Como \u00e9 feita a previs\u00e3o de vendas? Qual a acur\u00e1cia hist\u00f3rica?',
      'Existe processo formal de valida\u00e7\u00e3o de demanda com a produ\u00e7\u00e3o?',
      'Como \u00e9 a pol\u00edtica de pre\u00e7os? Existe pricing din\u00e2mico?',
      'Qual o lead time prometido ao cliente vs realizado?',
      'Como \u00e9 gerenciado o portf\u00f3lio de clientes (ABC, segmenta\u00e7\u00e3o)?',
      'Quais s\u00e3o as principais reclama\u00e7\u00f5es de clientes sobre entrega e atendimento?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'logistica': {
    title: 'Log\u00edstica',
    questions: [
      'Como funciona o fluxo de recebimento, armazenagem e expedi\u00e7\u00e3o?',
      'Qual o n\u00edvel de automa\u00e7\u00e3o na opera\u00e7\u00e3o (picking, embalagem, invent\u00e1rio)?',
      'Como \u00e9 gerenciada a frota / transportadoras? Existe TMS?',
      'Qual o custo log\u00edstico como % do faturamento?',
      'Existe rastreabilidade de pedidos em tempo real?',
      'Como \u00e9 feita a roteiriza\u00e7\u00e3o de entregas? Manual ou otimizada?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'ti': {
    title: 'Tecnologia / TI',
    questions: [
      'Quais sistemas s\u00e3o usados no dia a dia (ERP, WMS, TMS, BI)?',
      'Qual a vers\u00e3o do ERP e quando foi a \u00faltima atualiza\u00e7\u00e3o?',
      'Existem integra\u00e7\u00f5es autom\u00e1ticas entre sistemas ou \u00e9 tudo manual?',
      'Como \u00e9 a qualidade e confiabilidade dos dados para tomada de decis\u00e3o?',
      'Existe algum projeto de BI, data lake ou analytics em andamento?',
      'Como \u00e9 o suporte de TI para a opera\u00e7\u00e3o? Qual o SLA?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'financeiro': {
    title: 'Financeiro / Controladoria',
    questions: [
      'Como \u00e9 feito o custeio de produtos? Custo padr\u00e3o ou real?',
      'Qual a visibilidade de margem por SKU, canal e cliente?',
      'Como s\u00e3o aprovados investimentos em supply chain? Qual o processo?',
      'Existe an\u00e1lise de capital de giro vinculada ao estoque?',
      'Como \u00e9 feito o or\u00e7amento anual de opera\u00e7\u00f5es? \u00c9 bottom-up ou top-down?',
      'Quais KPIs financeiros s\u00e3o acompanhados com frequ\u00eancia mensal?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'qualidade': {
    title: 'Qualidade',
    questions: [
      'Como \u00e9 feito o controle de qualidade na produ\u00e7\u00e3o? Em quais etapas?',
      'Os checklists de qualidade s\u00e3o digitais ou em papel?',
      'Qual o \u00edndice de retrabalho e refugo atual? Como \u00e9 medido?',
      'Existe sistema de rastreabilidade de lotes/mat\u00e9rias-primas?',
      'Como s\u00e3o tratadas as n\u00e3o-conformidades? Existe processo formal?',
      'A empresa tem certifica\u00e7\u00f5es ISO? Como \u00e9 a manuten\u00e7\u00e3o?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'compras': {
    title: 'Compras / Procurement',
    questions: [
      'Como \u00e9 o processo de compras? Manual, por aprova\u00e7\u00e3o ou automatizado?',
      'Existe avalia\u00e7\u00e3o formal de fornecedores? Quais crit\u00e9rios?',
      'Qual o lead time m\u00e9dio de compra das principais mat\u00e9rias-primas?',
      'Existe depend\u00eancia cr\u00edtica de fornecedor \u00fanico em algum insumo?',
      'Como \u00e9 feita a negocia\u00e7\u00e3o de contratos? Existem contratos de longo prazo?',
      'Qual o saving anual gerado pela \u00e1rea de compras?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  },
  'rh': {
    title: 'RH / Pessoas',
    questions: [
      'Como est\u00e1 estruturada a \u00e1rea de RH? Quantas pessoas comp\u00f5em a equipe e como est\u00e3o divididas as responsabilidades?',
      'Existe programa de capacita\u00e7\u00e3o t\u00e9cnica para a equipe?',
      'Qual o turnover da \u00e1rea? Quais os cargos mais cr\u00edticos para reter?',
      'Existe clareza de pap\u00e9is e responsabilidades (RACI) nos processos-chave?',
      'Como funciona a comunica\u00e7\u00e3o entre turnos e entre \u00e1reas?',
      'Existem programas de reconhecimento por performance operacional?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para executá-la?'
    ]
  },
  'diretoria': {
    title: 'Diretoria Geral',
    questions: [
      'Qual a vis\u00e3o estrat\u00e9gica para supply chain nos pr\u00f3ximos 3 anos?',
      'Quais s\u00e3o os principais riscos do neg\u00f3cio relacionados \u00e0 opera\u00e7\u00e3o?',
      'Como \u00e9 priorizado o investimento entre projetos concorrentes?',
      'A empresa tem vis\u00e3o de supply chain digital? Qual o horizonte?',
      'Quais foram as maiores mudan\u00e7as na opera\u00e7\u00e3o nos \u00faltimos 2 anos?',
      'O que a diretoria considera como \u201cestado ideal\u201d da opera\u00e7\u00e3o em 3 anos?',
      'Na sua rotina de trabalho, qual a tarefa que te demanda mais tempo? Qual a maior dificuldade para execut\u00e1-la?'
    ]
  }
};

function updateQuestionsByArea(areaValue) {
  var list = document.getElementById('form-questions-list');
  var title = document.getElementById('form-questions-title');
  if (!list) return;

  var area = AREA_QUESTIONS[areaValue];
  if (!area) {
    title.textContent = 'Selecione a \u00e1rea para ver perguntas sugeridas';
    list.innerHTML = '';
    return;
  }

  title.textContent = 'Perguntas gerais para ' + area.title;
  list.innerHTML = area.questions.map(function(q) {
    return '<div class="question-item"><span>' + q + '</span><button type="button" class="question-add">+</button></div>';
  }).join('');
}

var PILAR_MAP = {
  'supply-chain': { label: 'CADEIA DE SUPRIMENTOS', color: 'var(--pilar-processos)',    title: 'Cadeia de Suprimentos' },
  'producao':     { label: 'OP. INDUSTRIAIS',       color: 'var(--pilar-operacoes)',    title: 'Operações Industriais' },
  'comercial':    { label: 'RECEITA & GROWTH',      color: 'var(--pilar-roadmap)',      title: 'Receita & Growth' },
  'logistica':    { label: 'OP. LOGÍSTICAS',        color: 'var(--pilar-operacoes)',    title: 'Operações Logísticas' },
  'ti':           { label: 'TECNOLOGIA',            color: 'var(--pilar-sistemas)',     title: 'Tecnologia & Sistemas' },
  'financeiro':   { label: 'FINANÇAS',              color: 'var(--pilar-organizacao)',  title: 'Finanças & Performance' },
  'qualidade':    { label: 'QUALIDADE',             color: 'var(--pilar-processos)',    title: 'Qualidade & Compliance' },
  'compras':      { label: 'SUPRIMENTOS',           color: 'var(--pilar-processos)',    title: 'Suprimentos & Aquisições' },
  'rh':           { label: 'PESSOAS',               color: 'var(--pilar-organizacao)',  title: 'Pessoas & Cultura' },
  'diretoria':    { label: 'GOVERNANÇA',            color: 'var(--pilar-roadmap)',      title: 'Estratégia & Governança' }
};

function initNovaEntrevista() {
  var btn = document.getElementById('btn-nova-entrevista');
  var modal = document.getElementById('modal-entrevista');
  var closeBtn = document.getElementById('modal-entrevista-close');
  var cancelBtn = document.getElementById('modal-entrevista-cancel');
  var form = document.getElementById('form-entrevista');
  var pilarSelect = document.getElementById('ent-pilar');
  var questionsToggle = document.getElementById('form-questions-toggle');
  var questionsBlock = document.getElementById('form-questions');
  var questionsTitle = document.getElementById('form-questions-title');

  if (!btn || !modal) return;

  // Open modal (new interview)
  btn.addEventListener('click', function() {
    resetInterviewModal();
    form.reset();
    modal.style.display = 'flex';
    var hoje = new Date();
    var dataInput = document.getElementById('ent-data');
    if (dataInput && !dataInput.value) {
      dataInput.value = hoje.toISOString().split('T')[0];
    }
    document.getElementById('ent-entrevistador').focus();
  });

  // Close modal
  function closeModal() {
    modal.style.display = 'none';
    form.reset();
    resetInterviewModal();
  }

  closeBtn.addEventListener('click', closeModal);
  cancelBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', function(e) { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.style.display === 'flex') closeModal();
  });

  // Area selector → update questions
  var areaSelect = document.getElementById('ent-area');
  if (areaSelect) {
    areaSelect.addEventListener('change', function() {
      updateQuestionsByArea(areaSelect.value);
    });
  }

  // Questions accordion toggle
  if (questionsToggle && questionsBlock) {
    questionsToggle.addEventListener('click', function() {
      questionsBlock.classList.toggle('collapsed');
    });
  }

  // Question "+" buttons → append to transcription
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('question-add')) {
      var questionText = e.target.parentElement.querySelector('span').textContent;
      var textarea = document.getElementById('ent-transcricao');
      if (textarea) {
        textarea.value += (textarea.value ? '\n\n' : '') + 'P: ' + questionText + '\nR: ';
        textarea.focus();
        textarea.scrollTop = textarea.scrollHeight;
      }
    }
  });

  // Submit form
  form.addEventListener('submit', function(e) {
    e.preventDefault();

    var nome = document.getElementById('ent-nome').value.trim();
    var cargo = document.getElementById('ent-cargo').value.trim();
    var data = document.getElementById('ent-data').value;
    var pilar = document.getElementById('ent-pilar').value;
    var transcricao = document.getElementById('ent-transcricao').value.trim();

    if (!nome || !cargo) return;

    var entrevistador = document.getElementById('ent-entrevistador').value.trim();
    var area = document.getElementById('ent-area').value;
    var nivel = document.getElementById('ent-nivel').value;

    // Save to backend (POST for new, PUT for edit)
    // ia_ready é automático no backend quando há transcrição
    var isEditing = !!_editingInterviewId;
    var url = isEditing ? '/api/interviews/' + _editingInterviewId : '/api/interviews';
    var method = isEditing ? 'PUT' : 'POST';

    fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        interviewer: entrevistador,
        interviewee: nome,
        role: cargo,
        department: area,
        level: nivel,
        pillar: pilar,
        date: data,
        transcript: transcricao,
        ia_ready: !!transcricao
      })
    }).then(function(res) { return res.json(); })
    .then(function(result) {
      if (result.status !== 'ok') {
        alert('Erro: ' + (result.detail || 'erro desconhecido'));
        return;
      }
      loadInterviews();
      closeModal();
      // Se pipeline foi disparado (edição ou criação com transcrição), mostra progresso
      if (result.reprocessing) {
        pollPipelineStatus();
      }
    }).catch(function(err) {
      alert('Erro: ' + err.message);
    });
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   AI AGENTS — Card selection + Chat interface
   ══════════════════════════════════════════════════════════════════════════ */

var currentAgent = null;

function initAgents() {
  var cards = document.querySelectorAll('.agent-card[data-agent]');
  var chatPanel = document.getElementById('agent-chat-panel');
  var agentGrid = document.getElementById('agent-grid');
  var backBtn = document.getElementById('agent-back-btn');
  var sendBtn = document.getElementById('agent-send-btn');
  var input = document.getElementById('agent-input');

  if (!cards.length) return;

  // Click agent card → open chat
  cards.forEach(function(card) {
    card.addEventListener('click', function() {
      currentAgent = card.getAttribute('data-agent');
      openAgentChat(currentAgent);
    });
  });

  // Back button
  if (backBtn) {
    backBtn.addEventListener('click', function() {
      chatPanel.style.display = 'none';
      agentGrid.style.display = '';
      currentAgent = null;
    });
  }

  // Send message
  if (sendBtn && input) {
    sendBtn.addEventListener('click', function() { sendAgentMessage(); });
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendAgentMessage();
      }
    });
  }
}

var AGENT_INFO = {
  'aria':      { name: 'ARIA',      role: 'Diagn\u00f3stico de Maturidade' },
  'strategos': { name: 'STRATEGOS', role: 'An\u00e1lise de Gaps Estrat\u00e9gicos' },
  'sentinel':  { name: 'SENTINEL',  role: 'Avalia\u00e7\u00e3o de Riscos' },
  'nexus':     { name: 'NEXUS',     role: 'Benchmark & Intelig\u00eancia de Mercado' },
  'catalyst':  { name: 'CATALYST',  role: 'Business Case & ROI' },
  'prism':     { name: 'PRISM',     role: 'An\u00e1lise de Entrevistas' },
  'atlas':     { name: 'ATLAS',     role: 'Roadmap & Transforma\u00e7\u00e3o' },
  'synapse':   { name: 'SYNAPSE',   role: 'S\u00edntese Integrada do Workflow' }
};

function openAgentChat(agentId) {
  var chatPanel = document.getElementById('agent-chat-panel');
  var agentGrid = document.getElementById('agent-grid');
  var nameEl = document.getElementById('agent-chat-name');
  var roleEl = document.getElementById('agent-chat-role');
  var messagesEl = document.getElementById('agent-chat-messages');

  var info = AGENT_INFO[agentId];
  if (!info) return;

  nameEl.textContent = info.name;
  roleEl.textContent = info.role;

  // Clear previous messages, show welcome
  messagesEl.innerHTML = '<div class="agent-welcome"><p class="body-text">' +
    'Agente <strong>' + info.name + '</strong> pronto. Envie sua pergunta sobre o projeto Santista S.A. ' +
    'O agente usar\u00e1 frameworks de consultoria de classe mundial para responder.</p></div>';

  agentGrid.style.display = 'none';
  chatPanel.style.display = 'flex';

  document.getElementById('agent-input').focus();
}

function sendAgentMessage() {
  var input = document.getElementById('agent-input');
  var messagesEl = document.getElementById('agent-chat-messages');
  var sendBtn = document.getElementById('agent-send-btn');
  var message = input.value.trim();

  if (!message || !currentAgent) return;

  // Add user message
  var userDiv = document.createElement('div');
  userDiv.className = 'agent-msg agent-msg--user';
  userDiv.innerHTML = '<div class="agent-msg-label">VOC\u00ca</div><div class="agent-msg-text">' + escapeHtml(message) + '</div>';
  messagesEl.appendChild(userDiv);

  // Clear input
  input.value = '';
  sendBtn.textContent = 'Processando...';
  sendBtn.disabled = true;

  // Add loading indicator
  var loadingDiv = document.createElement('div');
  loadingDiv.className = 'agent-msg agent-msg--agent';
  loadingDiv.id = 'agent-loading';
  var agentName = (AGENT_INFO[currentAgent] && AGENT_INFO[currentAgent].name) || 'AGENTE';
  loadingDiv.innerHTML = '<div class="agent-msg-label font-mono">' + agentName + '</div><div class="agent-msg-text"><span class="agent-typing">Analisando</span></div>';
  messagesEl.appendChild(loadingDiv);

  // Scroll to bottom
  messagesEl.scrollTop = messagesEl.scrollHeight;

  // Call API
  fetch('/api/agents/' + currentAgent + '/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: message })
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    var loading = document.getElementById('agent-loading');
    if (loading) loading.remove();

    var agentDiv = document.createElement('div');
    agentDiv.className = 'agent-msg agent-msg--agent';

    if (data.status === 'ok' && data.response) {
      agentDiv.innerHTML = '<div class="agent-msg-label font-mono">' + (data.agent_name || 'AGENTE') +
        '</div><div class="agent-msg-text agent-msg-markdown">' + renderMarkdown(data.response) + '</div>' +
        '<div class="agent-msg-meta font-mono">' + (data.usage ? data.usage.input_tokens + ' in \u00b7 ' + data.usage.output_tokens + ' out' : '') + '</div>';
    } else {
      var errMsg = data.detail ? (data.detail.error || data.detail) : 'Erro desconhecido';
      var hint = data.detail && data.detail.hint ? '<br><span style="color:var(--text-muted)">' + data.detail.hint + '</span>' : '';
      agentDiv.innerHTML = '<div class="agent-msg-label font-mono">ERRO</div><div class="agent-msg-text" style="color:var(--danger)">' + escapeHtml(String(errMsg)) + hint + '</div>';
    }

    messagesEl.appendChild(agentDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  })
  .catch(function(err) {
    var loading = document.getElementById('agent-loading');
    if (loading) loading.remove();

    var errDiv = document.createElement('div');
    errDiv.className = 'agent-msg agent-msg--agent';
    errDiv.innerHTML = '<div class="agent-msg-label font-mono">ERRO</div><div class="agent-msg-text" style="color:var(--danger)">' + escapeHtml(err.message) + '</div>';
    messagesEl.appendChild(errDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  })
  .finally(function() {
    sendBtn.textContent = 'Enviar';
    sendBtn.disabled = false;
    input.focus();
  });
}

function escapeHtml(text) {
  var d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

/* ══════════════════════════════════════════════════════════════════════════
   PIPELINE — Auto-analysis trigger + result loading
   ══════════════════════════════════════════════════════════════════════════ */

function triggerPipeline(area) {
  var url = '/api/pipeline/run';
  if (area) url += '?area=' + encodeURIComponent(area);
  fetch(url, { method: 'POST' })
    .then(function(res) { return res.json(); })
    .then(function(data) {
      if (data.status === 'ok') {
        pollPipelineStatus();
      }
    })
    .catch(function(err) { console.warn('Pipeline trigger error:', err); });
}

function pollPipelineStatus() {
  var banner = document.getElementById('pipeline-banner');
  var bannerTitle = document.getElementById('pipeline-banner-title');
  var bannerStep = document.getElementById('pipeline-banner-step');
  var bannerSteps = document.getElementById('pipeline-banner-steps');
  var prevCount = 0;
  var pollCount = 0;
  var maxPolls = 200; // ~10 min timeout (200 * 3s)

  banner.style.display = '';
  banner.classList.remove('done');

  var interval = setInterval(function() {
    pollCount++;
    if (pollCount > maxPolls) {
      clearInterval(interval);
      bannerTitle.textContent = 'Pipeline — timeout';
      bannerStep.textContent = 'O pipeline demorou demais. Recarregue a pagina para verificar.';
      banner.classList.add('done');
      setTimeout(function() { banner.style.display = 'none'; }, 8000);
      if (_activeStrategyArea) loadStrategyData(_activeStrategyArea);
      loadInterviews();
      return;
    }

    fetch('/api/pipeline/status')
      .then(function(res) { return res.json(); })
      .then(function(data) {
        var pipeline = data.pipeline;
        var steps = pipeline.steps_completed || [];
        var lastStep = steps.length ? steps[steps.length - 1] : 'Iniciando...';

        bannerStep.textContent = lastStep;

        // Update step dots
        if (steps.length !== prevCount) {
          prevCount = steps.length;
          var dotsHtml = '';
          for (var i = 0; i < steps.length; i++) {
            dotsHtml += '<div class="pipeline-step-dot done" title="' + steps[i].replace(/"/g, '&quot;') + '"></div>';
          }
          dotsHtml += '<div class="pipeline-step-dot active"></div>';
          bannerSteps.innerHTML = dotsHtml;
        }

        if (pipeline.errors && pipeline.errors.length) {
          bannerTitle.textContent = 'Pipeline — ' + pipeline.errors.length + ' erro(s)';
        }

        if (!pipeline.running) {
          clearInterval(interval);
          banner.classList.add('done');
          var hasErrors = pipeline.errors && pipeline.errors.length;
          bannerTitle.textContent = hasErrors ? 'Pipeline concluido com erros' : 'Pipeline concluido';
          bannerStep.textContent = hasErrors ? pipeline.errors[pipeline.errors.length - 1] : steps[steps.length - 1] || 'Finalizado';
          // Remove active dot
          bannerSteps.querySelectorAll('.active').forEach(function(d) { d.classList.remove('active'); d.classList.add('done'); });
          // Auto-hide after 5s
          setTimeout(function() { banner.style.display = 'none'; }, 5000);
          // Reload data
          if (_activeStrategyArea) loadStrategyData(_activeStrategyArea);
          loadInterviews();
        }
      })
      .catch(function() { clearInterval(interval); banner.style.display = 'none'; });
  }, 3000);
}

// Load data on page init + check if pipeline is already running
setTimeout(function() {
  loadInterviews();
  fetch('/api/pipeline/status').then(function(r) { return r.json(); }).then(function(data) {
    if (data.pipeline && data.pipeline.running) pollPipelineStatus();
  }).catch(function() {});
}, 500);

function loadInterviews() {
  fetch('/api/interviews')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status !== 'ok') return;
      var interviews = data.interviews;

      // Update counter
      var el = document.getElementById('metric-entrevistas');
      if (el) el.textContent = interviews.length;

      // Render cards
      var grid = document.getElementById('interview-grid');
      var emptyState = document.getElementById('interview-empty');
      if (!grid) return;

      if (interviews.length === 0) {
        if (emptyState) emptyState.style.display = '';
        renderCoverageMap([]);
        return;
      }
      if (emptyState) emptyState.style.display = 'none';

      var areaLabels = {
        'supply-chain': 'SUPPLY CHAIN', 'producao': 'PRODUÇÃO', 'comercial': 'COMERCIAL',
        'logistica': 'LOGÍSTICA', 'ti': 'TI', 'financeiro': 'FINANCEIRO',
        'qualidade': 'QUALIDADE', 'compras': 'COMPRAS', 'rh': 'RH', 'diretoria': 'DIRETORIA'
      };

      grid.innerHTML = '';
      interviews.forEach(function(iv) {
        var parts = iv.interviewee.split(' ');
        var initials = (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();

        var dateStr = 'Sem data';
        if (iv.date) {
          var d = new Date(iv.date + 'T12:00:00');
          var months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
          dateStr = d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
        }

        var aiTag = iv.analysis ? 'ANALISADO' : (iv.transcript ? 'PROCESSANDO' : 'NOVO');
        var areaTag = areaLabels[iv.department] || (iv.department || '').toUpperCase();
        var pilarInfo = PILAR_MAP[iv.pillar];
        var pilarTag = pilarInfo ? '<span class="interview-tag" style="color:' + pilarInfo.color + '">' + pilarInfo.label + '</span>' : '';

        var card = document.createElement('div');
        card.className = 'interview-card';
        card.setAttribute('data-interview-area', iv.department || '');
        card.setAttribute('data-interview-id', iv.id);
        card.innerHTML =
          '<div class="interview-card-top">' +
            '<div class="interview-avatar">' + initials + '</div>' +
            '<div class="interview-info">' +
              '<span class="interview-name">' + escapeHtml(iv.interviewee) + '</span>' +
              '<span class="interview-role">' + escapeHtml(iv.role) + '</span>' +
            '</div>' +
            '<span class="interview-ai-tag font-mono">' + aiTag + '</span>' +
          '</div>' +
          '<div class="interview-tags">' +
            (areaTag ? '<span class="interview-tag" style="color: var(--text-muted)">' + areaTag + '</span>' : '') +
            pilarTag +
          '</div>' +
          '<div class="interview-footer">' +
            '<span class="interview-date font-mono">' + dateStr + '</span>' +
            '<div class="interview-actions">' +
              '<button class="btn-icon btn-icon--edit" title="Editar" onclick="editInterview(' + iv.id + ')">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>' +
              '</button>' +
              '<button class="btn-icon btn-icon--delete" title="Excluir" onclick="deleteInterview(' + iv.id + ', \'' + escapeHtml(iv.interviewee).replace(/'/g, "\\'") + '\')">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>' +
              '</button>' +
            '</div>' +
          '</div>';

        grid.appendChild(card);
      });

      // Render coverage map
      renderCoverageMap(interviews);
    })
    .catch(function(err) { console.warn('Load interviews error:', err); });
}

function renderCoverageMap(interviews) {
  var tbody = document.getElementById('coverage-tbody');
  if (!tbody) return;

  var pilars = ['processos', 'sistemas', 'operacoes', 'organizacao', 'roadmap'];
  var areas = ['supply-chain', 'producao', 'comercial', 'logistica', 'ti', 'financeiro', 'qualidade', 'compras', 'rh', 'diretoria'];
  var areaLabels = {
    'supply-chain': 'Supply Chain', 'producao': 'Produção', 'comercial': 'Comercial',
    'logistica': 'Logística', 'ti': 'TI', 'financeiro': 'Financeiro',
    'qualidade': 'Qualidade', 'compras': 'Compras', 'rh': 'RH', 'diretoria': 'Diretoria'
  };

  // Build coverage matrix: area → pilar → count
  var matrix = {};
  areas.forEach(function(a) {
    matrix[a] = {};
    pilars.forEach(function(p) { matrix[a][p] = 0; });
  });

  // Count: each interview with a department counts for its pillar (if set),
  // or counts as general coverage for the area
  interviews.forEach(function(iv) {
    var dept = iv.department || '';
    var pilar = iv.pillar || '';
    if (matrix[dept]) {
      if (pilar && matrix[dept][pilar] !== undefined) {
        matrix[dept][pilar]++;
      } else {
        // No specific pillar — count as coverage for all pillars
        pilars.forEach(function(p) { matrix[dept][p] += 0.5; });
      }
    }
  });

  // Check which areas have any interviews
  var activeAreas = areas.filter(function(a) {
    return interviews.some(function(iv) { return iv.department === a; });
  });

  if (activeAreas.length === 0) {
    tbody.innerHTML = '<tr><td class="coverage-name" colspan="6" style="text-align: center; color: var(--text-subtle); font-style: italic;">Adicione entrevistas para popular o mapa</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  activeAreas.forEach(function(area) {
    var tr = document.createElement('tr');
    var tdName = document.createElement('td');
    tdName.className = 'coverage-name';
    tdName.textContent = areaLabels[area] || area;
    tr.appendChild(tdName);

    pilars.forEach(function(p) {
      var td = document.createElement('td');
      td.className = 'coverage-cell';
      var count = matrix[area][p];
      if (count >= 1) {
        td.innerHTML = '<span class="coverage-dot coverage-dot--done" title="' + Math.floor(count) + ' entrevista(s)"></span>';
      } else if (count > 0) {
        td.innerHTML = '<span class="coverage-dot coverage-dot--partial" title="Cobertura parcial"></span>';
      } else {
        td.innerHTML = '<span class="coverage-dot coverage-dot--empty" title="Sem cobertura"></span>';
      }
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });
}

function loadInterviewCount() {
  loadInterviews();
}

/* ── Delete Interview ──────────────────────────────────────────────── */
function deleteInterview(id, name) {
  if (!confirm('Excluir entrevista de "' + name + '"?\n\nA estrat\u00e9gia e o roadmap ser\u00e3o recalculados automaticamente.\nEsta a\u00e7\u00e3o n\u00e3o pode ser desfeita.')) return;
  fetch('/api/interviews/' + id, { method: 'DELETE' })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status === 'ok') {
        loadInterviews();
        if (data.reprocessing) {
          // Pipeline foi disparado para reprocessar a área
          pollPipelineStatus();
        } else if (data.area_cleared) {
          // Área ficou sem entrevistas — análises foram limpas
          showToast('\u00c1rea "' + (data.department || '') + '" sem entrevistas \u2014 an\u00e1lises removidas.', 'info');
          // Recarrega estratégia se estiver visualizando essa área
          if (_activeStrategyArea === data.department) loadStrategyData(_activeStrategyArea);
        }
      } else {
        alert('Erro ao excluir: ' + (data.detail || 'erro desconhecido'));
      }
    })
    .catch(function(err) { alert('Erro: ' + err.message); });
}

/* ── Edit Interview — opens modal pre-filled ──────────────────────── */
var _editingInterviewId = null;

function editInterview(id) {
  fetch('/api/interviews')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status !== 'ok') return;
      var iv = data.interviews.find(function(i) { return i.id === id; });
      if (!iv) return alert('Entrevista n\u00e3o encontrada');

      _editingInterviewId = id;

      // Fill modal fields
      var modal = document.getElementById('modal-entrevista');
      document.getElementById('ent-entrevistador').value = iv.interviewer || '';
      document.getElementById('ent-nome').value = iv.interviewee || '';
      document.getElementById('ent-cargo').value = iv.role || '';
      document.getElementById('ent-area').value = iv.department || '';
      document.getElementById('ent-nivel').value = iv.level || 'gerencia';
      document.getElementById('ent-pilar').value = iv.pillar || 'processos';
      document.getElementById('ent-data').value = iv.date || '';
      document.getElementById('ent-transcricao').value = iv.transcript || '';
      // Update modal title
      document.querySelector('#modal-entrevista .modal-title').textContent = 'Editar Entrevista';
      document.querySelector('#form-entrevista .btn--primary').textContent = 'Salvar Altera\u00e7\u00f5es';

      // Trigger area questions
      var areaSelect = document.getElementById('ent-area');
      areaSelect.dispatchEvent(new Event('change'));

      modal.style.display = 'flex';
    });
}

function resetInterviewModal() {
  _editingInterviewId = null;
  document.querySelector('#modal-entrevista .modal-title').textContent = 'Nova Entrevista';
  document.querySelector('#form-entrevista .btn--primary').textContent = 'Salvar Entrevista';
}

/* ══════════════════════════════════════════════════════════════════════════
   ONLINE INTERVIEW FORM — fill questions interactively
   ══════════════════════════════════════════════════════════════════════════ */

function initOnlineForm() {
  var areaSelect = document.getElementById('of-area');
  var questionsArea = document.getElementById('of-questions-area');
  var questionsList = document.getElementById('of-questions-list');
  var questionsTitle = document.getElementById('of-questions-title');
  var btnSave = document.getElementById('of-btn-save');
  var btnClear = document.getElementById('of-btn-clear');
  var dataInput = document.getElementById('of-data');

  if (!areaSelect || !btnSave) return;

  // Set today's date
  if (dataInput && !dataInput.value) {
    dataInput.value = new Date().toISOString().split('T')[0];
  }

  // Area change → render questions
  areaSelect.addEventListener('change', function() {
    var area = areaSelect.value;
    var areaData = AREA_QUESTIONS[area];

    if (!areaData) {
      questionsArea.style.display = 'none';
      return;
    }

    questionsTitle.textContent = 'Perguntas \u2014 ' + areaData.title;
    questionsList.innerHTML = areaData.questions.map(function(q, i) {
      return '<div class="of-question">' +
        '<span class="of-question-number">PERGUNTA ' + (i + 1) + '</span>' +
        '<p class="of-question-text">' + q + '</p>' +
        '<textarea class="of-question-answer" data-q-index="' + i + '" rows="3" placeholder="Digite a resposta do entrevistado..."></textarea>' +
      '</div>';
    }).join('');

    questionsArea.style.display = 'block';
  });

  // Clear form
  btnClear.addEventListener('click', function() {
    document.getElementById('of-entrevistador').value = '';
    document.getElementById('of-nome').value = '';
    document.getElementById('of-cargo').value = '';
    areaSelect.value = '';
    document.getElementById('of-observacoes').value = '';
    questionsArea.style.display = 'none';
    questionsList.innerHTML = '';
  });

  // Save
  btnSave.addEventListener('click', function() {
    var entrevistador = document.getElementById('of-entrevistador').value.trim();
    var nome = document.getElementById('of-nome').value.trim();
    var cargo = document.getElementById('of-cargo').value.trim();
    var area = areaSelect.value;
    var data = document.getElementById('of-data').value;
    var nivel = document.getElementById('of-nivel').value;
    var observacoes = document.getElementById('of-observacoes').value.trim();
    if (!nome || !cargo || !area) {
      alert('Preencha nome, cargo e \u00e1rea');
      return;
    }

    // Build transcript from answers
    var areaData = AREA_QUESTIONS[area];
    var transcript = '';
    var answered = 0;
    var total = 0;

    if (areaData) {
      var textareas = questionsList.querySelectorAll('.of-question-answer');
      textareas.forEach(function(ta, i) {
        total++;
        var answer = ta.value.trim();
        transcript += 'P: ' + areaData.questions[i] + '\n';
        transcript += 'R: ' + (answer || '(sem resposta)') + '\n\n';
        if (answer) answered++;
      });
    }

    if (observacoes) {
      transcript += 'OBSERVA\u00c7\u00d5ES:\n' + observacoes + '\n';
    }

    // Save to backend
    btnSave.textContent = 'Salvando...';
    btnSave.disabled = true;

    fetch('/api/interviews', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        interviewer: entrevistador,
        interviewee: nome,
        role: cargo,
        department: area,
        level: nivel,
        date: data,
        transcript: transcript,
        ia_ready: answered > 0
      })
    }).then(function(r) { return r.json(); })
    .then(function(result) {
      // Create card
      var parts = nome.split(' ');
      var initials = (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
      var months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
      var dateStr = data ? (new Date(data + 'T12:00:00').getDate() + ' ' + months[new Date(data + 'T12:00:00').getMonth()] + ' ' + new Date(data + 'T12:00:00').getFullYear()) : 'Hoje';

      var areaLabels = {
        'supply-chain': 'SUPPLY CHAIN', 'producao': 'PRODUÇÃO', 'comercial': 'COMERCIAL',
        'logistica': 'LOGÍSTICA', 'ti': 'TI', 'financeiro': 'FINANCEIRO',
        'qualidade': 'QUALIDADE', 'compras': 'COMPRAS', 'rh': 'RH', 'diretoria': 'DIRETORIA'
      };

      var card = document.createElement('div');
      card.className = 'interview-card';
      card.setAttribute('data-interview-area', area);
      card.style.animation = 'fadeIn 0.3s ease-out';
      card.innerHTML =
        '<div class="interview-card-top">' +
          '<div class="interview-avatar">' + initials + '</div>' +
          '<div class="interview-info">' +
            '<span class="interview-name">' + escapeHtml(nome) + '</span>' +
            '<span class="interview-role">' + escapeHtml(cargo) + '</span>' +
          '</div>' +
          '<span class="interview-ai-tag font-mono">' + (answered > 0 ? 'PROCESSANDO' : answered + '/' + total + ' resp.') + '</span>' +
        '</div>' +
        '<div class="interview-tags">' +
          '<span class="interview-tag" style="color: var(--text-muted)">' + (areaLabels[area] || area.toUpperCase()) + '</span>' +
        '</div>' +
        '<div class="interview-footer">' +
          '<span class="interview-date font-mono">' + dateStr + '</span>' +
          '<span class="interview-duration font-mono">' + answered + '/' + total + ' respostas</span>' +
        '</div>';

      var grid = document.getElementById('interview-grid');
      if (grid) {
        grid.insertBefore(card, grid.firstChild);
        var emptyState = document.getElementById('interview-empty');
        if (emptyState) emptyState.style.display = 'none';
      loadInterviewCount();
      }

      // Reset form
      btnClear.click();
      btnSave.textContent = 'Salvar Entrevista';
      btnSave.disabled = false;
    })
    .catch(function(err) {
      alert('Erro: ' + err.message);
      btnSave.textContent = 'Salvar Entrevista';
      btnSave.disabled = false;
    });
  });
}

/* ── Area Filter — filter interview cards by department ────────────────── */
function initAreaFilter() {
  var tabs = document.querySelectorAll('.area-tab[data-area-filter]');
  if (!tabs.length) return;

  tabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
      var filter = tab.getAttribute('data-area-filter');
      tabs.forEach(function(t) { t.classList.toggle('active', t === tab); });

      var cards = document.querySelectorAll('.interview-card');
      cards.forEach(function(card) {
        var cardArea = card.getAttribute('data-interview-area');
        if (filter === 'all' || cardArea === filter) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   FORM EXPORT / IMPORT
   ══════════════════════════════════════════════════════════════════════════ */

function initFormExportImport() {
  // ── EXPORT (.docx via backend) ──
  var btnExport = document.getElementById('btn-export-form');
  if (btnExport) {
    btnExport.addEventListener('click', function() {
      var area = document.getElementById('export-area').value;
      var nome = document.getElementById('export-nome').value.trim();
      var cargo = document.getElementById('export-cargo').value.trim();

      if (!area) { alert('Selecione uma \u00e1rea'); return; }

      var params = new URLSearchParams({ interviewee: nome, role: cargo });
      var url = '/api/forms/export/' + area + '?' + params.toString();

      // Download .docx
      var a = document.createElement('a');
      a.href = url;
      a.download = 'formulario_' + area + '.docx';
      a.click();
    });
  }

  // ── IMPORT ──
  var dropzone = document.getElementById('import-dropzone');
  var fileInput = document.getElementById('import-file');
  var preview = document.getElementById('import-preview');
  var previewContent = document.getElementById('import-preview-content');
  var btnCancel = document.getElementById('btn-import-cancel');
  var btnConfirm = document.getElementById('btn-import-confirm');
  var importedData = null;

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', function() { fileInput.click(); });

  dropzone.addEventListener('dragover', function(e) {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', function() {
    dropzone.classList.remove('dragover');
  });
  dropzone.addEventListener('drop', function(e) {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) processImportFile(e.dataTransfer.files[0]);
  });

  fileInput.addEventListener('change', function() {
    if (fileInput.files.length) processImportFile(fileInput.files[0]);
  });

  function processImportFile(file) {
    if (!file.name.endsWith('.docx')) {
      alert('Apenas arquivos .docx s\u00e3o aceitos');
      return;
    }

    var formData = new FormData();
    formData.append('file', file);

    fetch('/api/forms/import', { method: 'POST', body: formData })
      .then(function(r) { return r.json(); })
      .then(function(result) {
        if (result.status === 'ok' && result.data) {
          importedData = result.data;
          importedData.answeredCount = result.data.questions_answered;
          importedData.totalCount = result.data.questions_total;

          previewContent.textContent =
            'Entrevistado: ' + (importedData.interviewee || '(vazio)') + '\n' +
            'Cargo: ' + (importedData.role || '(vazio)') + '\n' +
            '\u00c1rea: ' + (importedData.department || '(vazio)') + '\n' +
            'Data: ' + (importedData.date || '(vazio)') + '\n' +
            'Perguntas respondidas: ' + importedData.answeredCount + '/' + importedData.totalCount + '\n\n' +
            'Transcri\u00e7\u00e3o (' + (importedData.transcript || '').length + ' caracteres):\n' +
            (importedData.transcript || '').substring(0, 500) + ((importedData.transcript || '').length > 500 ? '...' : '');
          dropzone.style.display = 'none';
          preview.style.display = 'block';
        } else {
          alert(result.detail || 'Erro ao processar arquivo');
        }
      })
      .catch(function(err) {
        alert('Erro ao importar: ' + err.message);
      });
  }

  if (btnCancel) {
    btnCancel.addEventListener('click', function() {
      preview.style.display = 'none';
      dropzone.style.display = '';
      fileInput.value = '';
      importedData = null;
    });
  }

  if (btnConfirm) {
    btnConfirm.addEventListener('click', function() {
      if (!importedData) return;

      // Backend already saved during import, just trigger pipeline if needed
      // Create card visually
      var parts = importedData.interviewee.split(' ');
      var initials = (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
      var aiTag = importedData.answeredCount > 0 ? 'PROCESSANDO' : 'IMPORTADO';

      var card = document.createElement('div');
      card.className = 'interview-card';
      card.style.animation = 'fadeIn 0.3s ease-out';
      card.innerHTML =
        '<div class="interview-card-top">' +
          '<div class="interview-avatar">' + initials + '</div>' +
          '<div class="interview-info">' +
            '<span class="interview-name">' + escapeHtml(importedData.interviewee) + '</span>' +
            '<span class="interview-role">' + escapeHtml(importedData.role) + '</span>' +
          '</div>' +
          '<span class="interview-ai-tag font-mono">' + aiTag + '</span>' +
        '</div>' +
        '<div class="interview-footer">' +
          '<span class="interview-date font-mono">' + escapeHtml(importedData.date) + '</span>' +
          '<span class="interview-duration font-mono">' + importedData.answeredCount + '/' + importedData.totalCount + ' respostas</span>' +
        '</div>';

      var grid = document.getElementById('interview-grid');
      if (grid) {
        grid.insertBefore(card, grid.firstChild);
        var emptyState = document.getElementById('interview-empty');
        if (emptyState) emptyState.style.display = 'none';
      loadInterviewCount();
      }

      // Reset import
      preview.style.display = 'none';
      dropzone.style.display = '';
      fileInput.value = '';
      importedData = null;
    });
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   AUTH — Logout + Current User
   ══════════════════════════════════════════════════════════════════════════ */

function initLogout() {
  var btn = document.getElementById('btn-logout');
  if (!btn) return;
  btn.addEventListener('click', function() {
    fetch('/api/auth/logout', { method: 'POST' })
      .then(function() { window.location.href = '/login'; })
      .catch(function() { window.location.href = '/login'; });
  });
}

function initCurrentUser() {
  fetch('/api/auth/me')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status !== 'ok') return;
      var user = data.user;
      var avatar = document.getElementById('topbar-avatar');
      if (avatar && user.name) {
        var parts = user.name.split(' ');
        avatar.textContent = (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
      }
      // Hide Usuarios tab for non-admins
      if (user.role !== 'admin') {
        var usrLink = document.querySelector('[data-page="usuarios"]');
        if (usrLink) usrLink.style.display = 'none';
      }
    })
    .catch(function() {});
}

/* ══════════════════════════════════════════════════════════════════════════
   USER MANAGEMENT — CRUD
   ══════════════════════════════════════════════════════════════════════════ */

function initUserManagement() {
  var btnNovo = document.getElementById('btn-novo-usuario');
  var modal = document.getElementById('modal-usuario');
  var closeBtn = document.getElementById('modal-usuario-close');
  var cancelBtn = document.getElementById('modal-usuario-cancel');
  var form = document.getElementById('form-usuario');

  if (!btnNovo || !modal) return;

  function openUserModal(editUser) {
    var titleEl = document.getElementById('modal-usuario-title');
    var editIdEl = document.getElementById('usr-edit-id');
    var usernameEl = document.getElementById('usr-username');
    var passLabel = document.getElementById('usr-pass-label');
    var passInput = document.getElementById('usr-password');

    if (editUser) {
      titleEl.textContent = 'Editar Usu\u00e1rio';
      editIdEl.value = editUser.id;
      usernameEl.value = editUser.username;
      usernameEl.disabled = true;
      document.getElementById('usr-name').value = editUser.name || '';
      document.getElementById('usr-email').value = editUser.email || '';
      document.getElementById('usr-role').value = editUser.role || 'viewer';
      passLabel.textContent = 'Nova Senha (deixe vazio para manter)';
      passInput.required = false;
      passInput.value = '';
    } else {
      titleEl.textContent = 'Novo Usu\u00e1rio';
      editIdEl.value = '';
      usernameEl.disabled = false;
      passLabel.textContent = 'Senha*';
      passInput.required = true;
      form.reset();
    }
    modal.style.display = 'flex';
  }

  function closeUserModal() {
    modal.style.display = 'none';
    form.reset();
    document.getElementById('usr-username').disabled = false;
  }

  btnNovo.addEventListener('click', function() { openUserModal(null); });
  closeBtn.addEventListener('click', closeUserModal);
  cancelBtn.addEventListener('click', closeUserModal);
  modal.addEventListener('click', function(e) { if (e.target === modal) closeUserModal(); });

  // Submit
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    var editId = document.getElementById('usr-edit-id').value;
    var isEdit = editId && editId !== '';

    if (isEdit) {
      var payload = {
        name: document.getElementById('usr-name').value,
        email: document.getElementById('usr-email').value,
        role: document.getElementById('usr-role').value,
      };
      var pass = document.getElementById('usr-password').value;
      if (pass) payload.password = pass;

      fetch('/api/users/' + editId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(function(r) { return r.json(); })
      .then(function() { closeUserModal(); loadUsersTable(); });
    } else {
      var pass = document.getElementById('usr-password').value;
      if (pass.length < 6) { alert('Senha deve ter no m\u00ednimo 6 caracteres'); return; }

      fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: document.getElementById('usr-username').value,
          name: document.getElementById('usr-name').value,
          email: document.getElementById('usr-email').value,
          role: document.getElementById('usr-role').value,
          password: pass
        })
      }).then(function(r) { return r.json(); })
      .then(function() { closeUserModal(); loadUsersTable(); });
    }
  });

  // Delegate edit/delete clicks
  document.addEventListener('click', function(e) {
    var editBtn = e.target.closest('[data-edit-user]');
    if (editBtn) {
      var userData = JSON.parse(editBtn.getAttribute('data-edit-user'));
      openUserModal(userData);
      return;
    }
    var deleteBtn = e.target.closest('[data-delete-user]');
    if (deleteBtn) {
      var userId = deleteBtn.getAttribute('data-delete-user');
      var userName = deleteBtn.getAttribute('data-delete-name');
      if (confirm('Excluir usu\u00e1rio "' + userName + '"?')) {
        fetch('/api/users/' + userId, { method: 'DELETE' })
          .then(function(r) { return r.json(); })
          .then(function(data) {
            if (data.status === 'ok') loadUsersTable();
            else alert(data.detail || 'Erro ao excluir');
          });
      }
    }
  });

  // Load on page navigate
  var origNavigate = window.navigateTo;
}

function loadUsersTable() {
  fetch('/api/users')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status !== 'ok') return;
      var tbody = document.getElementById('users-tbody');
      if (!tbody) return;

      var roleClasses = { admin: 'role-badge--admin', editor: 'role-badge--editor', viewer: 'role-badge--viewer' };
      var roleLabels = { admin: 'ADMIN', editor: 'EDITOR', viewer: 'VIEWER' };

      tbody.innerHTML = data.users.map(function(u) {
        var roleClass = roleClasses[u.role] || '';
        var roleLabel = roleLabels[u.role] || u.role;
        var statusClass = u.active ? 'user-status-active' : 'user-status-inactive';
        var statusText = u.active ? 'Ativo' : 'Inativo';
        var userData = JSON.stringify(u).replace(/"/g, '&quot;');

        return '<tr>' +
          '<td><span class="font-mono">' + escapeHtml(u.username) + '</span></td>' +
          '<td>' + escapeHtml(u.name || '\u2014') + '</td>' +
          '<td>' + escapeHtml(u.email || '\u2014') + '</td>' +
          '<td><span class="role-badge ' + roleClass + ' font-mono">' + roleLabel + '</span></td>' +
          '<td><span class="' + statusClass + '">' + statusText + '</span></td>' +
          '<td class="user-actions">' +
            '<button class="user-action-btn" data-edit-user="' + userData + '">Editar</button>' +
            '<button class="user-action-btn user-action-btn--danger" data-delete-user="' + u.id + '" data-delete-name="' + escapeHtml(u.username) + '">Excluir</button>' +
          '</td>' +
        '</tr>';
      }).join('');
    })
    .catch(function() {});
}

/* ══════════════════════════════════════════════════════════════════════════ */

function renderMarkdown(text) {
  // Basic markdown → HTML
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="section-heading">$1</h3>')
    .replace(/^# (.+)$/gm, '<h2 class="section-heading">$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code class="font-mono">$1</code>')
    .replace(/^\- (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^/, '<p>').replace(/$/, '</p>');
}

/* ══════════════════════════════════════════════════════════════════════════
   STRATEGY — Per-area strategy generation and display
   ══════════════════════════════════════════════════════════════════════════ */

var _activeStrategyArea = null;

var _AREA_LABELS = {
  'supply-chain': 'Supply Chain', 'producao': 'Produção / PCP', 'comercial': 'Comercial / Vendas',
  'logistica': 'Logística', 'ti': 'Tecnologia / TI', 'financeiro': 'Financeiro / Controladoria',
  'qualidade': 'Qualidade', 'compras': 'Compras / Procurement', 'rh': 'RH / Pessoas', 'diretoria': 'Diretoria Geral'
};

function _loadAreaTabs(containerId, dataAttr, callback) {
  fetch('/api/interviews')
    .then(function(res) { return res.json(); })
    .then(function(data) {
      var interviews = data.interviews || data || [];
      if (!Array.isArray(interviews)) return;
      var areas = {};
      interviews.forEach(function(iv) {
        if (iv.transcript && iv.department) {
          areas[iv.department] = (areas[iv.department] || 0) + 1;
        }
      });
      var container = document.getElementById(containerId);
      if (!container || !Object.keys(areas).length) return;
      var html = '';
      Object.keys(areas).sort().forEach(function(a) {
        html += '<button class="area-tab" ' + dataAttr + '="' + a + '">' +
          (_AREA_LABELS[a] || a) + ' <span class="font-mono" style="opacity:0.5">(' + areas[a] + ')</span></button>';
      });
      container.innerHTML = html;
      if (callback) callback();
    });
}

function initStrategy() {
  // Area select change
  var stratSelect = document.getElementById('strategy-area-select');
  if (!stratSelect) return;
  stratSelect.addEventListener('change', function() {
    _activeStrategyArea = this.value || null;
    if (_activeStrategyArea) {
      document.getElementById('strategy-tabs').style.display = '';
      loadStrategyData(_activeStrategyArea);
    } else {
      document.getElementById('strategy-tabs').style.display = 'none';
    }
  });

  // Strategy sub-tabs
  document.getElementById('strategy-tabs').addEventListener('click', function(e) {
    var tab = e.target.closest('.tab');
    if (!tab) return;
    var target = tab.getAttribute('data-stab');
    this.querySelectorAll('.tab').forEach(function(t) { t.classList.toggle('active', t.getAttribute('data-stab') === target); });
    document.querySelectorAll('.stab-content').forEach(function(el) {
      el.style.display = el.id === ('stab-' + target) ? '' : 'none';
    });
  });

  // ── Pipeline mode selector + trigger ──
  var pipelineModeSelect = document.getElementById('pipeline-mode-select');
  var pipelineModeHint = document.getElementById('pipeline-mode-hint');
  if (pipelineModeSelect && pipelineModeHint) {
    pipelineModeSelect.addEventListener('change', function() {
      var area = this.value;
      if (area) {
        var label = this.options[this.selectedIndex].text;
        pipelineModeHint.textContent = 'Por \u00e1rea: analisa apenas entrevistas de ' + label;
      } else {
        pipelineModeHint.textContent = 'Consolidado: analisa todas as \u00e1reas e gera vis\u00e3o global';
      }
    });
  }

  var btnRodarPipeline = document.getElementById('btn-rodar-pipeline');
  if (btnRodarPipeline) {
    btnRodarPipeline.addEventListener('click', function() {
      var area = pipelineModeSelect ? pipelineModeSelect.value : '';
      var modeLabel = area ? pipelineModeSelect.options[pipelineModeSelect.selectedIndex].text : 'todas as \u00e1reas';
      if (!confirm('Rodar diagn\u00f3stico IA para ' + modeLabel + '?\n\nIsso pode levar alguns minutos.')) return;
      triggerPipeline(area || null);
    });
  }

  // Generate strategy button
  document.getElementById('btn-gerar-estrategia').addEventListener('click', function() {
    if (!_activeStrategyArea) {
      alert('Selecione uma área primeiro');
      return;
    }
    fetch('/api/strategy/run?area=' + encodeURIComponent(_activeStrategyArea), { method: 'POST' })
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if (data.status === 'ok') {
          pollPipelineStatus();
          document.getElementById('stab-macro').innerHTML = '<div class="empty-state"><p class="empty-text">Gerando estrat&eacute;gia... Acompanhe o progresso no banner acima.</p></div>';
        } else if (data.status === 'already_running') {
          alert('Pipeline já está rodando. Aguarde a conclusão.');
        }
      });
  });
}

function loadStrategyData(area) {
  if (!area) return;
  fetch('/api/strategy?area=' + encodeURIComponent(area))
    .then(function(res) { return res.json(); })
    .then(function(data) {
      if (data.status !== 'ok') return;

      var tabs = [
        { id: 'stab-macro', content: data.macro, title: 'Roadmap Estrat&eacute;gico Macro', empty: 'Roadmap macro n&atilde;o gerado. Clique em &ldquo;Gerar estrat&eacute;gia&rdquo;.' },
        { id: 'stab-tatico', content: data.tatico, title: 'Roadmap T&aacute;tico (Micro Entreg&aacute;veis)', empty: 'Roadmap t&aacute;tico n&atilde;o gerado.' },
        { id: 'stab-automacao', content: data.automacao, title: 'Estrat&eacute;gia de Automa&ccedil;&atilde;o', empty: 'Estrat&eacute;gia de automa&ccedil;&atilde;o n&atilde;o gerada.' }
      ];

      tabs.forEach(function(tab) {
        var el = document.getElementById(tab.id);
        if (!el) return;
        if (tab.content) {
          el.innerHTML = '<div class="card-section">' +
            '<h3 class="card-label-heading">' + tab.title + '</h3>' +
            '<div class="agent-output-content" style="font-size:0.85rem;line-height:1.6;white-space:pre-wrap;max-height:700px;overflow-y:auto;padding:var(--space-4);background:var(--bg-secondary);border-radius:var(--radius-md)">' +
            renderMarkdown(tab.content) +
            '</div></div>';
        } else {
          el.innerHTML = '<div class="empty-state"><p class="empty-text">' + tab.empty + '</p></div>';
        }
      });
    });
}

/* ══════════════════════════════════════════════════════════════════════════
   ROADMAP — Per-area roadmap display (from ATLAS agent)
   ══════════════════════════════════════════════════════════════════════════ */

var _activeRoadmapArea = null;

function initRoadmap() {
  var roadmapSelect = document.getElementById('roadmap-area-select');
  if (!roadmapSelect) return;
  roadmapSelect.addEventListener('change', function() {
    _activeRoadmapArea = this.value || null;
    if (_activeRoadmapArea) {
      loadRoadmapData(_activeRoadmapArea);
    }
  });
}

function loadRoadmapData(area) {
  if (!area) return;
  fetch('/api/analysis?area=' + encodeURIComponent(area))
    .then(function(res) { return res.json(); })
    .then(function(data) {
      if (data.status !== 'ok') return;
      var container = document.getElementById('roadmap-content');
      if (!container) return;
      var analysis = data.analysis || {};
      var areaLabel = _AREA_LABELS[area] || area;

      // Roadmap ATLAS
      var roadmapContent = analysis.roadmap_atlas ? (analysis.roadmap_atlas.content || analysis.roadmap_atlas) : '';
      // Gaps STRATEGOS
      var gapsContent = analysis.gaps ? (analysis.gaps.content || analysis.gaps) : '';

      if (!roadmapContent && !gapsContent) {
        container.innerHTML = '<div class="empty-state"><p class="empty-text">Nenhum roadmap gerado para <strong>' + escapeHtml(areaLabel) + '</strong>. Execute o pipeline desta &aacute;rea primeiro.</p></div>';
        return;
      }

      var html = '';
      if (roadmapContent) {
        html += '<div class="card-section" style="margin-bottom:var(--space-6)">' +
          '<h3 class="card-label-heading">&#9776; ATLAS &mdash; Roadmap de ' + escapeHtml(areaLabel) + '</h3>' +
          '<div class="agent-output-content" style="font-size:0.85rem;line-height:1.6;white-space:pre-wrap;max-height:600px;overflow-y:auto;padding:var(--space-4);background:var(--bg-secondary);border-radius:var(--radius-md)">' +
          renderMarkdown(roadmapContent) +
          '</div></div>';
      }
      if (gapsContent) {
        html += '<div class="card-section">' +
          '<h3 class="card-label-heading">&#9654; STRATEGOS &mdash; Gaps de ' + escapeHtml(areaLabel) + '</h3>' +
          '<div class="agent-output-content" style="font-size:0.85rem;line-height:1.6;white-space:pre-wrap;max-height:600px;overflow-y:auto;padding:var(--space-4);background:var(--bg-secondary);border-radius:var(--radius-md)">' +
          renderMarkdown(gapsContent) +
          '</div></div>';
      }
      container.innerHTML = html;
    });
}

/* ══════════════════════════════════════════════════════════════════════════
   VEXIA — BPO area filters + transcription loader
   ══════════════════════════════════════════════════════════════════════════ */

function initVexia() {
  // Area filter tabs
  var filterBar = document.getElementById('vexia-area-filter');
  if (!filterBar) return;

  var tabs = filterBar.querySelectorAll('[data-vexia-area]');
  var cards = document.querySelectorAll('.vexia-area-card');

  tabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
      tabs.forEach(function(t) { t.classList.remove('active'); });
      tab.classList.add('active');
      var area = tab.getAttribute('data-vexia-area');
      cards.forEach(function(card) {
        if (area === 'all' || card.getAttribute('data-vexia-area') === area) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // Load transcription
  fetch('/api/vexia/transcricao')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status === 'ok') {
        var el = document.getElementById('vexia-transcricao');
        if (el) el.textContent = data.text;
      }
    })
    .catch(function() {});
}

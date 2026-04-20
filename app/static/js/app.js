/* ══════════════════════════════════════��════════════════════════════════════
   Stoken Advisory — Platform JS
   Client-side routing, sidebar, theme toggle
   ════════════════════���══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function() {
  initThemeToggle();
  initSidebar();
  initRouter();
  initDiagTabs();
  initInsightFilters();
  initInsightReadmore();
  initNovaEntrevista();
  initDiagActions();
  try { initAgents(); } catch(e) { console.warn('Agents init:', e); }
});

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
    navigateTo('diagnostico');
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
  'diagnostico': 'Diagn\u00f3stico',
  'insights': 'Insights',
  'roadmap': 'Roadmap',
  'agentes': 'Agentes IA',
  'configuracoes': 'Configura\u00e7\u00f5es'
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
}

/* ── Diagnostico Tabs ──────────────────────────────────────────────────── */
function initDiagTabs() {
  var tabs = document.querySelectorAll('[data-dtab]');
  if (!tabs.length) return;

  tabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
      var target = tab.getAttribute('data-dtab');

      // Update tab active state
      tabs.forEach(function(t) { t.classList.toggle('active', t === tab); });

      // Show/hide tab content
      var contents = document.querySelectorAll('.dtab-content');
      contents.forEach(function(c) {
        c.style.display = c.id === 'dtab-' + target ? 'block' : 'none';
      });
    });
  });
}

/* ── Insight Filters (functional) ──────────────────────────────────────── */
function initInsightFilters() {
  var filters = document.querySelectorAll('.insight-filter');
  if (!filters.length) return;

  filters.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var category = btn.getAttribute('data-filter');
      filters.forEach(function(f) { f.classList.toggle('active', f === btn); });

      var items = document.querySelectorAll('.insight-item');
      var dividers = document.querySelectorAll('.insight-divider');

      items.forEach(function(item) {
        if (category === 'all' || item.getAttribute('data-category') === category) {
          item.classList.remove('hidden');
        } else {
          item.classList.add('hidden');
        }
      });

      // Show/hide dividers based on visible adjacent items
      dividers.forEach(function(d) {
        var prev = d.previousElementSibling;
        var next = d.nextElementSibling;
        var prevVisible = prev && !prev.classList.contains('hidden') && prev.classList.contains('insight-item');
        var nextVisible = next && !next.classList.contains('hidden') && next.classList.contains('insight-item');
        d.classList.toggle('hidden', !prevVisible || !nextVisible);
      });
    });
  });
}

/* ── Insight "ler mais" — expand truncated text ───────────────────────── */
function initInsightReadmore() {
  // Bind directly to each link instead of delegation
  var links = document.querySelectorAll('.insight-readmore');
  links.forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      var body = link.closest('.insight-body');
      if (body) {
        var isExpanded = body.classList.toggle('expanded');
        link.textContent = isExpanded ? 'recolher' : 'ler mais';
      }
    });
  });
}

/* ── Diagnostico Actions — Rodar diag + Agente dropdown + Pilar links ── */
function initDiagActions() {
  // "Rodar diagnóstico completo" → navigate to ARIA agent with full diagnostic prompt
  var btnRodar = document.getElementById('btn-rodar-diag');
  if (btnRodar) {
    btnRodar.addEventListener('click', function() {
      navigateTo('agentes');
      setTimeout(function() {
        // Open ARIA agent chat
        currentAgent = 'aria';
        openAgentChat('aria');
        // Pre-fill the input
        var input = document.getElementById('agent-input');
        if (input) {
          input.value = 'Execute o diagn\u00f3stico completo de maturidade da Santista S.A. nos 5 pilares (Processos, Sistemas & Dados, Opera\u00e7\u00f5es, Organiza\u00e7\u00e3o, Roadmap). Para cada pilar, forne\u00e7a: score de 1 a 5, justificativa, gap vs benchmark do setor t\u00eaxtil, e top 3 a\u00e7\u00f5es recomendadas.';
        }
      }, 100);
    });
  }

  // "Agente individual ▾" dropdown
  var btnDropdown = document.getElementById('btn-agente-dropdown');
  var dropdown = document.getElementById('dropdown-agentes');
  if (btnDropdown && dropdown) {
    btnDropdown.addEventListener('click', function(e) {
      e.stopPropagation();
      dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    });

    // Close dropdown on outside click
    document.addEventListener('click', function() {
      dropdown.style.display = 'none';
    });

    // Dropdown items → navigate to agent
    dropdown.querySelectorAll('[data-goto-agent]').forEach(function(item) {
      item.addEventListener('click', function(e) {
        e.preventDefault();
        var agentId = item.getAttribute('data-goto-agent');
        dropdown.style.display = 'none';
        navigateTo('agentes');
        setTimeout(function() {
          currentAgent = agentId;
          openAgentChat(agentId);
        }, 100);
      });
    });
  }

  // "Gerar agora →" on pilar cards → navigate to ARIA with pilar-specific prompt
  document.addEventListener('click', function(e) {
    var link = e.target.closest('[data-run-pilar]');
    if (link) {
      e.preventDefault();
      var pilar = link.getAttribute('data-run-pilar');
      navigateTo('agentes');
      setTimeout(function() {
        currentAgent = 'aria';
        openAgentChat('aria');
        var input = document.getElementById('agent-input');
        if (input) {
          input.value = 'Analise o pilar "' + pilar + '" da Santista S.A. em detalhe. Forne\u00e7a: score CMMI (1-5), justificativa com evid\u00eancias, gap vs benchmark ABIT, e as 5 a\u00e7\u00f5es mais urgentes priorizadas por impacto.';
        }
      }, 100);
    }
  });
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
      'Como \u00e9 feita a gest\u00e3o de riscos da cadeia (fornecedores, log\u00edstica, demanda)?'
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
      'Como \u00e9 feito o sequenciamento de produ\u00e7\u00e3o? Quais crit\u00e9rios de prioriza\u00e7\u00e3o?'
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
      'Quais s\u00e3o as principais reclama\u00e7\u00f5es de clientes sobre entrega e atendimento?'
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
      'Como \u00e9 feita a roteiriza\u00e7\u00e3o de entregas? Manual ou otimizada?'
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
      'Como \u00e9 o suporte de TI para a opera\u00e7\u00e3o? Qual o SLA?'
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
      'Quais KPIs financeiros s\u00e3o acompanhados com frequ\u00eancia mensal?'
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
      'A empresa tem certifica\u00e7\u00f5es ISO? Como \u00e9 a manuten\u00e7\u00e3o?'
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
      'Qual o saving anual gerado pela \u00e1rea de compras?'
    ]
  },
  'rh': {
    title: 'RH / Pessoas',
    questions: [
      'Como est\u00e1 estruturada a equipe de supply chain? Quantas pessoas por \u00e1rea?',
      'Existe programa de capacita\u00e7\u00e3o t\u00e9cnica para a equipe?',
      'Qual o turnover da \u00e1rea? Quais os cargos mais cr\u00edticos para reter?',
      'Existe clareza de pap\u00e9is e responsabilidades (RACI) nos processos-chave?',
      'Como funciona a comunica\u00e7\u00e3o entre turnos e entre \u00e1reas?',
      'Existem programas de reconhecimento por performance operacional?'
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
      'O que a diretoria considera como \u201cestado ideal\u201d da opera\u00e7\u00e3o em 3 anos?'
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
  'processos':   { label: 'PROCESSOS',      color: 'var(--pilar-processos)',   title: 'Processos & Governan\u00e7a' },
  'sistemas':    { label: 'SISTEMAS',        color: 'var(--pilar-sistemas)',    title: 'Sistemas & Dados' },
  'operacoes':   { label: 'OPERA\u00c7\u00d5ES', color: 'var(--pilar-operacoes)', title: 'Opera\u00e7\u00f5es & Log\u00edstica' },
  'organizacao': { label: 'ORGANIZA\u00c7\u00c3O', color: 'var(--pilar-organizacao)', title: 'Organiza\u00e7\u00e3o & Pessoas' },
  'roadmap':     { label: 'ROADMAP',         color: 'var(--pilar-roadmap)',     title: 'Estrat\u00e9gia & Roadmap' }
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

  // Open modal
  btn.addEventListener('click', function() {
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
    var iaReady = document.getElementById('ent-ia-ready').checked;
    var transcricao = document.getElementById('ent-transcricao').value.trim();

    if (!nome || !cargo) return;

    // Generate initials
    var parts = nome.split(' ');
    var initials = (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();

    // Format date
    var dateStr = 'Hoje';
    if (data) {
      var d = new Date(data + 'T12:00:00');
      var months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
      dateStr = d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
    }

    var pilarInfo = PILAR_MAP[pilar];
    var tagHtml = pilarInfo ? '<span class="interview-tag" style="color:' + pilarInfo.color + '">' + pilarInfo.label + '</span>' : '';
    var aiTag = iaReady ? 'AI ANALYZED' : (transcricao ? 'TRANSCRITO' : 'NOVO');

    // Create card
    var card = document.createElement('div');
    card.className = 'interview-card';
    card.style.animation = 'fadeIn 0.3s ease-out';
    card.innerHTML =
      '<div class="interview-card-top">' +
        '<div class="interview-avatar">' + initials + '</div>' +
        '<div class="interview-info">' +
          '<span class="interview-name">' + escapeHtml(nome) + '</span>' +
          '<span class="interview-role">' + escapeHtml(cargo) + '</span>' +
        '</div>' +
        '<span class="interview-ai-tag font-mono">' + aiTag + '</span>' +
      '</div>' +
      (tagHtml ? '<div class="interview-tags">' + tagHtml + '</div>' : '') +
      '<div class="interview-footer">' +
        '<span class="interview-date font-mono">' + dateStr + '</span>' +
      '</div>';

    var grid = document.querySelector('.interview-grid');
    if (grid) grid.insertBefore(card, grid.firstChild);

    closeModal();
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
  'atlas':     { name: 'ATLAS',     role: 'Roadmap & Transforma\u00e7\u00e3o' }
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

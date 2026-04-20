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
  initNovaEntrevista();
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

/* ── Insight Filters ───────────────────────────────────────────────────── */
function initInsightFilters() {
  var filters = document.querySelectorAll('.insight-filter');
  if (!filters.length) return;

  filters.forEach(function(btn) {
    btn.addEventListener('click', function() {
      filters.forEach(function(f) { f.classList.toggle('active', f === btn); });
    });
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   NOVA ENTREVISTA — Modal + dynamic card creation
   ══════════════════════════════════════════════════════════════════════════ */

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

  // Pilar selector → update questions
  if (pilarSelect) {
    pilarSelect.addEventListener('change', function() {
      var val = pilarSelect.value;
      // Hide all question sets
      document.querySelectorAll('.question-set').forEach(function(qs) { qs.style.display = 'none'; });
      // Show matching
      var target = document.querySelector('.question-set[data-pilar-q="' + val + '"]');
      if (target) target.style.display = '';
      // Update title
      if (questionsTitle && PILAR_MAP[val]) {
        questionsTitle.textContent = 'Perguntas gerais para ' + PILAR_MAP[val].title;
      }
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
  loadingDiv.innerHTML = '<div class="agent-msg-label font-mono">' + (AGENT_INFO[currentAgent]?.name || 'AGENTE') + '</div><div class="agent-msg-text"><span class="agent-typing">Analisando</span></div>';
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

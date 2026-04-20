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
      // Future: actual filtering logic
    });
  });
}

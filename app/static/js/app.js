/* ═══════════════════════════════════════════════════════════════════════════
   AI Supply Chain — Santista S.A.
   Frontend Interactions & Animations
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  initNavScroll();
  initRevealAnimations();
  initCounters();
  initPlayground();
  initChartAnimation();
});

/* ── Nav scroll effect ──────────────────────────────────────────────────── */
function initNavScroll() {
  const nav = document.querySelector('.nav');
  if (!nav) return;

  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        nav.classList.toggle('scrolled', window.scrollY > 20);
        ticking = false;
      });
      ticking = true;
    }
  });
}

/* ── Scroll reveal ──────────────────────────────────────────────────────── */
function initRevealAnimations() {
  const elements = document.querySelectorAll('.reveal');
  if (!elements.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  elements.forEach(el => observer.observe(el));
}

/* ── Animated counters ──────────────────────────────────────────────────── */
function initCounters() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(el => observer.observe(el));
}

function animateCounter(el) {
  const target = parseInt(el.dataset.count, 10);
  const suffix = el.dataset.suffix || '';
  const prefix = el.dataset.prefix || '';
  const duration = 1500;
  const start = performance.now();

  function update(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 4); // ease-out quart
    const current = Math.round(eased * target);

    el.innerHTML = prefix + current.toLocaleString('pt-BR') +
      (suffix ? `<span class="stat-suffix">${suffix}</span>` : '');

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

/* ── API Playground ─────────────────────────────────────────────────────── */
function initPlayground() {
  const tabs = document.querySelectorAll('.playground-tab');
  const requestBlock = document.getElementById('request-code');
  const responseBlock = document.getElementById('response-code');
  const runBtn = document.getElementById('run-btn');
  const statusBadge = document.getElementById('response-status');

  if (!tabs.length || !requestBlock) return;

  const endpoints = {
    forecast: {
      request: `<span class="code-comment">// POST /forecast</span>
<span class="code-bracket">{</span>
  <span class="code-key">"data"</span>: <span class="code-bracket">[</span>
    <span class="code-bracket">{</span>
      <span class="code-key">"sku"</span>: <span class="code-string">"FIO-ALG-40NE"</span>,
      <span class="code-key">"client"</span>: <span class="code-string">"P&G Brasil"</span>,
      <span class="code-key">"sales"</span>: <span class="code-number">12500</span>,
      <span class="code-key">"stock"</span>: <span class="code-number">8200</span>,
      <span class="code-key">"cost"</span>: <span class="code-number">18.50</span>
    <span class="code-bracket">}</span>
  <span class="code-bracket">]</span>
<span class="code-bracket">}</span>`,
      response: `<span class="code-bracket">{</span>
  <span class="code-key">"status"</span>: <span class="code-string">"ok"</span>,
  <span class="code-key">"results"</span>: <span class="code-bracket">[</span>
    <span class="code-bracket">{</span>
      <span class="code-key">"sku"</span>: <span class="code-string">"FIO-ALG-40NE"</span>,
      <span class="code-key">"client"</span>: <span class="code-string">"P&G Brasil"</span>,
      <span class="code-key">"forecast_30d"</span>: <span class="code-number">16250.00</span>,
      <span class="code-key">"daily_avg"</span>: <span class="code-number">541.67</span>,
      <span class="code-key">"days_of_stock"</span>: <span class="code-number">15.14</span>,
      <span class="code-key">"risk"</span>: <span class="code-string">"ATEN\u00c7\u00c3O"</span>,
      <span class="code-key">"is_priority"</span>: <span class="code-number">true</span>
    <span class="code-bracket">}</span>
  <span class="code-bracket">]</span>
<span class="code-bracket">}</span>`
    },
    inventory: {
      request: `<span class="code-comment">// POST /inventory</span>
<span class="code-bracket">{</span>
  <span class="code-key">"data"</span>: <span class="code-bracket">[</span>
    <span class="code-bracket">{</span>
      <span class="code-key">"sku"</span>: <span class="code-string">"TEC-POLI-001"</span>,
      <span class="code-key">"client"</span>: <span class="code-string">"Magazine Luiza"</span>,
      <span class="code-key">"sales"</span>: <span class="code-number">9800</span>,
      <span class="code-key">"stock"</span>: <span class="code-number">35000</span>,
      <span class="code-key">"cost"</span>: <span class="code-number">22.30</span>
    <span class="code-bracket">}</span>
  <span class="code-bracket">]</span>
<span class="code-bracket">}</span>`,
      response: `<span class="code-bracket">{</span>
  <span class="code-key">"status"</span>: <span class="code-string">"ok"</span>,
  <span class="code-key">"results"</span>: <span class="code-bracket">[</span>
    <span class="code-bracket">{</span>
      <span class="code-key">"sku"</span>: <span class="code-string">"TEC-POLI-001"</span>,
      <span class="code-key">"client"</span>: <span class="code-string">"Magazine Luiza"</span>,
      <span class="code-key">"safety_stock"</span>: <span class="code-number">5387.10</span>,
      <span class="code-key">"reorder_point"</span>: <span class="code-number">7673.43</span>,
      <span class="code-key">"inventory_status"</span>: <span class="code-string">"EXCESSO"</span>,
      <span class="code-key">"suggested_order"</span>: <span class="code-number">0</span>,
      <span class="code-key">"stock_value_brl"</span>: <span class="code-number">780500.00</span>,
      <span class="code-key">"excess_alert"</span>: <span class="code-number">true</span>
    <span class="code-bracket">}</span>
  <span class="code-bracket">]</span>
<span class="code-bracket">}</span>`
    },
    pricing: {
      request: `<span class="code-comment">// POST /pricing</span>
<span class="code-bracket">{</span>
  <span class="code-key">"data"</span>: <span class="code-bracket">[</span>
    <span class="code-bracket">{</span>
      <span class="code-key">"sku"</span>: <span class="code-string">"MAL-TRK-220"</span>,
      <span class="code-key">"client"</span>: <span class="code-string">"Renner"</span>,
      <span class="code-key">"sales"</span>: <span class="code-number">6200</span>,
      <span class="code-key">"stock"</span>: <span class="code-number">4100</span>,
      <span class="code-key">"cost"</span>: <span class="code-number">31.80</span>
    <span class="code-bracket">}</span>
  <span class="code-bracket">]</span>
<span class="code-bracket">}</span>`,
      response: `<span class="code-bracket">{</span>
  <span class="code-key">"status"</span>: <span class="code-string">"ok"</span>,
  <span class="code-key">"results"</span>: <span class="code-bracket">[</span>
    <span class="code-bracket">{</span>
      <span class="code-key">"sku"</span>: <span class="code-string">"MAL-TRK-220"</span>,
      <span class="code-key">"client"</span>: <span class="code-string">"Renner"</span>,
      <span class="code-key">"cost"</span>: <span class="code-number">31.80</span>,
      <span class="code-key">"base_price"</span>: <span class="code-number">39.75</span>,
      <span class="code-key">"suggested_price"</span>: <span class="code-number">40.94</span>,
      <span class="code-key">"margin_pct"</span>: <span class="code-number">22.33</span>,
      <span class="code-key">"coverage_months"</span>: <span class="code-number">0.66</span>,
      <span class="code-key">"pricing_action"</span>: <span class="code-string">"PREMIUM"</span>
    <span class="code-bracket">}</span>
  <span class="code-bracket">]</span>
<span class="code-bracket">}</span>`
    }
  };

  let activeEndpoint = 'forecast';

  function setActive(name) {
    activeEndpoint = name;
    tabs.forEach(t => t.classList.toggle('active', t.dataset.endpoint === name));
    requestBlock.innerHTML = endpoints[name].request;
    if (responseBlock) {
      responseBlock.innerHTML = endpoints[name].response;
    }
    if (statusBadge) {
      statusBadge.style.opacity = '1';
    }
  }

  tabs.forEach(tab => {
    tab.addEventListener('click', () => setActive(tab.dataset.endpoint));
  });

  if (runBtn) {
    runBtn.addEventListener('click', () => {
      runBtn.innerHTML = '<span class="btn-icon">&#9655;</span> Executando...';
      runBtn.style.opacity = '0.7';

      setTimeout(() => {
        if (responseBlock) {
          responseBlock.innerHTML = endpoints[activeEndpoint].response;
          responseBlock.style.animation = 'fadeIn 0.3s ease-out';
        }
        if (statusBadge) {
          statusBadge.style.opacity = '1';
        }
        runBtn.innerHTML = '<span class="btn-icon">&#9655;</span> Executar';
        runBtn.style.opacity = '1';
      }, 800);
    });
  }

  // Initialize
  setActive('forecast');
}

/* ── Chart Animation ────────────────────────────────────────────────────── */
function initChartAnimation() {
  const bars = document.querySelectorAll('.chart-bar');
  if (!bars.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const barsInChart = entry.target.querySelectorAll('.chart-bar');
        barsInChart.forEach((bar, i) => {
          const targetHeight = bar.dataset.height || '50%';
          bar.style.height = '4px';
          setTimeout(() => {
            bar.style.transition = 'height 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
            bar.style.height = targetHeight;
          }, i * 40);
        });
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('.chart-area').forEach(area => observer.observe(area));
}

/* ── Smooth scroll for anchor links ─────────────────────────────────────── */
document.addEventListener('click', (e) => {
  const anchor = e.target.closest('a[href^="#"]');
  if (anchor) {
    e.preventDefault();
    const target = document.querySelector(anchor.getAttribute('href'));
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
});

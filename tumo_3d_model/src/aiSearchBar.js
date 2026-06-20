const SEARCH_ICON = `
  <svg class="ai-search-bar__icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
    <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/>
    <path d="M20 20l-3.5-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  </svg>`;

const GOOEY_FILTER = `
  <svg class="ai-search-bar__gooey-def" aria-hidden="true">
    <defs>
      <filter id="ai-gooey-effect">
        <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="blur"/>
        <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 19 -8" result="goo"/>
        <feComposite in="SourceGraphic" in2="goo" operator="atop"/>
      </filter>
    </defs>
  </svg>`;

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function isUnsupportedBrowser() {
  const ua = navigator.userAgent.toLowerCase();
  const isSafari = ua.includes('safari') && !ua.includes('chrome') && !ua.includes('chromium');
  const isChromeOnIos = ua.includes('crios');
  return isSafari || isChromeOnIos;
}

function spawnClickParticles(container, x, y) {
  for (let i = 0; i < 12; i += 1) {
    const dot = document.createElement('span');
    dot.className = 'ai-search-bar__click-particle';
    const angle = Math.random() * Math.PI * 2;
    const dist = 40 + Math.random() * 80;
    dot.style.left = `${x}px`;
    dot.style.top = `${y}px`;
    dot.style.setProperty('--dx', `${Math.cos(angle) * dist}px`);
    dot.style.setProperty('--dy', `${Math.sin(angle) * dist}px`);
    dot.style.background = `rgba(${120 + Math.floor(Math.random() * 100)}, ${80 + Math.floor(Math.random() * 120)}, 255, 0.85)`;
    container.appendChild(dot);
    dot.addEventListener('animationend', () => dot.remove(), { once: true });
  }
}

function buildParticles(container, count = 14) {
  container.innerHTML = '';
  for (let i = 0; i < count; i += 1) {
    const p = document.createElement('span');
    p.className = 'ai-search-bar__particle';
    p.style.left = `${8 + Math.random() * 84}%`;
    p.style.top = `${10 + Math.random() * 80}%`;
    p.style.setProperty('--dx', `${(Math.random() - 0.5) * 28}px`);
    p.style.setProperty('--dy', `${(Math.random() - 0.5) * 28}px`);
    p.style.animationDelay = `${Math.random() * 1.2}s`;
    p.style.animationDuration = `${1.4 + Math.random() * 1.4}s`;
    container.appendChild(p);
  }
}

export function mountAiSearchBar(mountEl, options = {}) {
  const {
    placeholder = 'Design this room…',
    onSearch,
    getDisabled = () => false,
  } = options;

  if (!mountEl) return null;

  mountEl.innerHTML = `
    ${GOOEY_FILTER}
    <form class="ai-search-bar" autocomplete="off">
      <div class="ai-search-bar__form-inner">
        <div class="ai-search-bar__track">
          <div class="ai-search-bar__gradient" aria-hidden="true"></div>
          <div class="ai-search-bar__particles-wrap" aria-hidden="true">
            <div class="ai-search-bar__particles"></div>
          </div>
          <div class="ai-search-bar__click-layer" aria-hidden="true"></div>
          <div class="ai-search-bar__icon-wrap">${SEARCH_ICON}</div>
          <input
            type="text"
            class="ai-search-bar__input"
            placeholder="${escapeHtml(placeholder)}"
            autocomplete="off"
            spellcheck="false"
          />
          <button type="submit" class="ai-search-bar__submit" hidden>Design</button>
        </div>
      </div>
    </form>`;

  const form = mountEl.querySelector('.ai-search-bar');
  const formInner = mountEl.querySelector('.ai-search-bar__form-inner');
  const track = mountEl.querySelector('.ai-search-bar__track');
  const input = mountEl.querySelector('.ai-search-bar__input');
  const submitBtn = mountEl.querySelector('.ai-search-bar__submit');
  const particlesWrap = mountEl.querySelector('.ai-search-bar__particles-wrap');
  const particlesHost = mountEl.querySelector('.ai-search-bar__particles');
  const clickLayer = mountEl.querySelector('.ai-search-bar__click-layer');
  const iconWrap = mountEl.querySelector('.ai-search-bar__icon-wrap');

  if (isUnsupportedBrowser()) {
    particlesWrap.style.filter = 'none';
  } else {
    particlesWrap.style.filter = 'url(#ai-gooey-effect)';
  }

  let blurTimer = null;

  function setFocused(focused) {
    form.classList.toggle('is-focused', focused);
    formInner.classList.toggle('is-focused', focused);
    track.classList.toggle('is-focused', focused);
    if (focused) {
      buildParticles(particlesHost);
      particlesWrap.hidden = false;
    } else {
      particlesWrap.hidden = true;
    }
  }

  function setDisabled(disabled) {
    form.classList.toggle('is-disabled', disabled);
    input.disabled = disabled;
    submitBtn.disabled = disabled;
  }

  function submit(value) {
    const trimmed = String(value || '').trim();
    if (!trimmed || getDisabled()) return;

    input.value = '';
    submitBtn.hidden = true;

    iconWrap.classList.add('is-animating');
    setTimeout(() => iconWrap.classList.remove('is-animating'), 700);

    onSearch?.(trimmed);
  }

  function syncDisabled() {
    setDisabled(getDisabled());
  }

  input.addEventListener('input', () => {
    submitBtn.hidden = !input.value.trim();
  });

  input.addEventListener('focus', () => {
    clearTimeout(blurTimer);
    setFocused(true);
  });

  input.addEventListener('blur', () => {
    blurTimer = setTimeout(() => setFocused(false), 180);
  });

  input.addEventListener('pointerdown', (e) => e.stopPropagation());

  track.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    const rect = track.getBoundingClientRect();
    spawnClickParticles(clickLayer, e.clientX - rect.left, e.clientY - rect.top);
    track.classList.add('is-clicked');
    setTimeout(() => track.classList.remove('is-clicked'), 700);
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    e.stopPropagation();
    submit(input.value);
  });

  submitBtn.addEventListener('pointerdown', (e) => e.stopPropagation());

  syncDisabled();

  return {
    focus() {
      input.focus();
    },
    clear() {
      input.value = '';
      submitBtn.hidden = true;
    },
    setPlaceholder(text) {
      input.placeholder = text;
    },
    refresh() {
      syncDisabled();
    },
    destroy() {
      clearTimeout(blurTimer);
      mountEl.innerHTML = '';
    },
  };
}

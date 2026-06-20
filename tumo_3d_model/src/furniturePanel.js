import { MODEL_CATALOG } from './factories.js';
import { renderModelThumbnail } from './furnitureThumbnails.js';
import {
  getOrderedRoomTemplates,
  getTemplateIcon,
  getTemplateSummary
} from './roomTemplates.js';

const FILTER_KEYS = {
  seating: new Set(['office_chair', 'simple_chair']),
  surfaces: new Set(['office_table', 'simple_table']),
  tech: new Set(['office_monitor', 'keyboard_mouse', 'speaker', 'microphone_stand', 'led_tv', 'whiteboard']),
  wall: new Set(['wall_flat_tv'])
};

let activeSection = 'templates';
let activeFilter = 'all';
let onSelectCallback = null;
let onFilterChangeCallback = null;
let onSectionChangeCallback = null;
let onTemplateSelectCallback = null;
let built = false;
let lastActiveModel = null;
let lastActiveTemplate = null;

export function getActiveFurnishFilter() {
  return activeFilter;
}

export function getActiveFurnishSection() {
  return activeSection;
}

export function setFurniturePanelFilterHandler(fn) {
  onFilterChangeCallback = fn;
}

export function setFurnitureSectionHandler(fn) {
  onSectionChangeCallback = fn;
}

export function setTemplateSelectHandler(fn) {
  onTemplateSelectCallback = fn;
}

export function setFurnishSection(section) {
  if (section !== 'ai' && section !== 'templates' && section !== 'customize') return;
  activeSection = section;
  updateSections();
  updateSectionViews();
  onSectionChangeCallback?.(activeSection);
}

function getFilteredCatalog() {
  const catalog = Object.entries(MODEL_CATALOG).map(([key, meta]) => ({ key, ...meta }));
  if (activeFilter === 'all') return catalog;
  const keys = FILTER_KEYS[activeFilter];
  return catalog.filter(item => keys?.has(item.key));
}

function updateSections() {
  document.querySelectorAll('.furnish-section').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.section === activeSection);
    btn.setAttribute('aria-selected', btn.dataset.section === activeSection ? 'true' : 'false');
  });
}

function updateSectionViews() {
  document.getElementById('furnish-section-ai')?.classList.toggle('hidden', activeSection !== 'ai');
  document.getElementById('furnish-section-templates')?.classList.toggle('hidden', activeSection !== 'templates');
  document.getElementById('furnish-section-customize')?.classList.toggle('hidden', activeSection !== 'customize');
  document.getElementById('furnish-filter-tabs')?.classList.toggle('hidden', activeSection !== 'customize');
  document.getElementById('furniture-panel')?.classList.toggle('furnish-mode-ai', activeSection === 'ai');
  document.body.classList.toggle('furnish-mode-build', activeSection === 'customize');
}

function updateTabs() {
  document.querySelectorAll('.furnish-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.filter === activeFilter);
    tab.setAttribute('aria-selected', tab.dataset.filter === activeFilter ? 'true' : 'false');
  });
}

function renderTemplateCards(grid) {
  grid.innerHTML = '';

  getOrderedRoomTemplates().forEach(template => {
    const isActive = lastActiveTemplate === template.id;
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'furnish-template-card';
    if (isActive) card.classList.add('active');
    card.dataset.template = template.id;
    card.setAttribute('aria-label', `${template.label} — ${template.tagline}`);
    card.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    card.style.setProperty('--template-accent', template.accent);

    card.innerHTML = `
      <div class="furnish-template-icon">${getTemplateIcon(template.icon)}</div>
      <div class="furnish-template-body">
        <span class="furnish-template-name">${template.label}</span>
        <span class="furnish-template-tagline">${template.tagline}</span>
        <span class="furnish-template-meta">
          <span class="furnish-template-count">${getTemplateSummary(template)}</span>
        </span>
      </div>
      ${isActive ? '<span class="furnish-template-check" aria-hidden="true">✓</span>' : ''}`;

    card.addEventListener('pointerdown', (e) => e.stopPropagation());
    card.addEventListener('click', (e) => {
      e.stopPropagation();
      lastActiveTemplate = template.id;
      document.querySelectorAll('.furnish-template-card').forEach(c => {
        const on = c.dataset.template === template.id;
        c.classList.toggle('active', on);
        c.setAttribute('aria-pressed', on ? 'true' : 'false');
        const existing = c.querySelector('.furnish-template-check');
        if (on && !existing) {
          const mark = document.createElement('span');
          mark.className = 'furnish-template-check';
          mark.setAttribute('aria-hidden', 'true');
          mark.textContent = '✓';
          c.appendChild(mark);
        } else if (!on) {
          existing?.remove();
        }
      });
      onTemplateSelectCallback?.(template.id);
    });

    grid.appendChild(card);
  });
}

function renderCards(grid) {
  if (activeFilter === 'remove') {
    grid.innerHTML = '';
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'furnish-card furnish-card--remove active';
    card.setAttribute('aria-label', 'Remove mode — click objects to delete');
    card.innerHTML = `
      <div class="furnish-card-preview furnish-card-preview--remove">
        <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
          <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="furnish-card-body">
        <span class="furnish-card-name">Remove</span>
      </div>`;
    card.addEventListener('pointerdown', (e) => e.stopPropagation());
    card.addEventListener('click', (e) => e.stopPropagation());
    grid.appendChild(card);
    return;
  }

  const items = getFilteredCatalog();
  grid.innerHTML = '';

  items.forEach(({ key, label, type }) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'furnish-card';
    card.dataset.model = key;
    card.title = label;
    card.setAttribute('aria-label', label);

    const preview = document.createElement('div');
    preview.className = 'furnish-card-preview';

    const skeleton = document.createElement('div');
    skeleton.className = 'furnish-thumb-skeleton';
    preview.appendChild(skeleton);

    const img = document.createElement('img');
    img.className = 'furnish-thumb';
    img.alt = label;
    img.decoding = 'async';
    img.loading = 'lazy';
    preview.appendChild(img);

    requestAnimationFrame(() => {
      try {
        img.src = renderModelThumbnail(key);
        img.onload = () => {
          skeleton.remove();
          img.classList.add('loaded');
        };
      } catch {
        skeleton.remove();
        preview.classList.add('furnish-card-preview--fallback');
      }
    });

    const body = document.createElement('div');
    body.className = 'furnish-card-body';

    const name = document.createElement('span');
    name.className = 'furnish-card-name';
    name.textContent = label;

    body.append(name);
    card.append(preview, body);

    card.addEventListener('pointerdown', (e) => e.stopPropagation());
    card.addEventListener('click', (e) => {
      e.stopPropagation();
      onSelectCallback?.(key);
    });

    grid.appendChild(card);
  });

  document.querySelectorAll('.furnish-card').forEach(card => {
    card.classList.toggle('active', card.dataset.model === lastActiveModel);
  });
}

export function collapseFurnishPanel() {
  const panel = document.getElementById('furniture-panel');
  const toggle = document.getElementById('furnish-toggle');
  panel?.classList.add('collapsed');
  toggle?.setAttribute('aria-expanded', 'false');
  toggle?.setAttribute('aria-label', 'Show furnish panel');
}

export function expandFurnishPanel() {
  const panel = document.getElementById('furniture-panel');
  const toggle = document.getElementById('furnish-toggle');
  panel?.classList.remove('collapsed');
  toggle?.setAttribute('aria-expanded', 'true');
  toggle?.setAttribute('aria-label', 'Hide furnish panel');
}

function bindStaticActions() {
  document.querySelectorAll('.furnish-section').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      setFurnishSection(btn.dataset.section || 'templates');
    });
  });

  document.querySelectorAll('.furnish-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.stopPropagation();
      activeFilter = tab.dataset.filter || 'all';
      updateTabs();
      onFilterChangeCallback?.(activeFilter);
      const grid = document.getElementById('furniture-grid');
      if (grid) renderCards(grid);
    });
  });

  const panel = document.getElementById('furniture-panel');
  const toggle = document.getElementById('furnish-toggle');
  toggle?.addEventListener('click', (e) => {
    e.stopPropagation();
    const collapsed = panel?.classList.toggle('collapsed');
    toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    toggle.setAttribute('aria-label', collapsed ? 'Show furnish panel' : 'Hide furnish panel');
  });
}

export function buildFurniturePanel(onSelect) {
  onSelectCallback = onSelect;
  if (built) return;
  built = true;

  const grid = document.getElementById('furniture-grid');
  const templateGrid = document.getElementById('template-grid');
  if (!grid || !templateGrid) return;

  updateSections();
  updateSectionViews();
  updateTabs();
  renderTemplateCards(templateGrid);
  renderCards(grid);
  bindStaticActions();

  const panel = document.getElementById('furniture-panel');
  panel?.addEventListener('pointerdown', (e) => e.stopPropagation());
}

export function setPanelActiveModel(modelKey) {
  lastActiveModel = modelKey;
  if (activeFilter === 'remove') return;

  document.querySelectorAll('.furnish-card').forEach(card => {
    card.classList.toggle('active', card.dataset.model === modelKey);
  });
}

export function setPlacedItemCount(count) {
  const el = document.getElementById('furnish-item-count');
  if (el) el.textContent = String(count);
}

export function refreshFurniturePanelFilter() {
  const grid = document.getElementById('furniture-grid');
  if (grid && built) renderCards(grid);
}

export function refreshTemplateCards() {
  const grid = document.getElementById('template-grid');
  if (grid && built) renderTemplateCards(grid);
}

export function setActiveTemplateId(templateId) {
  lastActiveTemplate = templateId;
  refreshTemplateCards();
}

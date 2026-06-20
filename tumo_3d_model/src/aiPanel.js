import { bridge } from './bridge.js';
import { mountAiSearchBar } from './aiSearchBar.js';
import { getVenueNameForRoom, isAiSupportedRoom } from './roomVenues.js';
import { indoorState } from './ui.js';

const STORAGE_PREFIX = 'tumo_furniture_';
const DESIGN_TIMEOUT_MS = 30000;

let built = false;
let loading = false;
let designTimeout = null;
let lastLayoutStyle = null;
let pendingDesignRoomId = null;
let searchBar = null;
const messages = [];

function getElements() {
  return {
    panelEl: document.querySelector('#furnish-section-ai .ai-panel'),
    roomLabel: document.getElementById('ai-room-label'),
    messagesEl: document.getElementById('ai-messages'),
    statusEl: document.getElementById('ai-status'),
    searchMount: document.getElementById('ai-search-mount'),
    hintEl: document.querySelector('.ai-search-hint'),
  };
}

function sanitizeLayoutItems(items) {
  if (!Array.isArray(items)) return [];
  return items.map((item) => {
    const clean = {
      modelKey: item.modelKey,
      x: Number(item.x) || 0,
      y: Number(item.y) || 0,
      z: Number(item.z) || 0,
      rotY: Number(item.rotY) || 0,
      type: item.type || 'floor',
    };
    if (clean.type === 'wall') {
      clean.wallAxis = item.wallAxis;
      clean.wallCoord = Number(item.wallCoord) || 0;
      clean.isPositiveWall = Boolean(item.isPositiveWall);
      clean.mountY = Number(item.mountY) || clean.y;
    }
    if (item.scale) clean.scale = item.scale;
    return clean;
  }).filter((item) => item.modelKey);
}

function getExistingLayoutItems(roomId) {
  const live = typeof window.__spaceflowGetLayoutItems === 'function'
    ? window.__spaceflowGetLayoutItems()
    : [];
  if (live.length) return sanitizeLayoutItems(live);

  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + roomId);
    return raw ? sanitizeLayoutItems(JSON.parse(raw)) : [];
  } catch {
    return [];
  }
}

function updateChatLayout() {
  const { panelEl } = getElements();
  const hasChat = messages.length > 0 || loading;
  panelEl?.classList.toggle('ai-panel--chatting', hasChat);
  document.getElementById('furniture-panel')?.classList.toggle('furnish-mode-ai-chat', hasChat);
}

function renderMessages() {
  const { messagesEl } = getElements();
  if (!messagesEl) return;

  updateChatLayout();

  if (!messages.length && !loading) {
    messagesEl.innerHTML = '';
    messagesEl.classList.add('is-empty');
    return;
  }

  messagesEl.classList.remove('is-empty');

  const html = messages.map((msg) => `
    <div class="ai-message ai-message--${msg.role}">
      <div class="ai-message-bubble">${escapeHtml(msg.text)}</div>
    </div>
  `).join('');

  messagesEl.innerHTML = loading
    ? `${html}<div class="ai-message ai-message--assistant"><div class="ai-message-bubble ai-message-bubble--typing"><span></span><span></span><span></span></div></div>`
    : html;

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function canSend() {
  const room = indoorState.activeRoomData;
  return Boolean(room && isAiSupportedRoom(room.roomId) && bridge.connected && !loading);
}

function clearDesignTimeout() {
  if (designTimeout) {
    clearTimeout(designTimeout);
    designTimeout = null;
  }
}

function finishDesign(options = {}) {
  const { message, isError = false } = options;
  pendingDesignRoomId = null;
  setLoading(false);
  if (message) {
    pushMessage('assistant', message);
  } else if (isError) {
    pushMessage('assistant', 'Could not update the layout. Please try again.');
  }
}

function setLoading(next) {
  loading = next;
  window._aiDesignInProgress = loading;
  const { statusEl } = getElements();
  if (statusEl) {
    statusEl.textContent = loading ? 'Designing layout…' : bridge.connected ? 'Ready' : 'Connecting to SpaceFlow…';
    statusEl.classList.toggle('ai-status--busy', loading);
  }
  if (loading) {
    clearDesignTimeout();
    designTimeout = setTimeout(() => {
      if (!loading) return;
      finishDesign({ isError: true, message: 'Layout design timed out. Please try again.' });
    }, DESIGN_TIMEOUT_MS);
  } else {
    clearDesignTimeout();
  }
  searchBar?.refresh();
  renderMessages();
}

export function refreshAiRoomContext() {
  const room = indoorState.activeRoomData;
  const { roomLabel } = getElements();
  if (!roomLabel) return;

  if (!room) {
    roomLabel.textContent = 'Enter a room to use AI';
  } else if (!isAiSupportedRoom(room.roomId)) {
    roomLabel.textContent = `${room.name} — AI layout not available here`;
  } else {
    const venue = getVenueNameForRoom(room.roomId);
    roomLabel.textContent = `${room.name} · ${venue}`;
    roomLabel.style.setProperty('--room-accent', room.color || '#3da9f5');
  }

  searchBar?.setPlaceholder(
    !room
      ? 'Enter a room to use AI'
      : !isAiSupportedRoom(room.roomId)
        ? 'AI layout not available in this room'
        : !bridge.connected
          ? 'Connecting to SpaceFlow backend…'
          : loading
            ? 'Designing layout…'
            : 'Design this room…',
  );
  searchBar?.refresh();
}

function pushMessage(role, text) {
  messages.push({ role, text });
  renderMessages();
}

function sendPrompt(rawPrompt) {
  const prompt = String(rawPrompt || '').trim();
  const room = indoorState.activeRoomData;
  if (!prompt || loading || !room || !isAiSupportedRoom(room.roomId)) return;

  if (!bridge.connected) {
    pushMessage('assistant', 'Not connected to SpaceFlow backend. Reconnecting…');
    return;
  }

  pushMessage('user', prompt);
  pendingDesignRoomId = room.roomId;
  setLoading(true);

  const existingItems = getExistingLayoutItems(room.roomId);

  try {
    bridge.send('AI_DESIGN', {
      roomId: room.roomId,
      prompt,
      venueName: getVenueNameForRoom(room.roomId),
      roomName: room.name,
      existingItems,
      previousLayoutStyle: lastLayoutStyle,
    });
  } catch (error) {
    console.warn('[AI Panel] Failed to send design request', error);
    finishDesign({ isError: true, message: 'Could not send the design request. Please try again.' });
  }
}

function bindBridgeEvents() {
  bridge.on('CONNECTED', () => {
    if (loading && !pendingDesignRoomId) {
      setLoading(false);
    }
    refreshAiRoomContext();
  });

  bridge.on('AI_DESIGN_STARTED', (payload) => {
    if (payload.roomId !== indoorState.activeRoomData?.roomId) return;
    pendingDesignRoomId = payload.roomId;
    setLoading(true);
  });

  bridge.on('APPLY_LAYOUT', (payload) => {
    if (payload.source !== 'ai_agent') return;
    if (payload.roomId !== pendingDesignRoomId) return;
    // Layout reached the scene — unlock the input even if DONE is delayed.
    if (loading) {
      clearDesignTimeout();
      loading = false;
      window._aiDesignInProgress = false;
      searchBar?.refresh();
      renderMessages();
    }
  });

  bridge.on('AI_DESIGN_DONE', (payload) => {
    if (payload.roomId !== indoorState.activeRoomData?.roomId) return;
    if (payload.layout_style) {
      lastLayoutStyle = payload.layout_style;
    }
    let text = payload.message || 'Custom layout applied to this room.';
    const models = payload.models_used;
    if (Array.isArray(models) && models.length && !text.includes('Models used:') && !payload.modified) {
      text += ` Models: ${models.join(', ')}.`;
    }
    finishDesign({ message: text });
  });

  bridge.on('AI_DESIGN_ERROR', (payload) => {
    if (payload.roomId && payload.roomId !== indoorState.activeRoomData?.roomId) return;
    finishDesign({ message: payload.message || 'Could not generate a layout.' });
  });
}

export function initAiPanel() {
  if (built) {
    refreshAiRoomContext();
    return;
  }
  built = true;

  const { searchMount } = getElements();
  searchBar = mountAiSearchBar(searchMount, {
    placeholder: 'Design this room…',
    onSearch: sendPrompt,
    getDisabled: () => !canSend(),
  });

  bindBridgeEvents();
  renderMessages();
  refreshAiRoomContext();
  setLoading(false);
}

export function resetAiConversation() {
  messages.length = 0;
  lastLayoutStyle = null;
  pendingDesignRoomId = null;
  searchBar?.clear();
  renderMessages();
  refreshAiRoomContext();
}

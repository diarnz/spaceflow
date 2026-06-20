import * as THREE from 'three';
import { scene, camera, controls, renderer, setCameraFov, INDOOR_FOV, OUTDOOR_FOV } from './sceneSetup.js';
import { boxData } from './factories.js';
import { setFloorVisibilityFade } from './world.js';
import { enterFurnishingMode, exitFurnishingMode, handleFurnishingClick } from './furnishing.js';
import { showConfirm } from './confirmDialog.js';

export const navState = {
  isNavigating: false,
  lerpSpeed: 0.022,
  targetCamPos: new THREE.Vector3(),
  targetLook: new THREE.Vector3(),
  onComplete: null
};

export const indoorState = {
  isIndoorMode: false,
  yaw: 0,
  pitch: 0,
  currentYaw: 0,
  currentPitch: 0,
  eyeY: null,
  activeRoomData: null,
  activeRoomGroup: null
};

/** Standing eye height from the room floor (meters). */
export function getRoomEyeY(room) {
  const floorY = room.y - room.h / 2 + 0.2;
  const eyeFromFloor = Math.min(1.62, room.h * 0.54 - 0.12);
  return floorY + Math.max(0.82, eyeFromFloor);
}

// State tracker for WASD / Arrow keyboard movements
export const keys = {
  w: false,
  a: false,
  s: false,
  d: false
};

const MOVEMENT_CODES = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']);

function setMovementKey(code, down) {
  switch (code) {
    case 'KeyW': case 'ArrowUp': keys.w = down; break;
    case 'KeyS': case 'ArrowDown': keys.s = down; break;
    case 'KeyA': case 'ArrowLeft': keys.a = down; break;
    case 'KeyD': case 'ArrowRight': keys.d = down; break;
  }
}

function isTypingTarget(target) {
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

// Capture phase so movement keys work even when a button has focus
window.addEventListener('keydown', (e) => {
  if (!MOVEMENT_CODES.has(e.code)) return;
  if (isTypingTarget(e.target)) return;
  setMovementKey(e.code, true);
  if (indoorState.isIndoorMode) e.preventDefault();
}, true);

window.addEventListener('keyup', (e) => {
  if (!MOVEMENT_CODES.has(e.code)) return;
  setMovementKey(e.code, false);
}, true);

function setOutdoorNavVisible(visible) {
  document.getElementById('controls-hint')?.classList.toggle('hidden', !visible);
  document.getElementById('nav-hint')?.classList.toggle('hidden', !visible);
}

function getFloorLabel(y) {
  if (y < -3.5) return 'Floor 0';
  if (y < 3.5) return 'Floor 1';
  return 'Floor 3';
}

function setActiveFloorButton(floorKey) {
  const map = { floor0: '0', floor1: '1', floor3: '3' };
  const active = floorKey ? map[floorKey] : null;
  document.querySelectorAll('.floor-btn[data-floor]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.floor === active);
  });
  document.getElementById('btn-reset')?.classList.toggle('active', floorKey === null);
}

function positionRoomTooltip(label, clientX, clientY) {
  const pad = 14;
  const offset = 18;
  const w = label.offsetWidth || 280;
  const h = label.offsetHeight || 150;

  let left = clientX + offset;
  let top = clientY + offset;

  if (left + w > window.innerWidth - pad) left = clientX - w - offset;
  if (top + h > window.innerHeight - pad) top = clientY - h - offset;

  left = Math.max(pad, Math.min(left, window.innerWidth - w - pad));
  top = Math.max(pad, Math.min(top, window.innerHeight - h - pad));

  label.style.left = `${left}px`;
  label.style.top = `${top}px`;
}

export function initUI() {
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  const label = document.getElementById('room-label');
  const labelAccent = document.getElementById('label-accent');
  const labelFloor = document.getElementById('label-floor');
  const labelSize = document.getElementById('label-size');
  const labelName = document.getElementById('label-name');
  const labelDesc = document.getElementById('label-desc');

  let hoveredMat = null;
  let hoveredRoomId = null;
  let pointerX = 0;
  let pointerY = 0;
  let isCameraDragging = false;

  function hideRoomHover() {
    hoveredRoomId = null;
    label.classList.remove('visible');
    label.setAttribute('aria-hidden', 'true');
    if (hoveredMat) {
      hoveredMat.emissiveIntensity = 0;
      hoveredMat = null;
    }
  }

  // Track pointerdown position to distinguish between click and drag
  let startX = 0, startY = 0;
  
  renderer.domElement.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    startX = e.clientX;
    startY = e.clientY;
    hideRoomHover();
  });

  renderer.domElement.addEventListener('pointerup', (e) => {
    // If the mouse moved more than 10px, assume it's a camera drag/orbit, not a click
    const deltaX = Math.abs(e.clientX - startX);
    const deltaY = Math.abs(e.clientY - startY);
    if (deltaX > 10 || deltaY > 10) return;

    // Do not raycast click if already inside a room
    if (indoorState.isIndoorMode) return;

    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(boxData);

    if (hits.length > 0 && hits[0].object.userData.name) {
      enterRoom(hits[0].object);
    }
  });

  renderer.domElement.addEventListener('mousemove', (e) => {
    pointerX = e.clientX;
    pointerY = e.clientY;

    if (indoorState.isIndoorMode) {
      hideRoomHover();
      return;
    }

    if (isCameraDragging || e.buttons > 0) {
      hideRoomHover();
      return;
    }

    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const hits = raycaster.intersectObjects(boxData);

    if (hits.length > 0 && hits[0].object.userData.name) {
      const d = hits[0].object.userData;

      if (d.roomId !== hoveredRoomId) {
        hoveredRoomId = d.roomId;
        label.style.setProperty('--room-accent', d.color);
        if (labelAccent) labelAccent.style.background = d.color;
        labelName.textContent = d.name;
        labelDesc.textContent = d.desc;
        if (labelFloor) labelFloor.textContent = getFloorLabel(d.y);
        if (labelSize) labelSize.textContent = `${d.w.toFixed(1)} × ${d.d.toFixed(1)} m`;
      }

      positionRoomTooltip(label, pointerX, pointerY);
      label.classList.add('visible');
      label.setAttribute('aria-hidden', 'false');

      if (hoveredMat !== d.glowMat) {
        if (hoveredMat) hoveredMat.emissiveIntensity = 0;
        hoveredMat = d.glowMat;
        hoveredMat.emissive.set(d.color);
        hoveredMat.emissiveIntensity = 0.35;
      }
    } else {
      hideRoomHover();
    }
  });

  function jumpTo(x, y, z, lookY) {
    navState.targetLook.set(0, lookY, 0);
    navState.targetCamPos.set(x, y, z);
    navState.isNavigating = true;
  }

  function goToFloor(x, y, z, lookY, floorKey) {
    // If transitioning from indoor mode back to floor view, clean up indoor state
    if (indoorState.isIndoorMode) {
      exitFurnishingMode();
      indoorState.isIndoorMode = false;
      controls.enabled = true;
      
      // Defrost the windows of the room we just exited
      if (indoorState.activeRoomGroup) {
        indoorState.activeRoomGroup.traverse(child => {
          if (child.isMesh && child.material && child.material.transparent && child.material.roughness !== undefined) {
            child.material.roughness = 0.05;
            child.material.opacity = 0.25;
            child.material.needsUpdate = true;
          }
        });
      }

      // Reset keyboard states
      for (let k in keys) keys[k] = false;

      isDraggingIndoor = false;
      dragPointerId = null;

      // Clear references
      indoorState.activeRoomData = null;
      indoorState.activeRoomGroup = null;
      indoorState.eyeY = null;
      setCameraFov(OUTDOOR_FOV);

      setOutdoorNavVisible(true);
    }

    setActiveFloorButton(floorKey);
    setFloorVisibilityFade(floorKey);
    jumpTo(x, y, z, lookY);
  }

  document.getElementById('btn-f0').addEventListener('click', () => goToFloor(0,   -4.6, 13.6, -5,   'floor0'));
  document.getElementById('btn-f1').addEventListener('click', () => goToFloor(0.2, -1.5, 10,   -1.7, 'floor1'));
  document.getElementById('btn-f3').addEventListener('click', () => goToFloor(0.2,  2.8, 10,    3.8, 'floor3'));
  document.getElementById('btn-reset').addEventListener('click', () => goToFloor(0, 0.5, 20.5, -1.5, null));
  document.getElementById('btn-exit')?.addEventListener('click', async (e) => {
    e.stopPropagation();
    const ok = await showConfirm({
      title: 'Are you sure you want to exit?',
      message: 'You will leave this room and return to campus view.',
      confirmLabel: 'Exit room',
      cancelLabel: 'Stay',
      variant: 'exit'
    });
    if (ok) exitIndoorMode();
  });

  controls.addEventListener('start', () => {
    navState.isNavigating = false;
    isCameraDragging = true;
    hideRoomHover();
  });
  controls.addEventListener('end', () => {
    isCameraDragging = false;
  });
}

// ─── First-Person Look Drag Input Listeners ─────────────────────────────────
let isDraggingIndoor = false;
let dragPointerId = null;
const dragSensitivity = 0.003;

function isIndoorUiTarget(target) {
  return target.tagName === 'BUTTON' ||
    target.closest('#ui') ||
    target.closest('#controls-hint') ||
    target.closest('#nav-hint') ||
    target.closest('#furniture-panel') ||
    target.closest('#room-label');
}

const canvas = renderer.domElement;
canvas.tabIndex = 0;
canvas.style.outline = 'none';

canvas.addEventListener('pointerdown', (e) => {
  if (!indoorState.isIndoorMode || navState.isNavigating) return;
  if (isIndoorUiTarget(e.target)) return;
  canvas._indoorStartX = e.clientX;
  canvas._indoorStartY = e.clientY;
  isDraggingIndoor = true;
  dragPointerId = e.pointerId;
  canvas.setPointerCapture(e.pointerId);
});

canvas.addEventListener('pointermove', (e) => {
  if (!indoorState.isIndoorMode || !isDraggingIndoor || e.pointerId !== dragPointerId) return;
  indoorState.yaw -= e.movementX * dragSensitivity;
  indoorState.pitch = Math.max(-Math.PI / 2.3, Math.min(Math.PI / 2.3, indoorState.pitch - e.movementY * dragSensitivity));
});

canvas.addEventListener('pointerup', (e) => {
  if (dragPointerId === null || e.pointerId !== dragPointerId) return;

  const deltaX = Math.abs(e.clientX - (canvas._indoorStartX ?? e.clientX));
  const deltaY = Math.abs(e.clientY - (canvas._indoorStartY ?? e.clientY));

  if (indoorState.isIndoorMode && deltaX <= 10 && deltaY <= 10) {
    handleFurnishingClick();
  }

  if (canvas.hasPointerCapture(e.pointerId)) {
    canvas.releasePointerCapture(e.pointerId);
  }
  isDraggingIndoor = false;
  dragPointerId = null;
});

canvas.addEventListener('pointercancel', (e) => {
  if (dragPointerId === null || e.pointerId !== dragPointerId) return;
  if (canvas.hasPointerCapture(e.pointerId)) {
    canvas.releasePointerCapture(e.pointerId);
  }
  isDraggingIndoor = false;
  dragPointerId = null;
});

// ─── Enter Room ─────────────────────────────────────────────────────────────
export function enterRoom(hitObject) {
  const d = hitObject.userData;
  const roomGroup = hitObject.parent;

  // Store room data references
  window._currentRoomId = d.roomId;
  indoorState.activeRoomData = d;
  indoorState.activeRoomGroup = roomGroup;

  const eyeY = getRoomEyeY(d);
  indoorState.eyeY = eyeY;
  setCameraFov(INDOOR_FOV);

  // First-person position at standing height, slightly inside the room
  const enterDist = Math.min(1.2, d.d * 0.22);
  navState.targetCamPos.set(
    d.x - Math.sin(d.ry) * enterDist,
    eyeY,
    d.z - Math.cos(d.ry) * enterDist
  );

  const forwardX = d.x - Math.sin(d.ry) * (enterDist + 2.5);
  const forwardZ = d.z - Math.cos(d.ry) * (enterDist + 2.5);
  navState.targetLook.set(forwardX, eyeY, forwardZ);

  navState.lerpSpeed = 0.18;
  navState.isNavigating = true;
  controls.enabled = false;
  indoorState.isIndoorMode = true;

  if (document.activeElement instanceof HTMLElement && document.activeElement !== canvas) {
    document.activeElement.blur();
  }
  canvas.focus({ preventScroll: true });

  navState.onComplete = () => {
    indoorState.pitch = -0.06;
    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
    indoorState.yaw = Math.atan2(forward.x, forward.z);
    indoorState.currentYaw = indoorState.yaw;
    indoorState.currentPitch = indoorState.pitch;
  };

  enterFurnishingMode(roomGroup, d);
  window.spaceFlowBridge?.send('ROOM_ENTERED', { roomId: d.roomId, roomName: d.name });
  window.spaceFlowBridge?.send('REQUEST_LAYOUT', { roomId: d.roomId });
  window.spaceFlowBridge?.applyPendingLayout?.(d.roomId);

  // Apply frosted glass blur to room windows
  roomGroup.traverse(child => {
    if (child.isMesh && child.material && child.material.transparent && child.material.roughness !== undefined) {
      child.material.roughness = 0.88; // frosted glass roughness
      child.material.opacity = 0.55;   // slightly more opaque for blurred light look
      child.material.needsUpdate = true;
    }
  });

  // Update UI Elements
  setOutdoorNavVisible(false);
}

export function enterRoomById(roomId) {
  if (!roomId) return false;

  const target = scene.getObjectByProperty('userData.roomId', roomId);
  if (!target) return false;

  enterRoom(target);
  return true;
}

// ─── Exit Room ──────────────────────────────────────────────────────────────
export function exitIndoorMode() {
  if (!indoorState.isIndoorMode) return;
  if (window._currentRoomId) {
    window.spaceFlowBridge?.send('ROOM_EXITED', { roomId: window._currentRoomId });
  }
  window._currentRoomId = null;
  document.getElementById('btn-reset').click();
}

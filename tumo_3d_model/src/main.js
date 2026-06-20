import * as THREE from 'three';
import { scene, camera, renderer, controls, setupLighting } from './sceneSetup.js';
import { buildWorld } from './world.js';
import { initUI, navState, indoorState, keys, enterRoomById } from './ui.js';
import { preloadModels, boxData } from './factories.js';
import { initFurnishing, updateFurnishingPreview, hydrateAllRoomLayouts } from './furnishing.js';
import { isFloorPlanEditorOpen } from './floorPlanEditor.js';
import { bridge } from './bridge.js';

window.boxData = boxData;
bridge.connect();

const domeLight = setupLighting();

const loaderOverlay = document.getElementById('loading-overlay');
const loaderStatus = document.getElementById('loader-status');
const loaderProgressFill = document.getElementById('loader-progress-fill');
const loaderPercent = document.getElementById('loader-percent');

const loadingStatusMessages = {
  office_table: 'Furnishing labs with creative tables...',
  office_chair: 'Placing designer ergonomic chairs...',
  office_monitor: 'Setting up high-end workstation displays...',
  keyboard_mouse: 'Connecting input accessories...',
  simple_table: 'Assembling coding stations...',
  simple_chair: 'Setting up study seating...',
  speaker: 'Mounting professional acoustics...',
  microphone_stand: 'Calibrating sound studio recording gear...',
  wall_flat_tv: 'Mounting presentation displays...',
  led_tv: 'Calibrating media lounge TVs...',
  whiteboard: 'Loading ideation whiteboards...'
};

preloadModels(
  (percent, lastLoadedKey) => {
    if (loaderProgressFill) loaderProgressFill.style.width = `${percent}%`;
    if (loaderPercent) loaderPercent.textContent = `${percent}%`;
    if (loaderStatus) {
      const message = loadingStatusMessages[lastLoadedKey] || 'Equipping creative centers…';
      loaderStatus.textContent = message;
    }
  },
  () => {
    if (loaderOverlay) {
      loaderOverlay.classList.add('fade-out');
      setTimeout(() => {
        loaderOverlay.remove();
        document.body.classList.add('app-ready');
      }, 850);
    } else {
      document.body.classList.add('app-ready');
    }
    buildWorld();
    initFurnishing(renderer, camera);
    hydrateAllRoomLayouts();
    initUI();
    const initialRoomId = new URLSearchParams(window.location.search).get('autoRoom');
    if (initialRoomId) {
      requestAnimationFrame(() => {
        enterRoomById(initialRoomId);
      });
    }
  }
);

window.addEventListener('message', (event) => {
  if (event.origin !== 'http://localhost:5173') return;
  const { type, payload = {} } = event.data || {};
  if (type === 'NAVIGATE_TO_ROOM' && payload.roomId) {
    enterRoomById(payload.roomId);
  }
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  if (isFloorPlanEditorOpen()) return;

  const delta = clock.getDelta();
  const t = clock.getElapsedTime();

  if (navState.isNavigating) {
    camera.position.lerp(navState.targetCamPos, navState.lerpSpeed);
    if (controls.enabled) {
      controls.target.lerp(navState.targetLook, navState.lerpSpeed);
    } else {
      const currentLook = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion).add(camera.position);
      currentLook.lerp(navState.targetLook, navState.lerpSpeed);
      camera.lookAt(currentLook);
    }
    if (camera.position.distanceTo(navState.targetCamPos) < 0.35) {
      camera.position.copy(navState.targetCamPos);
      if (indoorState.eyeY != null) {
        camera.position.y = indoorState.eyeY;
      }
      navState.isNavigating = false;
      if (navState.onComplete) {
        navState.onComplete();
        navState.onComplete = null;
      }
    }
  }

  // Handle first-person camera look-around and movement inside rooms
  if (indoorState.isIndoorMode && !navState.isNavigating) {
    const targetDir = new THREE.Vector3(
      Math.sin(indoorState.yaw) * Math.cos(indoorState.pitch),
      Math.sin(indoorState.pitch),
      Math.cos(indoorState.yaw) * Math.cos(indoorState.pitch)
    );
    camera.lookAt(camera.position.clone().add(targetDir));

    const moveSpeed = 2.8 * delta;
    const moveVec = new THREE.Vector3();

    const forwardVec = new THREE.Vector3(Math.sin(indoorState.yaw), 0, Math.cos(indoorState.yaw));
    const rightVec = new THREE.Vector3(Math.cos(indoorState.yaw), 0, -Math.sin(indoorState.yaw));

    if (keys.w) moveVec.add(forwardVec);
    if (keys.s) moveVec.sub(forwardVec);
    if (keys.a) moveVec.add(rightVec);
    if (keys.d) moveVec.sub(rightVec);

    if (moveVec.lengthSq() > 0) {
      moveVec.normalize().multiplyScalar(moveSpeed);
      camera.position.add(moveVec);

      if (indoorState.eyeY != null) {
        camera.position.y = indoorState.eyeY;
      }

      if (indoorState.activeRoomData) {
        const d = indoorState.activeRoomData;
        const roomCenter = new THREE.Vector3(d.x, d.y, d.z);

        const localPos = camera.position.clone().sub(roomCenter);
        localPos.applyAxisAngle(new THREE.Vector3(0, 1, 0), -d.ry);

        const padX = Math.min(0.45, d.w * 0.2);
        const padZ = Math.min(0.45, d.d * 0.2);
        localPos.x = Math.max(-d.w / 2 + padX, Math.min(d.w / 2 - padX, localPos.x));
        localPos.z = Math.max(-d.d / 2 + padZ, Math.min(d.d / 2 - padZ, localPos.z));

        localPos.applyAxisAngle(new THREE.Vector3(0, 1, 0), d.ry).add(roomCenter);
        camera.position.copy(localPos);
      }
    }

    updateFurnishingPreview();
  }

  // subtle dome light pulse
  domeLight.intensity = 2.4 + Math.sin(t * 0.5) * 0.2;

  const tumoPulse = 0.82 + Math.sin(t * 2.2) * 0.18;
  scene.traverse(obj => {
    const meshes = obj.userData?.tumoGlowMeshes;
    const base = obj.userData?.tumoGlowBase;
    if (!meshes?.length || !base?.length) return;
    meshes.forEach((mesh, i) => {
      if (mesh.material?.opacity != null && base[i] != null) {
        mesh.material.opacity = base[i] * tumoPulse;
      }
    });
  });

  if (controls.enabled) {
    controls.update();
  }
  
  renderer.render(scene, camera);
}
animate();

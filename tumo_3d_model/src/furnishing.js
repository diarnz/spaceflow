import * as THREE from 'three';
import {
  createDecorMesh,
  getDefaultScale,
  applyModelRotY,
  getModelRotYOffset,
  MODEL_CATALOG,
  boxData
} from './factories.js';
import { showFloorPlanModal } from './floorPlan2d.js';
import { showConfirm } from './confirmDialog.js';
import {
  buildFurniturePanel,
  collapseFurnishPanel,
  expandFurnishPanel,
  getActiveFurnishFilter,
  getActiveFurnishSection,
  setActiveTemplateId,
  setFurniturePanelFilterHandler,
  setFurnitureSectionHandler,
  setFurnishSection,
  setPanelActiveModel,
  setPlacedItemCount,
  setTemplateSelectHandler
} from './furniturePanel.js';
import { getRoomTemplate, getHackathonPodCenters, getMediaStudioLayout, getClassroomLayout } from './roomTemplates.js';
import { initAiPanel, refreshAiRoomContext } from './aiPanel.js';

const STORAGE_PREFIX = 'tumo_furniture_';
const HIGHLIGHT_COLOR = new THREE.Color(0x44aaff);
const GHOST_OPACITY = 0.45;
const SURFACE_STACK_OFFSET = 0.004;
const WALL_INSET = 0.06;
const ROOM_FLOOR_INSET = 0.22;
const PLACEMENT_OVERLAP_GAP = 0.06;
const WALL_MOUNT_MIN_Y = 0.45;
const WALL_MOUNT_MAX_RATIO = 0.82;

const SURFACE_MODELS = new Set(['office_table', 'simple_table']);
const STACKABLE_MODELS = new Set([
  'office_monitor',
  'keyboard_mouse',
  'speaker'
]);

const _box = new THREE.Box3();
const _worldPoint = new THREE.Vector3();
const _localPoint = new THREE.Vector3();

let renderer = null;
let camera = null;
let raycaster = null;

let active = false;
let roomGroup = null;
let roomData = null;
let furnitureGroup = null;

let selectedModelKey = null;
let ghostMesh = null;
let ghostRotY = 0;
let selectedItem = null;
let highlightBackup = [];
let removeModeActive = false;
let templatesModeActive = true;

const _invMatrix = new THREE.Matrix4();
const _rayOrigin = new THREE.Vector3();
const _rayDir = new THREE.Vector3();

export function getModelCatalog() {
  return Object.entries(MODEL_CATALOG).map(([key, meta]) => ({ key, ...meta }));
}

function storageKey(roomId) {
  return STORAGE_PREFIX + roomId;
}

function loadLayout(roomId) {
  try {
    const raw = localStorage.getItem(storageKey(roomId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveLayout(roomId, items) {
  localStorage.setItem(storageKey(roomId), JSON.stringify(items));
}

function serializeLayout() {
  if (!furnitureGroup || !roomData) return [];
  const items = [];
  furnitureGroup.children.forEach(child => {
    if (!child.userData.modelKey) return;
    const item = {
      modelKey: child.userData.modelKey,
      x: child.position.x,
      y: child.position.y,
      z: child.position.z,
      rotY: child.rotation.y - getModelRotYOffset(child.userData.modelKey),
      type: child.userData.placementType || 'floor'
    };
    if (item.type !== 'wall') {
      const bottomY = getMeshBottomYInGroup(child);
      item.surfaceY = child.position.y + bottomY;
    } else {
      item.wallAxis = child.userData.wallAxis;
      item.wallCoord = child.userData.wallCoord;
      item.isPositiveWall = child.userData.isPositiveWall;
      item.mountY = child.userData.mountY;
    }
    if (child.userData.scaleOverride) {
      item.scale = child.userData.scaleOverride;
    }
    items.push(item);
  });
  return items;
}

function persistLayout(options = {}) {
  if (!roomData?.roomId) return;
  const items = serializeLayout();
  saveLayout(roomData.roomId, items);
  if (!options.skipBridge) {
    window.spaceFlowBridge?.send('LAYOUT_SAVED', { roomId: roomData.roomId, items });
  }
}

function applyGhostOpacity(mesh, opacity) {
  mesh.traverse(child => {
    if (!child.isMesh || !child.material) return;
    const mats = Array.isArray(child.material) ? child.material : [child.material];
    mats.forEach(mat => {
      if (!mat.userData._ghostOrig) {
        mat.userData._ghostOrig = {
          transparent: mat.transparent,
          opacity: mat.opacity,
          depthWrite: mat.depthWrite
        };
      }
      mat.transparent = true;
      mat.opacity = opacity;
      mat.depthWrite = false;
      mat.needsUpdate = true;
    });
  });
}

function restoreGhostMaterials(mesh) {
  mesh.traverse(child => {
    if (!child.isMesh || !child.material) return;
    const mats = Array.isArray(child.material) ? child.material : [child.material];
    mats.forEach(mat => {
      if (mat.userData._ghostOrig) {
        mat.transparent = mat.userData._ghostOrig.transparent;
        mat.opacity = mat.userData._ghostOrig.opacity;
        mat.depthWrite = mat.userData._ghostOrig.depthWrite;
        delete mat.userData._ghostOrig;
        mat.needsUpdate = true;
      }
    });
  });
}

function disposeGhost() {
  if (!ghostMesh) return;
  restoreGhostMaterials(ghostMesh);
  ghostMesh.parent?.remove(ghostMesh);
  disposePlacedObject(ghostMesh);
  ghostMesh = null;
}

function updateGhost() {
  if (!selectedModelKey || !furnitureGroup || !roomData) {
    disposeGhost();
    return;
  }

  const meta = MODEL_CATALOG[selectedModelKey];
  if (!meta) return;

  const hit = getPlacementHit(selectedModelKey);
  if (!hit) {
    if (ghostMesh) ghostMesh.visible = false;
    return;
  }

  if (!ghostMesh || ghostMesh.userData.modelKey !== selectedModelKey) {
    disposeGhost();
    ghostMesh = createDecorMesh(selectedModelKey, getDefaultScale(selectedModelKey), 0, ghostRotY, 0);
    ghostMesh.userData.modelKey = selectedModelKey;
    applyGhostOpacity(ghostMesh, GHOST_OPACITY);
    furnitureGroup.add(ghostMesh);
  }

  ghostMesh.visible = true;
  applyPlacementPosition(ghostMesh, hit, meta.type);
}

function getRoomLocalLookRay() {
  roomGroup.updateMatrixWorld(true);
  _invMatrix.copy(roomGroup.matrixWorld).invert();

  _rayOrigin.copy(camera.position).applyMatrix4(_invMatrix);
  camera.getWorldDirection(_rayDir);
  _rayDir.transformDirection(_invMatrix).normalize();

  return { origin: _rayOrigin, dir: _rayDir };
}

function getFloorLevelY() {
  return roomGroup.userData.floorY ?? (-roomData.h / 2 + 0.2);
}

function toFurnitureY(roomLocalY) {
  return roomLocalY - getFloorLevelY();
}

function intersectPlane(origin, dir, planeNormal, planeConstant) {
  const denom = planeNormal.dot(dir);
  if (Math.abs(denom) < 1e-6) return null;
  const t = -(origin.dot(planeNormal) + planeConstant) / denom;
  if (t < 0) return null;
  return origin.clone().add(dir.clone().multiplyScalar(t));
}

function getRoomFloorHalfExtents() {
  if (!roomData) return { halfX: 1, halfZ: 1 };
  return {
    halfX: roomData.w / 2 - ROOM_FLOOR_INSET,
    halfZ: roomData.d / 2 - ROOM_FLOOR_INSET
  };
}

function boundsInsideRoom(bounds, margin = 0) {
  const { halfX, halfZ } = getRoomFloorHalfExtents();
  return (
    bounds.minX >= -halfX + margin &&
    bounds.maxX <= halfX - margin &&
    bounds.minZ >= -halfZ + margin &&
    bounds.maxZ <= halfZ - margin
  );
}

function boundsOverlap2D(a, b, gap = PLACEMENT_OVERLAP_GAP) {
  return !(
    a.maxX + gap < b.minX ||
    a.minX - gap > b.maxX ||
    a.maxZ + gap < b.minZ ||
    a.minZ - gap > b.maxZ
  );
}

function getFloorOverlapTargets(excludeMesh) {
  const targets = [];
  if (!furnitureGroup) return targets;
  furnitureGroup.children.forEach(child => {
    if (child === excludeMesh || !child.userData?.isPlacedFurniture) return;
    if (child.userData.placementType === 'wall') return;
    if (STACKABLE_MODELS.has(child.userData.modelKey)) return;
    targets.push(child);
  });
  return targets;
}

function meshHasFloorOverlap(mesh, gap = PLACEMENT_OVERLAP_GAP) {
  const bounds = getItemBoundsXZ(mesh);
  return getFloorOverlapTargets(mesh).some(other =>
    boundsOverlap2D(bounds, getItemBoundsXZ(other), gap)
  );
}

function isFloorPlacementValid(mesh) {
  return boundsInsideRoom(getItemBoundsXZ(mesh)) && !meshHasFloorOverlap(mesh);
}

function clampMeshXZToRoom(mesh) {
  if (!furnitureGroup || !roomData) return;
  const { halfX, halfZ } = getRoomFloorHalfExtents();

  for (let pass = 0; pass < 6; pass++) {
    const bounds = getItemBoundsXZ(mesh);
    let dx = 0;
    let dz = 0;
    if (bounds.minX < -halfX) dx = -halfX - bounds.minX;
    else if (bounds.maxX > halfX) dx = halfX - bounds.maxX;
    if (bounds.minZ < -halfZ) dz = -halfZ - bounds.minZ;
    else if (bounds.maxZ > halfZ) dz = halfZ - bounds.maxZ;
    if (dx === 0 && dz === 0) break;
    mesh.position.x += dx;
    mesh.position.z += dz;
  }
}

function clampWallItemAlongWall(mesh) {
  if (!roomData || mesh.userData.placementType !== 'wall') return;
  const { halfX, halfZ } = getRoomFloorHalfExtents();
  const bounds = getItemBoundsXZ(mesh);
  if (mesh.userData.wallAxis === 'z') {
    let dx = 0;
    if (bounds.minX < -halfX) dx = -halfX - bounds.minX;
    else if (bounds.maxX > halfX) dx = halfX - bounds.maxX;
    mesh.position.x += dx;
  } else {
    let dz = 0;
    if (bounds.minZ < -halfZ) dz = -halfZ - bounds.minZ;
    else if (bounds.maxZ > halfZ) dz = halfZ - bounds.maxZ;
    mesh.position.z += dz;
  }
}

function findFreeFloorPosition(mesh, prefX, prefZ, rotY, surfaceY = 0) {
  const { halfX, halfZ } = getRoomFloorHalfExtents();
  const step = 0.24;
  const maxR = Math.min(halfX, halfZ);
  const candidates = [{ x: prefX, z: prefZ, dist: 0 }];

  for (let ring = 1; ring <= Math.ceil(maxR / step); ring++) {
    const r = ring * step;
    const segments = Math.max(10, ring * 8);
    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      const x = prefX + Math.cos(angle) * r;
      const z = prefZ + Math.sin(angle) * r;
      if (Math.abs(x) > halfX || Math.abs(z) > halfZ) continue;
      candidates.push({ x, z, dist: r });
    }
  }

  candidates.sort((a, b) => a.dist - b.dist);
  for (const candidate of candidates) {
    setPlacedPosition(mesh, candidate.x, candidate.z, rotY, surfaceY);
    clampMeshXZToRoom(mesh);
    if (isFloorPlacementValid(mesh)) {
      return { x: mesh.position.x, z: mesh.position.z };
    }
  }

  setPlacedPosition(mesh, 0, 0, rotY, surfaceY);
  clampMeshXZToRoom(mesh);
  return { x: mesh.position.x, z: mesh.position.z };
}

function resolveFloorPlacement(mesh, x, z, rotY, surfaceY = 0, { relocate = false } = {}) {
  setPlacedPosition(mesh, x, z, rotY, surfaceY);
  clampMeshXZToRoom(mesh);
  if (!relocate || isFloorPlacementValid(mesh)) return;
  findFreeFloorPosition(mesh, x, z, rotY, surfaceY);
}

function clampToFloorBounds(x, z) {
  const { halfX, halfZ } = getRoomFloorHalfExtents();
  return {
    x: Math.max(-halfX, Math.min(halfX, x)),
    z: Math.max(-halfZ, Math.min(halfZ, z))
  };
}

function findPlacedItemByTemplateIndex(index) {
  return furnitureGroup?.children.find(child => child.userData.templateIndex === index) ?? null;
}

function getPlacedMeshes(excludeGhost = true) {
  const meshes = [];
  if (!furnitureGroup) return meshes;
  furnitureGroup.traverse(child => {
    if (!child.userData?.isPlacedFurniture) return;
    if (excludeGhost && child === ghostMesh) return;
    child.traverse(node => {
      if (node.isMesh) meshes.push(node);
    });
  });
  return meshes;
}

function getPlacedItemTopY(item) {
  item.updateWorldMatrix(true, false);
  _box.setFromObject(item);
  _worldPoint.set(
    (_box.min.x + _box.max.x) * 0.5,
    _box.max.y,
    (_box.min.z + _box.max.z) * 0.5
  );
  furnitureGroup.worldToLocal(_worldPoint);
  return _worldPoint.y + SURFACE_STACK_OFFSET;
}

function clampToSurfaceBounds(item, x, z) {
  item.updateWorldMatrix(true, false);
  _box.setFromObject(item);
  const corners = [
    new THREE.Vector3(_box.min.x, _box.max.y, _box.min.z),
    new THREE.Vector3(_box.max.x, _box.max.y, _box.min.z),
    new THREE.Vector3(_box.min.x, _box.max.y, _box.max.z),
    new THREE.Vector3(_box.max.x, _box.max.y, _box.max.z)
  ];
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  corners.forEach(corner => {
    furnitureGroup.worldToLocal(corner);
    minX = Math.min(minX, corner.x);
    maxX = Math.max(maxX, corner.x);
    minZ = Math.min(minZ, corner.z);
    maxZ = Math.max(maxZ, corner.z);
  });
  const inset = 0.06;
  return {
    x: Math.max(minX + inset, Math.min(maxX - inset, x)),
    z: Math.max(minZ + inset, Math.min(maxZ - inset, z))
  };
}

function getSurfaceHit() {
  if (!furnitureGroup || !raycaster) return null;

  raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
  const meshes = getPlacedMeshes(true);
  if (!meshes.length) return null;

  const hits = raycaster.intersectObjects(meshes, false);
  for (const hit of hits) {
    const item = findPlacedItemFromIntersect(hit.object);
    if (!item || !SURFACE_MODELS.has(item.userData.modelKey)) continue;

    furnitureGroup.worldToLocal(_localPoint.copy(hit.point));
    const topY = getPlacedItemTopY(item);
    const clamped = clampToSurfaceBounds(item, _localPoint.x, _localPoint.z);

    return {
      x: clamped.x,
      y: topY,
      z: clamped.z,
      rotY: ghostRotY,
      surfaceId: item.uuid
    };
  }
  return null;
}

function getFloorHit() {
  const { origin, dir } = getRoomLocalLookRay();
  const floorY = getFloorLevelY();
  const maxDist = Math.max(roomData.w, roomData.d) * 0.85;

  const floorHit = intersectPlane(origin, dir, new THREE.Vector3(0, 1, 0), -floorY);
  let target = null;

  if (floorHit && origin.distanceTo(floorHit) <= maxDist) {
    target = floorHit;
  } else if (dir.y <= 0.15) {
    // Looking at walls or slightly down — project aim point onto the floor
    const t = Math.min(maxDist, 3.5);
    target = origin.clone().add(dir.clone().multiplyScalar(t));
    target.y = floorY;
  }

  if (!target) return null;

  const clamped = clampToFloorBounds(target.x, target.z);
  return { x: clamped.x, y: 0, z: clamped.z, rotY: ghostRotY };
}

function getWallMountYLimits() {
  const minY = WALL_MOUNT_MIN_Y;
  const maxY = toFurnitureY(-roomData.h / 2 + roomData.h * WALL_MOUNT_MAX_RATIO);
  return { minY, maxY: Math.max(minY + 0.2, maxY) };
}

function getWallHit() {
  const { origin, dir } = getRoomLocalLookRay();
  const halfW = roomData.w / 2 - 0.2;
  const halfD = roomData.d / 2 - 0.2;
  const { minY, maxY } = getWallMountYLimits();
  const defaultMountY = THREE.MathUtils.clamp(toFurnitureY(origin.y), minY, maxY);

  const walls = [
    { normal: new THREE.Vector3(0, 0, -1), constant: halfD, axis: 'z', value: halfD, rotY: Math.PI, range: halfW, isPositive: true },
    { normal: new THREE.Vector3(0, 0, 1), constant: halfD, axis: 'z', value: -halfD, rotY: 0, range: halfW, isPositive: false },
    { normal: new THREE.Vector3(-1, 0, 0), constant: halfW, axis: 'x', value: halfW, rotY: -Math.PI / 2, range: halfD, isPositive: true },
    { normal: new THREE.Vector3(1, 0, 0), constant: halfW, axis: 'x', value: -halfW, rotY: Math.PI / 2, range: halfD, isPositive: false }
  ];

  let best = null;
  let bestScore = -Infinity;

  walls.forEach(wall => {
    const facing = -dir.dot(wall.normal);
    if (facing < 0.06) return;

    let along;
    let mountY = defaultMountY;
    let dist = 3;

    const hit = intersectPlane(origin, dir, wall.normal, wall.constant);
    if (hit) {
      dist = hit.distanceTo(origin);
      along = wall.axis === 'x' ? hit.z : hit.x;
      const hitMountY = toFurnitureY(hit.y);
      if (hitMountY >= minY - 0.25 && hitMountY <= maxY + 0.25) {
        mountY = THREE.MathUtils.clamp(hitMountY, minY, maxY);
      }
    } else {
      along = wall.axis === 'x' ? origin.z + dir.z * 3 : origin.x + dir.x * 3;
    }

    if (Math.abs(along) > wall.range) return;

    const margin = 0.32;
    const clampedAlong = Math.max(-wall.range + margin, Math.min(wall.range - margin, along));
    const score = facing / (dist + 0.05);

    if (score > bestScore) {
      bestScore = score;
      best = {
        x: wall.axis === 'x' ? wall.value : clampedAlong,
        y: mountY,
        z: wall.axis === 'z' ? wall.value : clampedAlong,
        rotY: wall.rotY,
        wallAxis: wall.axis,
        wallCoord: wall.value,
        isPositiveWall: wall.isPositive
      };
    }
  });

  return best;
}

function getPlacementHit(modelKey) {
  const meta = MODEL_CATALOG[modelKey];
  if (!meta) return null;
  if (meta.type === 'wall') return getWallHit();

  if (STACKABLE_MODELS.has(modelKey)) {
    const surfaceHit = getSurfaceHit();
    if (surfaceHit) return surfaceHit;
  }
  return getFloorHit();
}

function getMeshBottomYInGroup(mesh) {
  mesh.updateWorldMatrix(true, false);
  _box.setFromObject(mesh);
  _worldPoint.set(
    (_box.min.x + _box.max.x) * 0.5,
    _box.min.y,
    (_box.min.z + _box.max.z) * 0.5
  );
  furnitureGroup.worldToLocal(_worldPoint);
  return _worldPoint.y;
}

function getBoxCornersInGroup(mesh, group = furnitureGroup) {
  if (!group) return [];
  mesh.updateWorldMatrix(true, false);
  _box.setFromObject(mesh);
  const corners = [
    new THREE.Vector3(_box.min.x, _box.min.y, _box.min.z),
    new THREE.Vector3(_box.max.x, _box.min.y, _box.min.z),
    new THREE.Vector3(_box.min.x, _box.max.y, _box.min.z),
    new THREE.Vector3(_box.max.x, _box.max.y, _box.min.z),
    new THREE.Vector3(_box.min.x, _box.min.y, _box.max.z),
    new THREE.Vector3(_box.max.x, _box.min.y, _box.max.z),
    new THREE.Vector3(_box.min.x, _box.max.y, _box.max.z),
    new THREE.Vector3(_box.max.x, _box.max.y, _box.max.z)
  ];
  return corners.map(corner => group.worldToLocal(corner));
}

function setWallPosition(mesh, hit, group = furnitureGroup) {
  if (!group || !mesh.userData?.modelKey) return;

  applyModelRotY(mesh, mesh.userData.modelKey, hit.rotY);
  mesh.position.set(hit.x, 0, hit.z);

  let minY = Infinity;
  let maxY = -Infinity;
  const cornersAfterRot = getBoxCornersInGroup(mesh, group);
  if (!cornersAfterRot.length) return;

  cornersAfterRot.forEach(corner => {
    minY = Math.min(minY, corner.y);
    maxY = Math.max(maxY, corner.y);
  });
  if (!Number.isFinite(minY) || !Number.isFinite(maxY)) return;

  mesh.position.y = hit.y - (minY + maxY) * 0.5;

  const inset = WALL_INSET + (mesh.userData.modelKey === 'wall_flat_tv' ? 0.025 : 0);
  const corners = getBoxCornersInGroup(mesh, group);
  if (!corners.length) return;

  if (hit.wallAxis === 'z') {
    const targetZ = hit.isPositiveWall ? hit.wallCoord - inset : hit.wallCoord + inset;
    const backZ = corners.reduce((best, corner) => (
      Math.abs(corner.z - hit.wallCoord) < Math.abs(best - hit.wallCoord) ? corner.z : best
    ), corners[0].z);
    mesh.position.z += targetZ - backZ;
  } else {
    const targetX = hit.isPositiveWall ? hit.wallCoord - inset : hit.wallCoord + inset;
    const backX = corners.reduce((best, corner) => (
      Math.abs(corner.x - hit.wallCoord) < Math.abs(best - hit.wallCoord) ? corner.x : best
    ), corners[0].x);
    mesh.position.x += targetX - backX;
  }

  mesh.userData.wallAxis = hit.wallAxis;
  mesh.userData.wallCoord = hit.wallCoord;
  mesh.userData.isPositiveWall = hit.isPositiveWall;
  mesh.userData.mountY = hit.y;

  mesh.traverse(child => {
    if (child.isMesh) child.renderOrder = 4;
  });
}

function applyPlacementPosition(mesh, hit, placementType = 'floor', { relocate = false } = {}) {
  if (placementType === 'wall') {
    setWallPosition(mesh, hit);
    clampWallItemAlongWall(mesh);
    return;
  }
  if (hit.surfaceId != null || (hit.y ?? 0) > 0.01) {
    setPlacedPosition(mesh, hit.x, hit.z, hit.rotY, hit.y ?? 0);
    return;
  }
  resolveFloorPlacement(mesh, hit.x, hit.z, hit.rotY, hit.y ?? 0, { relocate });
}

function getItemBoundsXZ(itemMesh) {
  const corners = getBoxCornersInGroup(itemMesh);
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  corners.forEach(corner => {
    minX = Math.min(minX, corner.x);
    maxX = Math.max(maxX, corner.x);
    minZ = Math.min(minZ, corner.z);
    maxZ = Math.max(maxZ, corner.z);
  });
  return { minX, maxX, minZ, maxZ };
}

function getTableTopBounds(tableMesh) {
  const corners = getBoxCornersInGroup(tableMesh);
  let maxY = -Infinity;
  corners.forEach(corner => {
    maxY = Math.max(maxY, corner.y);
  });
  const topY = maxY - 0.04;
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  corners.forEach(corner => {
    if (corner.y < topY) return;
    minX = Math.min(minX, corner.x);
    maxX = Math.max(maxX, corner.x);
    minZ = Math.min(minZ, corner.z);
    maxZ = Math.max(maxZ, corner.z);
  });
  return { minX, maxX, minZ, maxZ };
}

function findNearestSurfaceTable(x, z) {
  let best = null;
  let bestDist = Infinity;
  furnitureGroup?.children.forEach(child => {
    if (!SURFACE_MODELS.has(child.userData?.modelKey)) return;
    const fp = getMeshFootprintXZ(child);
    const dx = fp.cx - x;
    const dz = fp.cz - z;
    const dist = dx * dx + dz * dz;
    if (dist < bestDist) {
      bestDist = dist;
      best = child;
    }
  });
  return best;
}

function fitStackedItemOnTable(itemMesh, modelKey) {
  const tableMesh = findNearestSurfaceTable(itemMesh.position.x, itemMesh.position.z);
  if (!tableMesh) return;

  const inset = 0.07;
  const table = getTableTopBounds(tableMesh);
  const item = getItemBoundsXZ(itemMesh);
  let dz = 0;

  if (modelKey === 'office_monitor') {
    const tableMidZ = (table.minZ + table.maxZ) * 0.5;
    const itemMidZ = (item.minZ + item.maxZ) * 0.5;
    if (Math.abs(itemMidZ - tableMidZ) < (table.maxZ - table.minZ) * 0.3) return;
    if (item.minZ < table.minZ + inset) dz = table.minZ + inset - item.minZ;
  } else if (modelKey === 'keyboard_mouse') {
    if (item.maxZ > table.maxZ - inset) dz = table.maxZ - inset - item.maxZ;
    if (item.minZ < table.minZ + inset) dz = table.minZ + inset - item.minZ;
  }

  if (dz !== 0) itemMesh.position.z += dz;
}

function setPlacedPosition(mesh, x, z, rotY, surfaceY = 0) {
  mesh.position.set(x, 0, z);
  applyModelRotY(mesh, mesh.userData.modelKey, rotY);
  groundPlacedMesh(mesh, surfaceY);
}

function groundPlacedMesh(mesh, surfaceY = 0) {
  const bottomY = getMeshBottomYInGroup(mesh);
  mesh.position.y = surfaceY - bottomY;
}

function nudgeAwayFromOverlaps(mesh, maxPasses = 10) {
  for (let pass = 0; pass < maxPasses; pass++) {
    if (!meshHasFloorOverlap(mesh)) return;
    const bounds = getItemBoundsXZ(mesh);
    const cx = (bounds.minX + bounds.maxX) * 0.5;
    const cz = (bounds.minZ + bounds.maxZ) * 0.5;
    const targets = getFloorOverlapTargets(mesh);
    let pushX = 0;
    let pushZ = 0;
    targets.forEach(other => {
      const ob = getItemBoundsXZ(other);
      const ox = (ob.minX + ob.maxX) * 0.5;
      const oz = (ob.minZ + ob.maxZ) * 0.5;
      const dx = cx - ox;
      const dz = cz - oz;
      const len = Math.hypot(dx, dz) || 1;
      pushX += (dx / len) * 0.14;
      pushZ += (dz / len) * 0.14;
    });
    mesh.position.x += pushX;
    mesh.position.z += pushZ;
    clampMeshXZToRoom(mesh);
    groundPlacedMesh(mesh, 0);
  }
}

function placeFloorDecor(modelKey, x, z, rotY, { scale, scaleOverride } = {}) {
  const mesh = createDecorMesh(
    modelKey,
    getDefaultScale(modelKey, scale),
    0,
    0,
    0
  );
  mesh.userData.modelKey = modelKey;
  mesh.userData.placementType = 'floor';
  mesh.userData.isPlacedFurniture = true;
  if (scaleOverride || scale) mesh.userData.scaleOverride = scaleOverride ?? scale;
  furnitureGroup.add(mesh);
  setPlacedPosition(mesh, x, z, rotY, 0);
  clampMeshXZToRoom(mesh);
  nudgeAwayFromOverlaps(mesh);
  return mesh;
}

function layoutItemSortKey(item) {
  const type = item.type || MODEL_CATALOG[item.modelKey]?.type || 'floor';
  if (type === 'wall') return 1;
  if (SURFACE_MODELS.has(item.modelKey)) return 2;
  if (STACKABLE_MODELS.has(item.modelKey)) return 4;
  return 3;
}

function resolveItemSurfaceY(item) {
  const type = item.type || MODEL_CATALOG[item.modelKey]?.type || 'floor';
  if (type === 'wall') return null;

  if (STACKABLE_MODELS.has(item.modelKey)) {
    if (item.floorStand || item.onTable === false) return 0;
    if (item.stackOn != null) {
      const parent = findPlacedItemByTemplateIndex(item.stackOn);
      if (parent) return getPlacedItemTopY(parent);
    }
    const table = findNearestSurfaceTable(item.x, item.z);
    if (table) {
      const fp = getMeshFootprintXZ(table);
      const dist = Math.hypot(fp.cx - item.x, fp.cz - item.z);
      if (dist < Math.max(fp.halfX, fp.halfZ) + 0.28) return getPlacedItemTopY(table);
    }
    if (item.surfaceY != null) return item.surfaceY;
    return 0;
  }

  return 0;
}

function placeLayoutItem(mesh, item, options = {}) {
  const type = item.type || MODEL_CATALOG[item.modelKey]?.type || 'floor';
  const relocate = options.relocate ?? item.relocate ?? false;

  if (type === 'wall') {
    setWallPosition(mesh, {
      x: item.x,
      z: item.z,
      y: item.mountY ?? item.y ?? 0,
      rotY: item.rotY ?? 0,
      wallAxis: item.wallAxis ?? 'z',
      wallCoord: item.wallCoord ?? -(roomData.d / 2 - 0.2),
      isPositiveWall: item.isPositiveWall ?? false
    });
    clampWallItemAlongWall(mesh);
    return;
  }

  if (STACKABLE_MODELS.has(item.modelKey)) {
    if (item.stackOn != null) {
      const parent = findPlacedItemByTemplateIndex(item.stackOn);
      if (parent) {
        const surfaceY = getPlacedItemTopY(parent);
        const { x, z } = resolveStackPosition(parent, furnitureGroup, item);
        setPlacedPosition(mesh, x, z, item.rotY ?? 0, surfaceY);
        if (!item.skipTableFit) fitStackedItemOnTable(mesh, item.modelKey);
        return;
      }
    }
    const surfaceY = resolveItemSurfaceY(item);
    setPlacedPosition(mesh, item.x, item.z, item.rotY ?? 0, surfaceY);
    clampMeshXZToRoom(mesh);
    if (!item.skipTableFit) fitStackedItemOnTable(mesh, item.modelKey);
    return;
  }

  const surfaceY = resolveItemSurfaceY(item);
  resolveFloorPlacement(mesh, item.x, item.z, item.rotY ?? 0, surfaceY, { relocate });
}

function getMeshFootprintXZ(mesh) {
  mesh.updateWorldMatrix(true, false);
  _box.setFromObject(mesh);
  _worldPoint.copy(_box.getCenter(new THREE.Vector3()));
  furnitureGroup.worldToLocal(_worldPoint);
  const size = new THREE.Vector3();
  _box.getSize(size);
  return {
    cx: _worldPoint.x,
    cz: _worldPoint.z,
    halfX: size.x * 0.5,
    halfZ: size.z * 0.5
  };
}

function placeStackedOnTable(tableMesh, def) {
  const fp = getMeshFootprintXZ(tableMesh);
  const rotY = tableMesh.rotation.y;
  const cos = Math.cos(rotY);
  const sin = Math.sin(rotY);
  const localX = (def.lxf ?? 0) * fp.halfX;
  const localZ = (def.lzf ?? 0) * fp.halfZ;
  const x = fp.cx + localX * cos - localZ * sin;
  const z = fp.cz + localX * sin + localZ * cos;
  const surfaceY = getPlacedItemTopY(tableMesh);

  const mesh = createDecorMesh(
    def.modelKey,
    getDefaultScale(def.modelKey, def.scale),
    0,
    0,
    0
  );
  mesh.userData.modelKey = def.modelKey;
  mesh.userData.placementType = 'floor';
  mesh.userData.isPlacedFurniture = true;
  if (def.scale) mesh.userData.scaleOverride = def.scale;
  furnitureGroup.add(mesh);
  setPlacedPosition(mesh, x, z, def.rotY ?? 0, surfaceY);
  return mesh;
}

function snapChairToTableEdge(chairMesh, tableMesh, dirX, dirZ) {
  const gap = 0.14;
  const table = getItemBoundsXZ(tableMesh);
  const chair = getItemBoundsXZ(chairMesh);
  let dx = 0;
  let dz = 0;

  if (dirZ > 0) dz = (table.maxZ + gap) - chair.minZ;
  else if (dirZ < 0) dz = (table.minZ - gap) - chair.maxZ;
  if (dirX > 0) dx = (table.maxX + gap) - chair.minX;
  else if (dirX < 0) dx = (table.minX - gap) - chair.maxX;

  chairMesh.position.x += dx;
  chairMesh.position.z += dz;
}

function measureChairFootprint() {
  const probe = createDecorMesh('simple_chair', getDefaultScale('simple_chair'), 0, 0, 0);
  furnitureGroup.add(probe);
  applyModelRotY(probe, 'simple_chair', 0);
  probe.position.set(0, 0, 0);
  probe.updateWorldMatrix(true, false);
  _box.setFromObject(probe);
  const size = new THREE.Vector3();
  _box.getSize(size);
  furnitureGroup.remove(probe);
  disposePlacedObject(probe);
  return {
    halfW: size.x * 0.5,
    halfD: size.z * 0.5
  };
}

function faceChairToward(chairMesh, targetX, targetZ) {
  const bounds = getItemBoundsXZ(chairMesh);
  const cx = (bounds.minX + bounds.maxX) * 0.5;
  const cz = (bounds.minZ + bounds.maxZ) * 0.5;
  const dx = targetX - cx;
  const dz = targetZ - cz;
  // simple_chair GLB seat faces +Z at rotY = 0 (same as conference template rotY: Math.PI toward -Z)
  const rotY = Math.atan2(dx, dz);
  applyModelRotY(chairMesh, 'simple_chair', rotY);
  const bottomY = getMeshBottomYInGroup(chairMesh);
  chairMesh.position.y = -bottomY;
}

function placeHackathonChairs(tableMesh) {
  const table = getItemBoundsXZ(tableMesh);
  const tableCx = (table.minX + table.maxX) * 0.5;
  const tableCz = (table.minZ + table.maxZ) * 0.5;
  const halfX = (table.maxX - table.minX) * 0.5;
  const halfZ = (table.maxZ - table.minZ) * 0.5;
  const longIsX = halfX >= halfZ;
  const chair = getHackathonChairFootprint();
  const gap = 0.14;

  const alongHalf = longIsX ? halfX : halfZ;
  const edgeHalf = longIsX ? halfZ : halfX;
  const chairAlong = longIsX ? chair.halfW : chair.halfD;
  const chairDepth = longIsX ? chair.halfD : chair.halfW;
  const minSpread = chairAlong + 0.16;
  const maxSpread = Math.max(minSpread, alongHalf - chairAlong - 0.08);
  const seatSpread = Math.min(maxSpread, Math.max(minSpread, alongHalf * 0.38));
  const edgeDist = edgeHalf + gap + chairDepth;

  const sides = longIsX
    ? [{ nx: 0, nz: 1 }, { nx: 0, nz: -1 }]
    : [{ nx: 1, nz: 0 }, { nx: -1, nz: 0 }];

  sides.forEach(({ nx, nz }) => {
    [-1, 1].forEach(sign => {
      const px = longIsX ? tableCx + sign * seatSpread : tableCx + nx * edgeDist;
      const pz = longIsX ? tableCz + nz * edgeDist : tableCz + sign * seatSpread;

      const mesh = createDecorMesh('simple_chair', getDefaultScale('simple_chair'), 0, 0, 0);
      mesh.userData.modelKey = 'simple_chair';
      mesh.userData.placementType = 'floor';
      mesh.userData.isPlacedFurniture = true;
      furnitureGroup.add(mesh);
      setPlacedPosition(mesh, px, pz, 0, 0);
      faceChairToward(mesh, tableCx, tableCz);
      snapChairToTableEdge(mesh, tableMesh, nx, nz);
      faceChairToward(mesh, tableCx, tableCz);
      clampMeshXZToRoom(mesh);
    });
  });
}

function placeHackathonPod(cx, cz) {
  const tableMesh = spawnLayoutMesh({
    modelKey: 'simple_table',
    x: cx,
    z: cz,
    rotY: 0,
    type: 'floor',
    skipTableFit: true,
    relocate: true
  });
  if (!tableMesh) return;

  placeHackathonChairs(tableMesh);

  [
    { modelKey: 'office_monitor', lxf: 0, lzf: 0.28, rotY: 0 },
    { modelKey: 'office_monitor', lxf: 0, lzf: -0.28, rotY: Math.PI },
    { modelKey: 'speaker', lxf: 0, lzf: 0, rotY: 0, scale: { h: 0.22 } }
  ].forEach(def => placeStackedOnTable(tableMesh, def));
}

function applyHackathonPods(roomW, roomD) {
  if (!furnitureGroup || !roomData) return;

  clearAllPlacedFurniture();

  _hackathonChairFootprint = null;

  getHackathonPodCenters(roomW, roomD).forEach(({ cx, cz }) => {
    placeHackathonPod(cx, cz);
  });

  clearSelectionHighlight();
  deselectModel();
  persistLayout();
  updatePlacedCount();
}

function placeWallDecor(modelKey, hit) {
  const mesh = createDecorMesh(modelKey, getDefaultScale(modelKey), 0, 0, 0);
  mesh.userData.modelKey = modelKey;
  mesh.userData.placementType = 'wall';
  mesh.userData.isPlacedFurniture = true;
  furnitureGroup.add(mesh);
  setWallPosition(mesh, hit);
  clampWallItemAlongWall(mesh);
  return mesh;
}

function applyMediaStudio(roomW, roomD, roomH) {
  if (!furnitureGroup || !roomData) return;

  clearAllPlacedFurniture();

  const layout = getMediaStudioLayout(roomW, roomD, roomH);

  placeWallDecor('wall_flat_tv', buildWallHitFromDef(roomW, roomD, roomH, layout.wallTv));

  const desk = placeFloorDecor('simple_table', layout.desk.x, layout.desk.z, layout.desk.rotY);

  placeStackedOnTable(desk, {
    modelKey: 'office_monitor',
    lxf: 0,
    lzf: -0.22,
    rotY: 0
  });
  placeStackedOnTable(desk, {
    modelKey: 'keyboard_mouse',
    lxf: 0,
    lzf: 0.24,
    rotY: 0
  });

  placeFloorDecor('led_tv', layout.floorTv.x, layout.floorTv.z, layout.floorTv.rotY);

  placeFloorDecor('speaker', layout.speakerMain.x, layout.speakerMain.z, layout.speakerMain.rotY, {
    scale: layout.speakerMain.scale
  });
  placeFloorDecor('speaker', layout.speakerFill.x, layout.speakerFill.z, layout.speakerFill.rotY, {
    scale: layout.speakerFill.scale
  });

  const deskBounds = getItemBoundsXZ(desk);
  const deskCx = (deskBounds.minX + deskBounds.maxX) * 0.5;
  const deskCz = (deskBounds.minZ + deskBounds.maxZ) * 0.5;

  const chair = placeFloorDecor(
    'simple_chair',
    layout.talentChair.x,
    layout.talentChair.z,
    0
  );
  faceChairToward(chair, deskCx, deskCz);
  clampMeshXZToRoom(chair);
  groundPlacedMesh(chair, 0);

  placeFloorDecor('microphone_stand', layout.mic.x, layout.mic.z, layout.mic.rotY);

  clearSelectionHighlight();
  deselectModel();
  persistLayout();
  updatePlacedCount();
}

function placeClassroomChairForTable(tableMesh, sideZ = 1) {
  const table = getItemBoundsXZ(tableMesh);
  const tableCx = (table.minX + table.maxX) * 0.5;
  const tableCz = (table.minZ + table.maxZ) * 0.5;
  const halfZ = (table.maxZ - table.minZ) * 0.5;
  const pz = tableCz + sideZ * (halfZ + 0.42);

  const chair = placeFloorDecor('simple_chair', tableCx, pz, 0);
  faceChairToward(chair, tableCx, tableCz);
  snapChairToTableEdge(chair, tableMesh, 0, sideZ);
  faceChairToward(chair, tableCx, tableCz);
  clampMeshXZToRoom(chair);
  groundPlacedMesh(chair, 0);
  return chair;
}

function placeClassroomWorkstation(x, z) {
  const table = placeFloorDecor('simple_table', x, z, 0);
  placeStackedOnTable(table, {
    modelKey: 'office_monitor',
    lxf: 0,
    lzf: -0.22,
    rotY: 0
  });
  placeStackedOnTable(table, {
    modelKey: 'keyboard_mouse',
    lxf: 0,
    lzf: 0.22,
    rotY: 0
  });
  placeClassroomChairForTable(table, 1);
  return table;
}

function placeInstructorStation({ x, z, rotY }) {
  const table = placeFloorDecor('office_table', x, z, rotY);
  placeStackedOnTable(table, {
    modelKey: 'office_monitor',
    lxf: 0,
    lzf: -0.22,
    rotY: 0
  });
  placeStackedOnTable(table, {
    modelKey: 'keyboard_mouse',
    lxf: 0,
    lzf: 0.22,
    rotY: 0
  });
  placeClassroomChairForTable(table, -1);
  return table;
}

function applyClassroom(roomW, roomD, roomH) {
  if (!furnitureGroup || !roomData) return;

  clearAllPlacedFurniture();

  const layout = getClassroomLayout(roomW, roomD);

  placeFloorDecor('whiteboard', layout.whiteboard.x, layout.whiteboard.z, layout.whiteboard.rotY);
  placeWallDecor('wall_flat_tv', buildWallHitFromDef(roomW, roomD, roomH, layout.wallTv));

  layout.workstations.forEach(({ x, z }) => {
    placeClassroomWorkstation(x, z);
  });

  if (layout.instructor) {
    placeInstructorStation(layout.instructor);
  }

  clearSelectionHighlight();
  deselectModel();
  persistLayout();
  updatePlacedCount();
}

function clearAllPlacedFurniture() {
  const toRemove = furnitureGroup.children.filter(c => c.userData?.isPlacedFurniture);
  toRemove.forEach(child => {
    furnitureGroup.remove(child);
    disposePlacedObject(child);
  });
}

let _hackathonChairFootprint = null;

function getHackathonChairFootprint() {
  if (!_hackathonChairFootprint) {
    _hackathonChairFootprint = measureChairFootprint();
  }
  return _hackathonChairFootprint;
}

function sortLayoutItems(items) {
  return [...items].sort((a, b) => layoutItemSortKey(a) - layoutItemSortKey(b));
}

function spawnLayoutMesh(item, options = {}) {
  if (!MODEL_CATALOG[item.modelKey]) return null;
  if (item.modelKey === 'whiteboard') item.type = 'floor';

  const mesh = createDecorMesh(
    item.modelKey,
    getDefaultScale(item.modelKey, item.scale),
    0,
    0,
    0
  );
  mesh.userData.modelKey = item.modelKey;
  mesh.userData.placementType = item.type || MODEL_CATALOG[item.modelKey].type;
  mesh.userData.isPlacedFurniture = true;
  if (item.scale) mesh.userData.scaleOverride = item.scale;
  if (item.templateIndex != null) mesh.userData.templateIndex = item.templateIndex;
  furnitureGroup.add(mesh);
  placeLayoutItem(mesh, item, options);
  return mesh;
}

function createPlacedItem(modelKey, hit, placementType = 'floor') {
  const mesh = createDecorMesh(modelKey, getDefaultScale(modelKey), 0, hit.rotY, 0);
  mesh.userData.modelKey = modelKey;
  mesh.userData.placementType = placementType;
  mesh.userData.isPlacedFurniture = true;
  furnitureGroup.add(mesh);
  applyPlacementPosition(mesh, hit, placementType, { relocate: true });
  return mesh;
}

function clearFurnitureGroup(group) {
  if (!group) return;
  [...group.children].forEach(child => {
    group.remove(child);
    disposePlacedObject(child);
  });
}

function loadSavedLayout() {
  if (!furnitureGroup || !roomData?.roomId) return;
  clearFurnitureGroup(furnitureGroup);

  const items = loadLayout(roomData.roomId);
  sortLayoutItems(items).forEach(item => {
    spawnLayoutMesh(item);
  });
  updatePlacedCount();
}

/** Populate every room's saved layout at startup (visible through windows before entering). */
export function hydrateAllRoomLayouts() {
  const prevRoomGroup = roomGroup;
  const prevRoomData = roomData;
  const prevFurnitureGroup = furnitureGroup;

  boxData.forEach(hitMesh => {
    const data = hitMesh.userData;
    if (!data?.roomId) return;

    const group = hitMesh.parent;
    const userFurniture = group?.userData?.userFurniture;
    if (!userFurniture) return;

    const items = loadLayout(data.roomId);
    if (!items.length) return;

    clearFurnitureGroup(userFurniture);

    roomGroup = group;
    roomData = data;
    furnitureGroup = userFurniture;

    sortLayoutItems(items).forEach(item => {
      spawnLayoutMesh(item);
    });
  });

  roomGroup = prevRoomGroup;
  roomData = prevRoomData;
  furnitureGroup = prevFurnitureGroup;
}

function clearSelectionHighlight() {
  highlightBackup.forEach(({ mat, emissive, intensity }) => {
    mat.emissive.copy(emissive);
    if (mat.emissiveIntensity !== undefined) mat.emissiveIntensity = intensity;
    mat.needsUpdate = true;
  });
  highlightBackup = [];
  selectedItem = null;
}

function highlightItem(item) {
  clearSelectionHighlight();
  selectedItem = item;
  item.traverse(child => {
    if (!child.isMesh || !child.material) return;
    const mats = Array.isArray(child.material) ? child.material : [child.material];
    mats.forEach(mat => {
      highlightBackup.push({
        mat,
        emissive: mat.emissive.clone(),
        intensity: mat.emissiveIntensity ?? 0
      });
      mat.emissive.copy(HIGHLIGHT_COLOR);
      if (mat.emissiveIntensity !== undefined) mat.emissiveIntensity = 0.6;
      mat.needsUpdate = true;
    });
  });
}

function placeSelectedModel() {
  if (!selectedModelKey || !furnitureGroup) return;
  const hit = getPlacementHit(selectedModelKey);
  if (!hit) return;

  const meta = MODEL_CATALOG[selectedModelKey];
  createPlacedItem(selectedModelKey, hit, meta.type);
  persistLayout();
  updatePlacedCount();
}

function disposePlacedObject(root) {
  root.traverse(child => {
    if (child.isMesh && !child.userData.catalogGeometry) {
      child.geometry?.dispose();
    }
  });
}

function deletePlacedItem(item) {
  if (!item || !furnitureGroup) return;
  furnitureGroup.remove(item);
  disposePlacedObject(item);
  if (selectedItem === item) clearSelectionHighlight();
  persistLayout();
  updatePlacedCount();
}

function deleteSelectedItem() {
  if (!selectedItem) return;
  deletePlacedItem(selectedItem);
}

function updateFurnishHint() {}

function showTemplateAppliedHint(_template) {}

function getMeshTopYInGroup(mesh, group) {
  mesh.updateWorldMatrix(true, false);
  _box.setFromObject(mesh);
  _worldPoint.set(
    (_box.min.x + _box.max.x) * 0.5,
    _box.max.y,
    (_box.min.z + _box.max.z) * 0.5
  );
  group.worldToLocal(_worldPoint);
  return _worldPoint.y;
}

function getMeshBottomYForGroup(mesh, group) {
  mesh.updateWorldMatrix(true, false);
  _box.setFromObject(mesh);
  _worldPoint.set(
    (_box.min.x + _box.max.x) * 0.5,
    _box.min.y,
    (_box.min.z + _box.max.z) * 0.5
  );
  group.worldToLocal(_worldPoint);
  return _worldPoint.y;
}

function resolveStackPosition(parentMesh, group, def) {
  parentMesh.updateWorldMatrix(true, false);
  _box.setFromObject(parentMesh);
  const center = _box.getCenter(new THREE.Vector3());
  group.worldToLocal(center);

  const size = new THREE.Vector3();
  _box.getSize(size);
  const halfW = size.x * 0.5;
  const halfD = size.z * 0.5;

  const localX = (def.lx ?? 0) + (def.lxf ?? 0) * halfW;
  const localZ = (def.lz ?? 0) + (def.lzf ?? 0) * halfD;

  const rotY = parentMesh.rotation.y;
  const cos = Math.cos(rotY);
  const sin = Math.sin(rotY);
  const dx = localX * cos - localZ * sin;
  const dz = localX * sin + localZ * cos;

  return {
    x: center.x + dx,
    z: center.z + dz
  };
}

function isWallTemplateItem(def, meta) {
  return meta.type === 'wall' || def.wall != null;
}

function buildWallHitFromDef(roomW, roomD, roomH, def) {
  const pad = Math.min(0.22, roomW * 0.06, roomD * 0.06);
  const scaleX = roomW / 2 - pad;
  const scaleZ = roomD / 2 - pad;
  const inset = 0.1;
  const halfW = roomW / 2 - inset;
  const halfD = roomD / 2 - inset;
  const floorY = roomGroup?.userData?.floorY ?? (-roomH / 2 + 0.22);
  const floorRoomY = -roomH / 2 + 0.22;
  const ceilRoomY = roomH / 2 - 0.28;
  let mountRoomY;
  if (def.mountYR != null) {
    mountRoomY = floorRoomY + (ceilRoomY - floorRoomY) * def.mountYR;
  } else {
    mountRoomY = THREE.MathUtils.clamp(
      def.mountY ?? roomH * 0.55,
      floorRoomY + 0.45,
      ceilRoomY - 0.08
    );
  }
  const furnitureMountY = mountRoomY - floorY;
  const wall = def.wall ?? 'back';
  const alongX = (def.nx ?? 0) * scaleX;
  const alongZ = (def.nz ?? 0) * scaleZ;

  const walls = {
    back: {
      x: alongX,
      z: -halfD,
      rotY: def.rotY ?? 0,
      wallAxis: 'z',
      wallCoord: -halfD,
      isPositiveWall: false
    },
    front: {
      x: alongX,
      z: halfD,
      rotY: def.rotY ?? Math.PI,
      wallAxis: 'z',
      wallCoord: halfD,
      isPositiveWall: true
    },
    left: {
      x: -halfW,
      z: alongZ,
      rotY: def.rotY ?? Math.PI / 2,
      wallAxis: 'x',
      wallCoord: -halfW,
      isPositiveWall: false
    },
    right: {
      x: halfW,
      z: alongZ,
      rotY: def.rotY ?? -Math.PI / 2,
      wallAxis: 'x',
      wallCoord: halfW,
      isPositiveWall: true
    }
  };

  const base = walls[wall] ?? walls.back;
  return { ...base, y: furnitureMountY };
}

function buildLayoutFromTemplate(template, roomW, roomD, roomH) {
  const pad = Math.min(0.22, roomW * 0.06, roomD * 0.06);
  const scaleX = roomW / 2 - pad;
  const scaleZ = roomD / 2 - pad;
  const tempGroup = new THREE.Group();
  const tempMeshes = [];
  const layout = [];

  template.items.forEach((def, idx) => {
    if (def.stackOn != null) return;
    const meta = MODEL_CATALOG[def.modelKey];
    if (!meta || isWallTemplateItem(def, meta)) return;

    const mesh = createDecorMesh(def.modelKey, getDefaultScale(def.modelKey, def.scale), 0, def.rotY ?? 0, 0);
    const x = def.nx * scaleX;
    const z = def.nz * scaleZ;
    mesh.position.set(x, 0, z);
    applyModelRotY(mesh, def.modelKey, def.rotY ?? 0);
    const bottomY = getMeshBottomYForGroup(mesh, tempGroup);
    mesh.position.y = -bottomY;
    tempGroup.add(mesh);
    tempMeshes[idx] = mesh;

    layout.push({
      modelKey: def.modelKey,
      x,
      z,
      rotY: def.rotY ?? 0,
      type: meta.type,
      surfaceY: mesh.position.y + bottomY,
      scale: def.scale,
      templateIndex: idx
    });
  });

  template.items.forEach((def) => {
    if (def.stackOn == null) return;
    const parentMesh = tempMeshes[def.stackOn];
    const meta = MODEL_CATALOG[def.modelKey];
    if (!parentMesh || !meta) return;

    const surfaceY = getMeshTopYInGroup(parentMesh, tempGroup);
    const { x, z } = resolveStackPosition(parentMesh, tempGroup, def);

    layout.push({
      modelKey: def.modelKey,
      x,
      z,
      rotY: def.rotY ?? 0,
      type: meta.type,
      surfaceY,
      scale: def.scale,
      stackOn: def.stackOn,
      lxf: def.lxf,
      lzf: def.lzf,
      lx: def.lx,
      lz: def.lz
    });
  });

  template.items.forEach((def, idx) => {
    if (def.stackOn != null) return;
    const meta = MODEL_CATALOG[def.modelKey];
    if (!meta || !isWallTemplateItem(def, meta)) return;

    const hit = buildWallHitFromDef(roomW, roomD, roomH, def);
    const mesh = createDecorMesh(def.modelKey, getDefaultScale(def.modelKey), 0, 0, 0);
    mesh.userData.modelKey = def.modelKey;
    tempGroup.add(mesh);
    setWallPosition(mesh, hit, tempGroup);
    tempMeshes[idx] = mesh;

    layout.push({
      modelKey: def.modelKey,
      x: mesh.position.x,
      z: mesh.position.z,
      mountY: mesh.userData.mountY ?? hit.y,
      rotY: def.rotY ?? hit.rotY,
      type: 'wall',
      wallAxis: hit.wallAxis,
      wallCoord: hit.wallCoord,
      isPositiveWall: hit.isPositiveWall
    });
  });

  return layout;
}

export function applyRoomTemplate(templateId) {
  const template = getRoomTemplate(templateId);
  if (!template || !roomData) return;

  if (roomData.roomId) localStorage.removeItem(storageKey(roomData.roomId));

  if (templateId === 'hackathon') {
    applyHackathonPods(roomData.w, roomData.d);
    setActiveTemplateId(templateId);
    showTemplateAppliedHint(template);
    return;
  }

  if (templateId === 'media') {
    applyMediaStudio(roomData.w, roomData.d, roomData.h);
    setActiveTemplateId(templateId);
    showTemplateAppliedHint(template);
    return;
  }

  if (templateId === 'classroom') {
    applyClassroom(roomData.w, roomData.d, roomData.h);
    setActiveTemplateId(templateId);
    showTemplateAppliedHint(template);
    return;
  }

  const items = buildLayoutFromTemplate(template, roomData.w, roomData.d, roomData.h);
  applyLayoutFromPlan(items, { relocate: true });
  setActiveTemplateId(templateId);
  showTemplateAppliedHint(template);
}

function setTemplatesMode(on) {
  templatesModeActive = on;
  document.body.classList.toggle('furnish-templates-mode', on);
  if (on) {
    deselectModel();
    setRemoveMode(false);
    clearSelectionHighlight();
    setCrosshairVisible(false);
  } else {
    updateFurnishHint();
    if (removeModeActive) setCrosshairVisible(true);
  }
}

function clearRoomLayout() {
  if (!furnitureGroup || !roomData?.roomId) return;
  while (furnitureGroup.children.length) {
    const child = furnitureGroup.children[0];
    furnitureGroup.remove(child);
    disposePlacedObject(child);
  }
  clearSelectionHighlight();
  deselectModel();
  setActiveTemplateId(null);
  localStorage.removeItem(storageKey(roomData.roomId));
  updatePlacedCount();
}

function setCrosshairVisible(visible) {
  const crosshair = document.getElementById('placement-crosshair');
  if (crosshair) crosshair.classList.toggle('visible', visible);
}

function setRemoveMode(on) {
  removeModeActive = on;
  document.body.classList.toggle('furnish-remove-mode', on);
  if (on) {
    deselectModel();
    clearSelectionHighlight();
    setCrosshairVisible(true);
  } else if (!selectedModelKey) {
    setCrosshairVisible(false);
  }
  updateFurnishHint();
}

function deselectModel() {
  selectedModelKey = null;
  ghostRotY = 0;
  disposeGhost();
  updatePaletteActive(null);
  setCrosshairVisible(false);
}

function setSelectedModel(modelKey) {
  if (selectedModelKey === modelKey) {
    deselectModel();
    return;
  }
  setRemoveMode(false);
  clearSelectionHighlight();
  selectedModelKey = modelKey;
  ghostRotY = 0;
  updatePaletteActive(modelKey);
  setCrosshairVisible(true);
  collapseFurnishPanel();
  updateGhost();
}

function updatePlacedCount() {
  const count = furnitureGroup?.children.filter(c => c.userData?.modelKey).length ?? 0;
  setPlacedItemCount(count);
}

function updatePaletteActive(modelKey) {
  setPanelActiveModel(modelKey);
}

function buildPalette() {
  const panel = document.getElementById('furniture-panel');
  if (!panel || panel.dataset.built) return;
  panel.dataset.built = 'true';

  buildFurniturePanel((modelKey) => {
    if (modelKey) setSelectedModel(modelKey);
    else deselectModel();
  });

  initAiPanel();

  setFurniturePanelFilterHandler((filter) => {
    if (getActiveFurnishSection() === 'customize') {
      setRemoveMode(filter === 'remove');
    }
  });

  setFurnitureSectionHandler((section) => {
    setTemplatesMode(section === 'templates');
    if (section === 'ai') {
      deselectModel();
      clearSelectionHighlight();
      setCrosshairVisible(false);
      refreshAiRoomContext();
    }
  });

  setTemplateSelectHandler((templateId) => {
    applyRoomTemplate(templateId);
  });

  document.getElementById('btn-clear-room')?.addEventListener('click', async (e) => {
    e.stopPropagation();
    const ok = await showConfirm({
      title: 'Are you sure you want to clear?',
      message: 'All furniture will be removed from this room. This cannot be undone.',
      confirmLabel: 'Clear room',
      cancelLabel: 'Keep items',
      variant: 'danger'
    });
    if (ok) clearRoomLayout();
  });

  document.getElementById('btn-floorplan')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const snap = captureRoomSnapshot();
    if (snap) showFloorPlanModal(snap, applyLayoutFromPlan);
  });
}

function findPlacedItemFromIntersect(object) {
  let obj = object;
  while (obj) {
    if (obj.userData?.isPlacedFurniture) return obj;
    if (obj === furnitureGroup) break;
    obj = obj.parent;
  }
  return null;
}

function handleIndoorClick() {
  if (!active || !furnitureGroup) return;
  if (templatesModeActive) return;

  if (selectedModelKey) {
    placeSelectedModel();
    updateGhost();
    return;
  }

  raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
  const targets = [];
  furnitureGroup.traverse(child => {
    if (child.userData?.isPlacedFurniture) targets.push(child);
  });

  if (targets.length) {
    const hits = raycaster.intersectObjects(targets, true);
    if (hits.length) {
      const item = findPlacedItemFromIntersect(hits[0].object);
      if (item) {
        if (removeModeActive) {
          deletePlacedItem(item);
          return;
        }
        highlightItem(item);
        return;
      }
    }
  }

  if (!removeModeActive) clearSelectionHighlight();
}

export function handleFurnishingClick() {
  handleIndoorClick();
}

export function updateFurnishingPreview() {
  if (!active || !selectedModelKey || templatesModeActive) return;
  updateGhost();
}

export function initFurnishing(r, cam) {
  renderer = r;
  camera = cam;
  window.__spaceflowGetLayoutItems = () => serializeLayout();
  raycaster = new THREE.Raycaster();
  buildPalette();

  if (!window._aiLayoutListenerBound) {
    window._aiLayoutListenerBound = true;
    window.addEventListener('spaceflow:ai-layout', () => {
      setFurnishSection('ai');
      setTemplatesMode(false);
      setActiveTemplateId(null);
      deselectModel();
      clearSelectionHighlight();
      setCrosshairVisible(false);
    });
  }

  window.addEventListener('keydown', (e) => {
    if (!active || templatesModeActive) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (e.key === 'r' || e.key === 'R') {
      if (selectedModelKey && MODEL_CATALOG[selectedModelKey]?.type === 'floor') {
        ghostRotY += Math.PI / 4;
        updateGhost();
      }
    } else if (e.key === 'c' || e.key === 'C') {
      if (selectedModelKey) deselectModel();
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
      deleteSelectedItem();
    } else if (e.key === 'Escape') {
      if (selectedItem) clearSelectionHighlight();
      else deselectModel();
    }
  });

}

export function enterFurnishingMode(group, data) {
  active = true;
  roomGroup = group;
  roomData = data;
  furnitureGroup = group.userData.userFurniture;

  if (!furnitureGroup) {
    group.traverse(child => {
      if (child.userData?.isUserFurniture) furnitureGroup = child;
    });
  }

  loadSavedLayout();

  const panel = document.getElementById('furniture-panel');
  if (panel) {
    panel.style.display = 'flex';
    expandFurnishPanel();
    panel.style.setProperty('--room-color', data.color);
  }

  deselectModel();
  const savedItems = roomData?.roomId ? loadLayout(roomData.roomId) : [];

  if (savedItems.length === 0) {
    setFurnishSection('ai');
    setActiveTemplateId(null);
  } else {
    setFurnishSection('customize');
    setTemplatesMode(false);
    setRemoveMode(getActiveFurnishFilter() === 'remove');
  }

  setTemplatesMode(getActiveFurnishSection() === 'templates');
  updatePlacedCount();
  refreshAiRoomContext();
}

export function applyLayoutFromPlan(items, options = {}) {
  if (!furnitureGroup || !roomData) return;

  clearAllPlacedFurniture();

  sortLayoutItems(items).forEach(item => {
    spawnLayoutMesh(item, options);
  });

  clearSelectionHighlight();
  deselectModel();
  persistLayout({ skipBridge: options.source === 'ai_agent' });
  updatePlacedCount();
}

export function getCurrentLayoutItems() {
  return serializeLayout();
}

export function getPersistedLayoutItems(roomId) {
  return loadLayout(roomId);
}

export function captureRoomSnapshot() {
  if (!roomData) return null;
  return {
    roomData: { ...roomData },
    items: serializeLayout()
  };
}

export function exitFurnishingMode() {
  const snapshot = captureRoomSnapshot();
  if (active) persistLayout();
  active = false;
  setTemplatesMode(false);
  setRemoveMode(false);
  deselectModel();
  clearSelectionHighlight();
  setCrosshairVisible(false);
  roomGroup = null;
  roomData = null;
  furnitureGroup = null;

  const panel = document.getElementById('furniture-panel');
  if (panel) panel.style.display = 'none';

  return snapshot;
}


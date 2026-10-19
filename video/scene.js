import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const WIDTH = 1920;
const HEIGHT = 1080;
const DURATION = 20;
const COLORS = {
  background: 0x15191e,
  holder: 0x424c57,
  mac: 0xc6cbd1,
  tpu: 0x5f9abc,
  screw: 0xabb4bd,
  insert: 0xc99b49,
};

// Convert the source CAD's Z-up millimetres to the renderer's Y-up world.
function toWorld([x, y, z]) {
  return new THREE.Vector3(x - 241.3, z - 66.28, 67 - y);
}

function directionToWorld([x, y, z]) {
  return new THREE.Vector3(x, z, -y);
}

// Smooth, clamped progress makes arbitrary timeline seeks deterministic.
function progress(time, start, end) {
  const t = THREE.MathUtils.clamp((time - start) / (end - start), 0, 1);
  return t * t * (3 - 2 * t);
}

// A phase withdraws each component, holds it, then returns it to its CAD position.
function separation(time, outStart, outEnd, inStart, inEnd) {
  return progress(time, outStart, outEnd) * (1 - progress(time, inStart, inEnd));
}

async function buildScene() {
  const response = await fetch('./assets/assembly.json');
  if (!response.ok) throw new Error(`Assembly load failed: HTTP ${response.status}`);
  const assembly = await response.json();
  if (!Array.isArray(assembly.parts) || assembly.parts.length !== 44) {
    throw new Error('Expected 26 CAD parts and 18 hardware parts.');
  }

  const canvas = document.getElementById('assembly-canvas');
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(1);
  renderer.setSize(WIDTH, HEIGHT, false);
  renderer.setClearColor(COLORS.background);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const environment = pmrem.fromScene(room, 0.04);
  scene.environment = environment.texture;
  room.dispose();
  pmrem.dispose();

  scene.add(new THREE.HemisphereLight(0xf1f4f9, 0x334154, 2.1));
  const key = new THREE.DirectionalLight(0xffffff, 3.2);
  key.position.set(-350, 600, 550);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, {left:-650, right:650, top:550, bottom:-450, near:1, far:1800});
  key.shadow.bias = -0.00015;
  key.shadow.normalBias = 0.35;
  key.shadow.radius = 4;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xa2bfdc, 2.4);
  rim.position.set(350, 250, -350);
  scene.add(rim);

  const materials = {
    holder: new THREE.MeshStandardMaterial({color:COLORS.holder, roughness:0.56, metalness:0.12}),
    mac: new THREE.MeshStandardMaterial({color:COLORS.mac, roughness:0.32, metalness:0.75}),
    tpu: new THREE.MeshStandardMaterial({color:COLORS.tpu, roughness:0.84, metalness:0}),
    screw: new THREE.MeshStandardMaterial({color:COLORS.screw, roughness:0.27, metalness:0.85}),
    insert: new THREE.MeshStandardMaterial({color:COLORS.insert, roughness:0.3, metalness:0.8}),
  };

  const parts = assembly.parts.map((part) => {
    if (!materials[part.kind]) throw new Error(`Unknown part kind: ${part.kind}`);
    const vertices = [];
    for (let i = 0; i < part.positions.length; i += 3) {
      vertices.push(...toWorld(part.positions.slice(i, i + 3)).toArray());
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setIndex(part.indices);
    // Flat face normals preserve the sharp CAD edges without rounding box corners.
    const surface = geometry.toNonIndexed();
    surface.computeVertexNormals();
    geometry.dispose();
    const mesh = new THREE.Mesh(surface, materials[part.kind]);
    mesh.name = part.name;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    scene.add(mesh);
    return {...part, mesh};
  });

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(5000, 5000),
    new THREE.MeshStandardMaterial({color:COLORS.background, roughness:0.95, metalness:0.05}),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -175;
  ground.receiveShadow = true;
  scene.add(ground);

  const camera = new THREE.PerspectiveCamera(32, WIDTH / HEIGHT, 1, 6000);
  const phase = document.getElementById('phase');
  const originalCenter = new THREE.Vector3();

  // Animate original meshes only; their zero translation is the exact source assembly.
  function renderAt(time) {
    const t = THREE.MathUtils.clamp(time, 0, DURATION);
    const halves = separation(t, 6.1, 8.4, 13, 14.8);
    const pads = separation(t, 6.8, 8.8, 12, 13.8);
    const screws = separation(t, 4.7, 6.6, 15, 16.8);
    const inserts = separation(t, 6.2, 8, 14, 15.5);
    const macSlide = separation(t, 4, 5.5, 17.1, 18.4);
    const macLift = separation(t, 5.5, 7.5, 16.1, 17.1);
    const wide = separation(t, 4.4, 8, 14.5, 18.5);

    for (const part of parts) {
      const side = part.side === 'left' ? -1 : 1;
      const offset = new THREE.Vector3();
      if (part.kind === 'holder') {
        offset.x = side * 78 * halves;
      } else if (part.kind === 'mac') {
        offset.set(side * 30 * macLift, 172 * macLift, 164 * macSlide);
      } else if (part.kind === 'tpu') {
        offset.set(side * 78 * halves, 0, 195 * pads);
      } else {
        // Hardware withdraws along its own axis and follows its supporting half.
        const axis = directionToWorld(part.axis);
        const travel = part.kind === 'screw' ? 100 * screws : 48 * inserts;
        offset.copy(axis).multiplyScalar(-travel);
        offset.x += side * 78 * halves;
      }
      part.mesh.position.copy(offset);
    }

    const orbit = 0.36 - 0.62 * progress(t, 0, 4) + 0.38 * progress(t, 8, 12) + 0.25 * progress(t, 18.4, 20);
    const radius = 790 + wide * 220;
    camera.position.set(Math.sin(orbit) * radius, 285 + wide * 195, Math.cos(orbit) * radius);
    originalCenter.set(0, 6 + wide * 30, 20 + wide * 30);
    camera.lookAt(originalCenter);
    phase.textContent = t < 4 ? 'Assembled' : t < 8.8 ? 'Exploding' : t < 12 ? 'Exploded view' : t < 18.4 ? 'Reassembling' : 'Assembled';
    renderer.render(scene, camera);
  }

  window.addEventListener('hf-seek', (event) => renderAt(event.detail.time));
  window.renderAssemblyAt = renderAt;
  renderAt(window.__hfThreeTime ?? 0);
}

window.__hf = window.__hf || {};
window.__hf.buildReady = window.__hf.buildReady || {};
window.__hf.buildReady['rack-assembly'] = buildScene().catch((error) => {
  document.getElementById('failure').textContent = error.message;
  throw error;
});

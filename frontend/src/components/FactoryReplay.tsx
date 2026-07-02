import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

import type { StationDescriptor, VisitDto } from "../types";

// 3D factory replay of one simulation run, driven entirely by the server's
// station-level event trace. Orders are cubes: they crowd the backlog, pile up
// in queues (amber = waiting = waste), ride the stations while processed
// (blue), and stack up at the dock colored by demand-schedule punctuality.
// Primitive geometry only — asset polish (Blender→glTF) is a later slice.

interface Props {
  visits: VisitDto[];
  onTime: boolean[];
  completionTimes: number[];
  stations: StationDescriptor[];
  makespan: number;
  wipCap: number | null;
}

const SPACING = 6;
const COLOR_BACKLOG = 0x5c6773;
const COLOR_QUEUE = 0xd9a441;
const COLOR_PROCESS = 0x4d9fff;
const COLOR_ON_TIME = 0x35c48f;
const COLOR_LATE = 0xe0803a;
const SPEEDS = [8, 32, 128]; // sim time units per real second

function makeLabel(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 96;
  const context = canvas.getContext("2d")!;
  context.font = "bold 44px system-ui, sans-serif";
  context.fillStyle = "#e6edf3";
  context.textAlign = "center";
  context.fillText(text, 256, 62);
  const material = new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas),
    transparent: true,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(4.6, 0.86, 1);
  return sprite;
}

function gridSlot(rank: number, perRow: number, dx: number, dz: number) {
  return {
    row: Math.floor(rank / perRow) * dx,
    lane: (rank % perRow) * dz,
  };
}

export default function FactoryReplay({
  visits,
  onTime,
  completionTimes,
  stations,
  makespan,
  wipCap,
}: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const scrubberRef = useRef<HTMLInputElement>(null);
  const clockLabelRef = useRef<HTMLSpanElement>(null);
  const simTimeRef = useRef(0);
  const playingRef = useRef(true);
  const speedRef = useRef(SPEEDS[1]);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(SPEEDS[1]);

  playingRef.current = playing;
  speedRef.current = speed;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    // --- static scene -----------------------------------------------------
    const scene = new THREE.Scene();
    const centerX = ((stations.length - 1) * SPACING) / 2;
    const gateX = -SPACING;
    const exitX = stations.length * SPACING - SPACING / 2 + 1.5;

    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const sun = new THREE.DirectionalLight(0xffffff, 1.1);
    sun.position.set(6, 10, 6);
    scene.add(sun);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(70, 26),
      new THREE.MeshStandardMaterial({ color: 0x101820 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(centerX, -0.01, 0);
    scene.add(ground);
    const grid = new THREE.GridHelper(70, 35, 0x223040, 0x1a2530);
    grid.position.set(centerX, 0, 0);
    scene.add(grid);

    const bottleneckMean = Math.max(...stations.map((s) => s.cycle_time_mean));
    stations.forEach((station, index) => {
      const isBottleneck = station.cycle_time_mean === bottleneckMean;
      const block = new THREE.Mesh(
        new THREE.BoxGeometry(2.4, 1.3, 2.6),
        new THREE.MeshStandardMaterial({ color: isBottleneck ? 0x4a3038 : 0x2a3440 }),
      );
      block.position.set(index * SPACING, 0.65, 0);
      scene.add(block);
      const label = makeLabel(
        `${station.name} ~${station.cycle_time_mean}${isBottleneck ? " ⛔" : ""}`,
      );
      label.position.set(index * SPACING, 2.3, 0);
      scene.add(label);
    });

    // Entry gate (with the WIP cap when the scenario has one) and the dock.
    const postMaterial = new THREE.MeshStandardMaterial({ color: 0x35c48f });
    [-1.6, 1.6].forEach((z) => {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.25, 2.2, 0.25), postMaterial);
      post.position.set(gateX, 1.1, z);
      scene.add(post);
    });
    const beam = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.25, 3.45), postMaterial);
    beam.position.set(gateX, 2.2, 0);
    scene.add(beam);
    const gateLabel = makeLabel(wipCap !== null ? `Tavan ${wipCap}` : "Giriş");
    gateLabel.position.set(gateX, 3, 0);
    scene.add(gateLabel);
    const dockLabel = makeLabel("Sevkiyat");
    dockLabel.position.set(exitX + 1.5, 2.3, 0);
    scene.add(dockLabel);

    // --- orders ------------------------------------------------------------
    const byOrder = new Map<number, VisitDto[]>();
    visits.forEach((visit) => {
      const list = byOrder.get(visit.order_id) ?? [];
      list.push(visit);
      byOrder.set(visit.order_id, list);
    });
    byOrder.forEach((list) => list.sort((a, b) => a.station_index - b.station_index));
    const orderIds = [...byOrder.keys()].sort((a, b) => a - b);
    const completionRank = new Map<number, number>();
    [...orderIds]
      .sort((a, b) => completionTimes[a] - completionTimes[b])
      .forEach((id, rank) => completionRank.set(id, rank));

    const cubeGeometry = new THREE.BoxGeometry(0.48, 0.48, 0.48);
    const cubes = new Map<number, THREE.Mesh<THREE.BoxGeometry, THREE.MeshStandardMaterial>>();
    orderIds.forEach((id) => {
      const cube = new THREE.Mesh(
        cubeGeometry,
        new THREE.MeshStandardMaterial({ color: COLOR_BACKLOG }),
      );
      cube.position.set(gateX - 2, 0.24, 0);
      scene.add(cube);
      cubes.set(id, cube);
    });

    const target = new THREE.Vector3();
    function layout(t: number, snap: boolean) {
      // Per-frame membership of each dynamic area, for compact grid slots.
      const backlog: number[] = [];
      const queues = new Map<number, number[]>();
      const outbound = new Map<number, number[]>();
      orderIds.forEach((id) => {
        const trail = byOrder.get(id)!;
        if (t >= completionTimes[id]) return;
        if (t < trail[0].queued_at) {
          backlog.push(id);
          return;
        }
        for (const visit of trail) {
          const next = trail[visit.station_index + 1];
          if (t >= visit.queued_at && t < visit.started_at) {
            const q = queues.get(visit.station_index) ?? [];
            q.push(id);
            queues.set(visit.station_index, q);
            return;
          }
          if (t >= visit.started_at && t < visit.finished_at) return; // processing
          if (t >= visit.finished_at && (next ? t < next.queued_at : true)) {
            const w = outbound.get(visit.station_index) ?? [];
            w.push(id);
            outbound.set(visit.station_index, w);
            return;
          }
        }
      });
      backlog.sort((a, b) => byOrder.get(a)![0].queued_at - byOrder.get(b)![0].queued_at);
      queues.forEach((ids, s) =>
        ids.sort((a, b) => byOrder.get(a)![s].queued_at - byOrder.get(b)![s].queued_at),
      );

      orderIds.forEach((id) => {
        const cube = cubes.get(id)!;
        const trail = byOrder.get(id)!;
        let color = COLOR_BACKLOG;
        if (t >= completionTimes[id]) {
          const rank = completionRank.get(id)!;
          const slot = gridSlot(rank, 6, 0.62, 0.62);
          target.set(exitX + 0.6 + slot.row, 0.24, -1.55 + slot.lane);
          color = onTime[id] ? COLOR_ON_TIME : COLOR_LATE;
        } else if (backlog.includes(id)) {
          const slot = gridSlot(backlog.indexOf(id), 6, 0.62, 0.62);
          target.set(gateX - 1.4 - slot.row, 0.24, -1.55 + slot.lane);
          color = COLOR_BACKLOG;
        } else {
          let placed = false;
          for (const visit of trail) {
            const queue = queues.get(visit.station_index);
            if (queue && queue.includes(id)) {
              const slot = gridSlot(queue.indexOf(id), 4, 0.62, 0.62);
              target.set(visit.station_index * SPACING - 1.9 - slot.row, 0.24, -0.93 + slot.lane);
              color = COLOR_QUEUE;
              placed = true;
              break;
            }
            if (t >= visit.started_at && t < visit.finished_at) {
              target.set(visit.station_index * SPACING, 1.55, 0);
              color = COLOR_PROCESS;
              placed = true;
              break;
            }
            const waiters = outbound.get(visit.station_index);
            if (waiters && waiters.includes(id)) {
              const slot = gridSlot(waiters.indexOf(id), 4, 0.62, 0.62);
              target.set(visit.station_index * SPACING + 1.9 + slot.row, 0.24, -0.93 + slot.lane);
              color = COLOR_QUEUE;
              placed = true;
              break;
            }
          }
          if (!placed) target.set(gateX - 2, 0.24, 0);
        }
        if (snap) cube.position.copy(target);
        else cube.position.lerp(target, 0.16);
        cube.material.color.setHex(color);
      });
    }

    // --- renderer / camera / loop ------------------------------------------
    const width = mount.clientWidth || 800;
    const height = 400;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    mount.appendChild(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 200);
    camera.position.set(centerX + 2, 10, 15);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(centerX, 0.6, 0);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI / 2.05;

    const resizeObserver = new ResizeObserver(() => {
      const w = mount.clientWidth || width;
      renderer.setSize(w, height);
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
    });
    resizeObserver.observe(mount);

    const endTime = Math.max(makespan, ...completionTimes) + 2;
    if (scrubberRef.current) scrubberRef.current.max = String(endTime);
    const clock = new THREE.Clock();
    let previousTime = simTimeRef.current;
    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      if (playingRef.current) {
        simTimeRef.current = Math.min(simTimeRef.current + delta * speedRef.current, endTime);
        if (simTimeRef.current >= endTime) {
          playingRef.current = false;
          setPlaying(false);
        }
      }
      const t = simTimeRef.current;
      layout(t, Math.abs(t - previousTime) > endTime * 0.05);
      previousTime = t;
      if (scrubberRef.current) scrubberRef.current.value = String(t);
      if (clockLabelRef.current) {
        clockLabelRef.current.textContent = `t = ${t.toFixed(0)} / ${endTime.toFixed(0)}`;
      }
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        if (mesh.geometry) mesh.geometry.dispose();
        const material = (mesh as THREE.Mesh).material as THREE.Material | undefined;
        if (material) material.dispose();
      });
      mount.removeChild(renderer.domElement);
    };
    // Rebuild the whole scene when a new run arrives.
  }, [visits, onTime, completionTimes, stations, makespan, wipCap]);

  return (
    <div className="replay">
      <div ref={mountRef} className="replay__canvas" />
      <div className="replay__controls">
        <button
          className="replay__btn"
          onClick={() => {
            if (!playing && scrubberRef.current) {
              const end = Number(scrubberRef.current.max);
              if (simTimeRef.current >= end) simTimeRef.current = 0; // yeniden izle
            }
            setPlaying(!playing);
          }}
        >
          {playing ? "⏸ Duraklat" : "▶ Oynat"}
        </button>
        {SPEEDS.map((value, index) => (
          <button
            key={value}
            className={
              speed === value ? "replay__btn replay__btn--active" : "replay__btn"
            }
            onClick={() => setSpeed(value)}
          >
            ×{[1, 4, 16][index]}
          </button>
        ))}
        <input
          ref={scrubberRef}
          className="replay__scrubber"
          type="range"
          min={0}
          max={makespan}
          step={0.5}
          defaultValue={0}
          onInput={(event) => {
            simTimeRef.current = Number((event.target as HTMLInputElement).value);
          }}
        />
        <span ref={clockLabelRef} className="replay__clock" />
      </div>
      <p className="replay__legend">
        <i className="dot" style={{ background: "#5c6773" }} /> backlog ·{" "}
        <i className="dot" style={{ background: "#d9a441" }} /> kuyruk/bekleme ·{" "}
        <i className="dot" style={{ background: "#4d9fff" }} /> işleniyor ·{" "}
        <i className="dot dot--ok" /> zamanında ·{" "}
        <i className="dot dot--late" /> geç — sürükleyerek döndür, tekerlekle yaklaş.
      </p>
    </div>
  );
}

"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useTexture } from "@react-three/drei";
import { useRef } from "react";
import * as THREE from "three";


function Moon() {
  const moon = useRef<THREE.Group>(null);
  const texture = useTexture("/textures/moon.webp");

  useFrame((state, delta) => {
    if (!moon.current) return;

    moon.current.rotation.y += delta * 0.12;

    const time = state.clock.elapsedTime * 0.16;

    moon.current.position.x = Math.cos(time) * 2.65;
    moon.current.position.y = Math.sin(time) * 2.65;
  });

  return (
    <group ref={moon}>
      <mesh>
        <sphereGeometry args={[0.24, 64, 64]} />
        <meshStandardMaterial map={texture} roughness={1} />
      </mesh>

      <pointLight position={[2, 2, 3]} intensity={1.5} />
    </group>
  );
}

function Orbit() {
  return (
    <mesh>
      <ringGeometry args={[2.64, 2.67, 180]} />
      <meshBasicMaterial
        color="#6BA9D9"
        transparent
        opacity={0.45}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

export default function MoonOrbit() {
  return (
    <div className="moon-orbit">
      <Canvas camera={{ position: [0, 0, 10], fov: 45 }} gl={{ alpha: true }}>
        <ambientLight intensity={0.45} />
        <directionalLight position={[4, 4, 5]} intensity={2} />

        <Orbit />
        <Moon />
      </Canvas>
    </div>
  );
}

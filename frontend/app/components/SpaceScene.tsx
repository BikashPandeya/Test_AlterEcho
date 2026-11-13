"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { Html, Stars, useGLTF } from "@react-three/drei";

function StarField() {
  const stars = useRef<THREE.Group>(null);

  useFrame((state, delta) => {
    if (stars.current) {
      stars.current.rotation.y += delta * 0.008;
      stars.current.rotation.x += delta * 0.002;
    }
  });

  return (
    <group ref={stars}>
      <Stars
        radius={90}
        depth={55}
        count={3500}
        factor={4}
        saturation={0.4}
        fade
        speed={0.35}
      />
    </group>
  );
}

function OrbitPath() {
  const orbitRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (orbitRef.current) {
      const material = orbitRef.current.material as THREE.MeshBasicMaterial;
      material.opacity = 0.3 + Math.sin(state.clock.elapsedTime * 1.5) * 0.08;
    }
  });

  return (
    <mesh ref={orbitRef}>
      <ringGeometry args={[3.15, 3.18, 180]} />
      <meshBasicMaterial
        color="#43BFFF"
        transparent
        opacity={0.4}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}


function Moon({ onClick }: { onClick: () => void }) {
  const moonRef = useRef<THREE.Group>(null);

  const { scene } = useGLTF("/models/moon.glb");
  const moonModel = useMemo(() => scene.clone(), [scene]);

  useFrame((state, delta) => {
    if (!moonRef.current) return;

    const time = state.clock.elapsedTime * 0.22;

    moonRef.current.position.x = Math.cos(time) * 3.16;
    moonRef.current.position.y = Math.sin(time) * 3.16;

    moonRef.current.rotation.y += delta * 0.12;
  });

  return (
    <group ref={moonRef}>
      <primitive
        object={moonModel}
        scale={0.27}
      />

      <Html center>
        <button
          type="button"
          className="moon-hit-target"
          aria-label="Open Moon 3D model"
          onClick={onClick}
        />
      </Html>

      {/* Subtle lunar glow */}
      <mesh scale={1.13}>
        <sphereGeometry args={[0.27, 32, 32]} />
        <meshBasicMaterial
          color="#A9DFFF"
          transparent
          opacity={0.07}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}




export default function SpaceScene({
  onMoonClick,
  showOrbit,
}: {
  onMoonClick: () => void;
  showOrbit: boolean;
}) {
  return (
    <div className="space-scene">
      <Canvas
        camera={{ position: [0, 0, 10], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[4, 5, 5]} intensity={2} />

        {/* <Nebula /> */}
        <StarField />
        {showOrbit && <OrbitPath />}
        {showOrbit && <Moon onClick={onMoonClick} />}
      </Canvas>
    </div>
  );
}

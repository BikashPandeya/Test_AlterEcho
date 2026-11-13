
"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";

function MoonModel() {
  const moonRef = useRef<THREE.Group>(null);

  const { scene } = useGLTF("/models/moon.glb");

  // Clone and normalize the NASA model
  const moon = useMemo(() => {
    const model = scene.clone(true);

    const box = new THREE.Box3().setFromObject(model);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    model.position.sub(center);

    const maxDimension = Math.max(size.x, size.y, size.z);

    if (maxDimension > 0) {
      model.scale.setScalar(3.5 / maxDimension);
    }

    return model;
  }, [scene]);

  useFrame((_, delta) => {
    if (moonRef.current) {
      moonRef.current.rotation.y += delta * 0.025;
    }
  });

  return (
    <group ref={moonRef}>
      <primitive object={moon} />
    </group>
  );
}

function MarsModel() {
  const planetRef = useRef<THREE.Group>(null);
  const { scene } = useGLTF("/models/Mars.glb");

  const mars = useMemo(() => {
    const model = scene.clone(true);
    const bounds = new THREE.Box3().setFromObject(model);
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const maxDimension = Math.max(size.x, size.y, size.z);

    model.position.sub(center);

    if (maxDimension > 0) {
      model.scale.setScalar(3.5 / maxDimension);
    }

    return model;
  }, [scene]);

  useFrame((_, delta) => {
    if (planetRef.current) {
      planetRef.current.rotation.y += delta * 0.08;
    }
  });

  return (
    <group ref={planetRef}>
      <primitive object={mars} />
    </group>
  );
}

export default function PlanetViewer({
  planet,
}: {
  planet: "mars" | "moon";
}) {
  return (
    <div style={{ width: "100%", height: "650px" }}>
      <Canvas
        camera={{ position: [0, 0, 7], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.8} />

        <directionalLight
          position={[4, 3, 5]}
          intensity={2}
        />

        <pointLight
          position={[-4, -2, -3]}
          intensity={0.5}
          color="#8bbcff"
        />

        {planet === "moon" ? (
          <MoonModel />
        ) : (
          <MarsModel />
        )}

        <OrbitControls
          enablePan={false}
          enableZoom={true}
          minDistance={3}
          maxDistance={12}
          rotateSpeed={0.8}
        />
      </Canvas>
    </div>
  );
}

useGLTF.preload("/models/moon.glb");
useGLTF.preload("/models/Mars.glb");

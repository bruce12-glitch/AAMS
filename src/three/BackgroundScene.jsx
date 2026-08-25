import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function prefersReducedMotion() {
  return typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

const REDUCED = prefersReducedMotion()

/** Drifting particle field — cyan/violet dust. */
function ParticleField({ count = 1300 }) {
  const ref = useRef()

  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const cA = new THREE.Color('#22d3ee')
    const cB = new THREE.Color('#a78bfa')
    const mixed = new THREE.Color()

    for (let i = 0; i < count; i++) {
      const r = 6 + Math.random() * 14
      const theta = Math.random() * Math.PI * 2
      const y = (Math.random() - 0.5) * 12
      positions[i * 3] = Math.cos(theta) * r
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = Math.sin(theta) * r - 4

      mixed.copy(cA).lerp(cB, Math.random())
      colors[i * 3] = mixed.r
      colors[i * 3 + 1] = mixed.g
      colors[i * 3 + 2] = mixed.b
    }
    return { positions, colors }
  }, [count])

  useFrame((state) => {
    if (!ref.current || REDUCED) return
    const t = state.clock.elapsedTime
    ref.current.rotation.y = t * 0.02
    ref.current.position.y = Math.sin(t * 0.25) * 0.35
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.055}
        vertexColors
        transparent
        opacity={0.65}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

/** Slow-rotating wireframe core — the "face mesh" motif. */
function WireCore() {
  const outerRef = useRef()
  const innerRef = useRef()

  useFrame((state) => {
    if (REDUCED) return
    const t = state.clock.elapsedTime
    if (outerRef.current) {
      outerRef.current.rotation.y = t * 0.08
      outerRef.current.rotation.x = Math.sin(t * 0.11) * 0.18
    }
    if (innerRef.current) {
      innerRef.current.rotation.y = -t * 0.14
      innerRef.current.rotation.z = Math.cos(t * 0.09) * 0.22
    }
  })

  return (
    <group position={[0, 0, -2]}>
      <mesh ref={outerRef}>
        <icosahedronGeometry args={[3.1, 1]} />
        <meshBasicMaterial wireframe color="#22d3ee" transparent opacity={0.075} />
      </mesh>
      <mesh ref={innerRef}>
        <octahedronGeometry args={[1.7, 0]} />
        <meshBasicMaterial wireframe color="#a78bfa" transparent opacity={0.09} />
      </mesh>
    </group>
  )
}

/** Subtle mouse parallax for the whole scene. */
function ParallaxRig({ children }) {
  const ref = useRef()
  const target = useRef({ x: 0, y: 0 })

  useFrame((state) => {
    if (!ref.current) return
    target.current.x = (state.pointer.x || 0) * 0.12
    target.current.y = (state.pointer.y || 0) * 0.08
    if (REDUCED) return
    ref.current.rotation.y += (target.current.x - ref.current.rotation.y) * 0.04
    ref.current.rotation.x += (-target.current.y - ref.current.rotation.x) * 0.04
  })

  return <group ref={ref}>{children}</group>
}

export default function BackgroundScene() {
  return (
    <div className="bg-canvas" aria-hidden="true">
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [0, 0, 7], fov: 55 }}
        gl={{ antialias: false, powerPreference: 'high-performance', alpha: true }}
        style={{ background: 'transparent' }}
      >
        <ParallaxRig>
          <ParticleField />
          <WireCore />
        </ParallaxRig>
      </Canvas>
      <div className="bg-vignette" />
    </div>
  )
}

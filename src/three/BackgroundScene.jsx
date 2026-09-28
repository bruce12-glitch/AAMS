import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

function prefersReducedMotion() {
  return typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

const REDUCED = prefersReducedMotion()

/**
 * Feature-detect WebGL before touching react-three-fiber.
 * Headless browsers / VMs / locked-down sessions may have no usable
 * WebGL context. Bail early so the boundary renders nothing cleanly.
 */
function hasWebGL() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return false
  try {
    const canvas = document.createElement('canvas')
    const gl =
      canvas.getContext('webgl2') ||
      canvas.getContext('webgl') ||
      canvas.getContext('experimental-webgl')
    return Boolean(gl && typeof gl.getParameter === 'function')
  } catch {
    return false
  }
}

/**
 * Classic entrepreneurial backdrop — NOT neon sci-fi.
 *
 * Design intent (classic, clear, smooth):
 *  - Light ivory page, so everything here is faint and warm.
 *  - One soft teal mist + one soft gold mist, very low opacity.
 *  - One hairline architectural grid, barely visible.
 *  - Fine slate dust, slow drift, no additive glow, no wireframes.
 * Motion is deliberately slow (0.02–0.05 rad/s) so it reads as
 * premium / calm, not "trash" busy animation.
 */

/** Fine, slow dust — slate + muted teal, normal blending. */
function ClassicDust({ count = 380 }) {
  const ref = useRef()

  const { positions, colors } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const cA = new THREE.Color('#94a3b8') // slate
    const cB = new THREE.Color('#5fa8a0') // muted teal
    const mixed = new THREE.Color()

    for (let i = 0; i < count; i++) {
      const r = 5 + Math.random() * 13
      const theta = Math.random() * Math.PI * 2
      const y = (Math.random() - 0.5) * 11
      pos[i * 3] = Math.cos(theta) * r
      pos[i * 3 + 1] = y
      pos[i * 3 + 2] = Math.sin(theta) * r - 4

      mixed.copy(cA).lerp(cB, Math.random() * 0.55)
      col[i * 3] = mixed.r
      col[i * 3 + 1] = mixed.g
      col[i * 3 + 2] = mixed.b
    }
    return { positions: pos, colors: col }
  }, [count])

  useFrame((state) => {
    if (!ref.current || REDUCED) return
    const t = state.clock.elapsedTime
    // Barely-there drift: one slow rotation + gentle breathing.
    ref.current.rotation.y = t * 0.018
    ref.current.position.y = Math.sin(t * 0.18) * 0.22
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.042}
        vertexColors
        transparent
        opacity={0.38}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  )
}

/** Two soft institutional mists — teal (left) + gold (right). */
function SoftMists() {
  const tealRef = useRef()
  const goldRef = useRef()

  useFrame((state) => {
    if (REDUCED) return
    const t = state.clock.elapsedTime
    if (tealRef.current) {
      tealRef.current.position.y = Math.sin(t * 0.16) * 0.35
      tealRef.current.position.x = -3.4 + Math.sin(t * 0.1) * 0.25
    }
    if (goldRef.current) {
      goldRef.current.position.y = Math.cos(t * 0.13) * 0.35
      goldRef.current.position.x = 3.4 + Math.cos(t * 0.09) * 0.25
    }
  })

  return (
    <group position={[0, 0.4, -3.5]}>
      <mesh ref={tealRef} position={[-3.4, 0, 0]}>
        <sphereGeometry args={[2.6, 32, 32]} />
        <meshBasicMaterial color="#14b8a6" transparent opacity={0.05} depthWrite={false} />
      </mesh>
      <mesh ref={goldRef} position={[3.4, 0.3, -1]}>
        <sphereGeometry args={[2.2, 32, 32]} />
        <meshBasicMaterial color="#c9a86a" transparent opacity={0.055} depthWrite={false} />
      </mesh>
    </group>
  )
}

/** Hairline architectural grid — classic ledger feel. */
function ClassicGrid() {
  const ref = useRef()
  const grid = useMemo(() => {
    const g = new THREE.GridHelper(34, 34, 0xd4cfc2, 0xe7e2d4)
    g.material.transparent = true
    g.material.opacity = 0.32
    g.material.depthWrite = false
    return g
  }, [])
  useFrame((state) => {
    if (!ref.current || REDUCED) return
    // Almost static; a whisper of movement so it feels alive, not frozen.
    ref.current.position.x = Math.sin(state.clock.elapsedTime * 0.05) * 0.15
  })
  return (
    <group ref={ref} position={[0, -3.4, -4]} rotation={[Math.PI / 2.35, 0, 0]}>
      <primitive object={grid} />
    </group>
  )
}

/** Thin gold horizon line — the single "entrepreneurial" accent. */
function HorizonLine() {
  const ref = useRef()
  useFrame((state) => {
    if (!ref.current || REDUCED) return
    ref.current.position.y = -1.9 + Math.sin(state.clock.elapsedTime * 0.2) * 0.04
  })
  return (
    <mesh ref={ref} position={[0, -1.9, -2.5]}>
      <planeGeometry args={[16, 0.012]} />
      <meshBasicMaterial color="#c9a86a" transparent opacity={0.35} depthWrite={false} />
    </mesh>
  )
}

/** Subtle mouse parallax for the whole scene. */
function ParallaxRig({ children }) {
  const ref = useRef()
  const target = useRef({ x: 0, y: 0 })

  useFrame((state) => {
    if (!ref.current) return
    target.current.x = (state.pointer.x || 0) * 0.06
    target.current.y = (state.pointer.y || 0) * 0.04
    if (REDUCED) return
    ref.current.rotation.y += (target.current.x - ref.current.rotation.y) * 0.03
    ref.current.rotation.x += (-target.current.y - ref.current.rotation.x) * 0.03
  })

  return <group ref={ref}>{children}</group>
}

export default function BackgroundScene() {
  // Decorative only: hidden tab -> 'never', reduced motion -> 'demand',
  // normal -> 'always'. Keeps battery + motion-sensitive users safe.
  const [frameloop, setFrameloop] = useState(REDUCED ? 'demand' : 'always')

  useEffect(() => {
    const sync = () => {
      if (document.hidden) setFrameloop('never')
      else setFrameloop(REDUCED ? 'demand' : 'always')
    }
    sync()
    document.addEventListener('visibilitychange', sync)
    return () => document.removeEventListener('visibilitychange', sync)
  }, [])

  if (!hasWebGL()) throw new Error('WebGL not available')

  return (
    <div className="bg-canvas" aria-hidden="true">
      <Canvas
        frameloop={frameloop}
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 7], fov: 52 }}
        gl={{
          antialias: true,
          powerPreference: 'default',
          alpha: true,
          failIfMajorPerformanceCaveat: false
        }}
        fallback={null}
        style={{ background: 'transparent' }}
      >
        <ParallaxRig>
          <SoftMists />
          <ClassicGrid />
          <HorizonLine />
          <ClassicDust />
        </ParallaxRig>
      </Canvas>
      <div className="bg-vignette" />
    </div>
  )
}

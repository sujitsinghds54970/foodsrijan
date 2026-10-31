import { PropsWithChildren, useEffect, useMemo, useRef } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { analyzeCeoBehavior, BehavioralAnalyzeResponse, BehavioralMetricsPayload } from './api'

interface CeoSecurityGuardProps extends PropsWithChildren {
  enabled?: boolean
  intervalMs?: number
  onStepUpRequired?: (result: BehavioralAnalyzeResponse) => void
}

type SampleState = {
  mouseMoveCount: number
  mouseDistance: number
  mouseSpeedSum: number
  keyCount: number
  keyIntervals: number[]
  scrollCount: number
  scrollDelta: number
  scrollBursts: number[]
}

const createEmptyState = (): SampleState => ({
  mouseMoveCount: 0,
  mouseDistance: 0,
  mouseSpeedSum: 0,
  keyCount: 0,
  keyIntervals: [],
  scrollCount: 0,
  scrollDelta: 0,
  scrollBursts: [],
})

const average = (values: number[]) => {
  if (values.length === 0) return 0
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

const variance = (values: number[]) => {
  if (values.length <= 1) return 0
  const mean = average(values)
  return values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length
}

export default function CeoSecurityGuard({ children, enabled = true, intervalMs = 10000, onStepUpRequired }: CeoSecurityGuardProps) {
  const { user, token } = useAuth()
  const sampleRef = useRef<SampleState>(createEmptyState())
  const lastMouseRef = useRef<{ x: number; y: number; t: number } | null>(null)
  const lastKeyTsRef = useRef<number | null>(null)
  const lastScrollTsRef = useRef<number | null>(null)
  const inFlightRef = useRef(false)
  const lastToastTimeRef = useRef<number>(0)
  const TOAST_COOLDOWN_MS = 5 * 60 * 1000 // 5 minutes
  const isSuperAdmin = useMemo(
    () => Boolean(user?.is_super_admin || (user?.role || '').trim().toLowerCase() === 'super_admin' || (user?.role || '').trim().toLowerCase() === 'super_ceo'),
    [user],
  )

  useEffect(() => {
    if (!enabled || !token || !isSuperAdmin) {
      sampleRef.current = createEmptyState()
      return
    }

    const handleMouseMove = (event: MouseEvent) => {
      const now = Date.now()
      const state = sampleRef.current
      state.mouseMoveCount += 1
      if (lastMouseRef.current) {
        const dx = event.clientX - lastMouseRef.current.x
        const dy = event.clientY - lastMouseRef.current.y
        const dt = Math.max(now - lastMouseRef.current.t, 1)
        const distance = Math.sqrt(dx ** 2 + dy ** 2)
        state.mouseDistance += distance
        state.mouseSpeedSum += distance / dt
      }
      lastMouseRef.current = { x: event.clientX, y: event.clientY, t: now }
    }

    const handleKeyDown = () => {
      const now = Date.now()
      const state = sampleRef.current
      state.keyCount += 1
      if (lastKeyTsRef.current !== null) {
        state.keyIntervals.push(now - lastKeyTsRef.current)
      }
      lastKeyTsRef.current = now
    }

    const handleScroll = () => {
      const now = Date.now()
      const state = sampleRef.current
      const currentY = Math.abs(window.scrollY || 0)
      state.scrollCount += 1
      state.scrollDelta += currentY
      if (lastScrollTsRef.current !== null) {
        state.scrollBursts.push(now - lastScrollTsRef.current)
      }
      lastScrollTsRef.current = now
    }

    const flushSample = async () => {
      if (inFlightRef.current) return
      const snapshot = sampleRef.current
      if (snapshot.mouseMoveCount === 0 && snapshot.keyCount === 0 && snapshot.scrollCount === 0) {
        return
      }

      const payload: BehavioralMetricsPayload = {
        sample_window_seconds: Math.max(5, Math.round(intervalMs / 1000)),
        mouse: {
          move_count: snapshot.mouseMoveCount,
          total_distance: Number(snapshot.mouseDistance.toFixed(2)),
          average_speed: Number((snapshot.mouseSpeedSum / Math.max(snapshot.mouseMoveCount, 1)).toFixed(4)),
        },
        keystroke: {
          key_count: snapshot.keyCount,
          average_interval_ms: Number(average(snapshot.keyIntervals).toFixed(2)),
          rhythm_variance_ms: Number(variance(snapshot.keyIntervals).toFixed(2)),
        },
        scroll: {
          event_count: snapshot.scrollCount,
          total_delta: Number(snapshot.scrollDelta.toFixed(2)),
          average_burst: Number(average(snapshot.scrollBursts).toFixed(2)),
        },
      }

      sampleRef.current = createEmptyState()
      inFlightRef.current = true
      try {
        const result = await analyzeCeoBehavior(payload)
        if (result.step_up_required) {
          // Only show toast if cooldown has passed
          const now = Date.now()
          if (now - lastToastTimeRef.current > TOAST_COOLDOWN_MS) {
            toast.error(result.message || 'CEO step-up authentication required')
            lastToastTimeRef.current = now
          }
          onStepUpRequired?.(result)
        }
      } catch {
        // Silent by design to avoid degrading the protected workflow on transient network issues.
      } finally {
        inFlightRef.current = false
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('scroll', handleScroll, { passive: true })
    const timer = window.setInterval(() => {
      void flushSample()
    }, intervalMs)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('scroll', handleScroll)
      window.clearInterval(timer)
      void flushSample()
    }
  }, [enabled, intervalMs, isSuperAdmin, onStepUpRequired, token, TOAST_COOLDOWN_MS])

  return <>{children}</>
}
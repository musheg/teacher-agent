import { useMemo } from 'react'

/**
 * Generic SVG canvas driven by a frames timeline.
 * Each op is one of:
 *   {op:'add', id, kind:'circle'|'rect'|'text', x, y, r?, w?, h?, text?, fill?}
 *   {op:'move', id, x, y}
 *   {op:'remove', id}
 */
export default function AnimationTimeline({ spec, currentMs }) {
  const objects = useMemo(() => {
    const state = new Map()
    for (const obj of spec.initial_objects || []) {
      state.set(obj.id, { ...obj })
    }
    for (const f of spec.frames || []) {
      if (currentMs < f.t_ms) break
      for (const op of f.ops || []) {
        if (op.op === 'add') state.set(op.id, { ...op })
        else if (op.op === 'remove') state.delete(op.id)
        else if (op.op === 'move') {
          const o = state.get(op.id)
          if (o) state.set(op.id, { ...o, x: op.x, y: op.y })
        }
      }
    }
    return Array.from(state.values())
  }, [spec, currentMs])

  return (
    <svg viewBox={`0 0 ${spec.width || 600} ${spec.height || 400}`} className="animation-canvas">
      {objects.map((o) => {
        if (o.kind === 'circle') return <circle key={o.id} cx={o.x} cy={o.y} r={o.r || 16} fill={o.fill || '#3b82f6'} />
        if (o.kind === 'rect') return <rect key={o.id} x={o.x} y={o.y} width={o.w || 30} height={o.h || 30} fill={o.fill || '#3b82f6'} rx="3" />
        if (o.kind === 'text') return <text key={o.id} x={o.x} y={o.y} fill={o.fill || 'currentColor'} fontSize="16">{o.text}</text>
        return null
      })}
    </svg>
  )
}

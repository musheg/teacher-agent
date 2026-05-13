import { useEffect, useRef } from 'react'

export default function Geometry({ spec }) {
  const ref = useRef(null)

  useEffect(() => {
    let board
    let cancelled = false
    ;(async () => {
      const mod = await import('jsxgraph')
      if (cancelled) return
      const JXG = mod.default || mod
      const [xmin, ymax, xmax, ymin] = spec.bounds || [-5, 5, 5, -5]
      const el = ref.current
      if (!el) return
      el.innerHTML = ''
      const inner = document.createElement('div')
      inner.id = `jxg-geo-${Math.random().toString(36).slice(2)}`
      inner.style.width = '100%'
      inner.style.height = '360px'
      el.appendChild(inner)
      board = JXG.JSXGraph.initBoard(inner.id, {
        boundingbox: [xmin, ymax, xmax, ymin],
        axis: true, showCopyright: false, showNavigation: false,
      })
      const objects = {}
      for (const c of spec.constructions || []) {
        const argRefs = (c.args || []).map((a) => (typeof a === 'string' && objects[a]) ? objects[a] : a)
        const obj = board.create(c.op === 'segment' ? 'segment' : c.op, argRefs, c.style || {})
        if (c.id) objects[c.id] = obj
      }
    })()
    return () => { cancelled = true; if (board) board.destroy?.() }
  }, [spec])

  return <div ref={ref} className="geometry" />
}

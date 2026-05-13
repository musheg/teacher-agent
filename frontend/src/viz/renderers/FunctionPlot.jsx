import { useEffect, useRef } from 'react'

export default function FunctionPlot({ spec }) {
  const ref = useRef(null)

  useEffect(() => {
    let board
    let cancelled = false
    ;(async () => {
      const mod = await import('jsxgraph')
      if (cancelled) return
      const JXG = mod.default || mod
      const xMin = spec.x_min ?? -10, xMax = spec.x_max ?? 10
      const yMin = spec.y_min ?? -10, yMax = spec.y_max ?? 10
      const el = ref.current
      if (!el) return
      el.innerHTML = ''
      const inner = document.createElement('div')
      inner.id = `jxgbox-${Math.random().toString(36).slice(2)}`
      inner.style.width = '100%'
      inner.style.height = '360px'
      el.appendChild(inner)
      board = JXG.JSXGraph.initBoard(inner.id, {
        boundingbox: [xMin, yMax, xMax, yMin],
        axis: true,
        showCopyright: false,
        showNavigation: false,
      })
      const fnSrc = (spec.expression || 'x').replace(/\^/g, '**')
      // eslint-disable-next-line no-new-func
      const fn = new Function(spec.variable || 'x', `return ${fnSrc}`)
      board.create('functiongraph', [fn, xMin, xMax], { strokeWidth: 2 })
      ;(spec.markers || []).forEach((m) => {
        if (m.x !== undefined && m.y !== undefined) {
          board.create('point', [m.x, m.y], { name: m.label || '', size: 4, color: m.color || '#3b82f6' })
        }
      })
    })()
    return () => { cancelled = true; if (board) board.destroy?.() }
  }, [spec])

  return <div ref={ref} className="function-plot" />
}

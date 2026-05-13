import { useEffect, useRef } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

export default function EquationSteps({ spec, currentMs }) {
  const refs = useRef([])

  useEffect(() => {
    spec.steps.forEach((s, i) => {
      const el = refs.current[i]
      if (!el) return
      try {
        katex.render(s.latex, el, { throwOnError: false, displayMode: true })
      } catch {
        el.textContent = s.latex
      }
    })
  }, [spec])

  // Reveal steps progressively if frames are provided.
  const stepRevealCount = (() => {
    if (!spec.frames?.length) return spec.steps.length
    let revealed = 0
    spec.frames.forEach((f) => {
      if (currentMs >= f.t_ms) revealed = Math.max(revealed, (f.ops?.[0]?.step ?? 0) + 1)
    })
    return revealed || 1
  })()

  return (
    <ol className="equation-steps">
      {spec.steps.slice(0, stepRevealCount).map((s, i) => (
        <li key={i} className="equation-step">
          <div ref={(el) => (refs.current[i] = el)} />
          {s.explanation && <div className="step-explanation">{s.explanation}</div>}
        </li>
      ))}
    </ol>
  )
}

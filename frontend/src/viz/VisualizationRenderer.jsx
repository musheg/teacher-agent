import { useEffect, useMemo, useState } from 'react'
import NumberLine from './renderers/NumberLine.jsx'
import FractionPie from './renderers/FractionPie.jsx'
import EquationSteps from './renderers/EquationSteps.jsx'
import FunctionPlot from './renderers/FunctionPlot.jsx'
import Geometry from './renderers/Geometry.jsx'
import BarChart from './renderers/BarChart.jsx'
import AnimationTimeline from './renderers/AnimationTimeline.jsx'

/**
 * Renders a VisualizationSpec emitted by the backend. The optional `frames`
 * timeline is synchronized to `ttsStartedAt` (a performance.now() timestamp).
 */
export default function VisualizationRenderer({ spec, ttsStartedAt }) {
  const [currentMs, setCurrentMs] = useState(0)

  // Drive a per-RAF clock relative to TTS start so each renderer can act on frames.
  useEffect(() => {
    if (!ttsStartedAt) return
    let raf
    const tick = () => {
      setCurrentMs(Math.max(0, performance.now() - ttsStartedAt))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [ttsStartedAt])

  const inner = useMemo(() => {
    if (!spec) return <div className="viz-empty">A picture will appear here when we talk.</div>
    switch (spec.kind) {
      case 'number_line':       return <NumberLine spec={spec} currentMs={currentMs} />
      case 'fraction_pie':      return <FractionPie spec={spec} currentMs={currentMs} />
      case 'equation_steps':    return <EquationSteps spec={spec} currentMs={currentMs} />
      case 'function_plot':     return <FunctionPlot spec={spec} currentMs={currentMs} />
      case 'geometry':          return <Geometry spec={spec} currentMs={currentMs} />
      case 'bar_chart':         return <BarChart spec={spec} currentMs={currentMs} />
      case 'animation_timeline':return <AnimationTimeline spec={spec} currentMs={currentMs} />
      default:                  return <div className="viz-empty">Unknown viz kind: {spec.kind}</div>
    }
  }, [spec, currentMs])

  return (
    <div className="viz-renderer">
      {spec?.title && <h3 className="viz-title">{spec.title}</h3>}
      <div className="viz-canvas">{inner}</div>
      {spec?.caption && <p className="viz-caption">{spec.caption}</p>}
    </div>
  )
}

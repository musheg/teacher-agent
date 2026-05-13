export default function FractionPie({ spec }) {
  const { numerator, denominator } = spec
  const cx = 150, cy = 150, r = 130
  const slices = []
  for (let i = 0; i < denominator; i++) {
    const a0 = (i / denominator) * 2 * Math.PI - Math.PI / 2
    const a1 = ((i + 1) / denominator) * 2 * Math.PI - Math.PI / 2
    const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0)
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1)
    const large = a1 - a0 > Math.PI ? 1 : 0
    slices.push({
      i,
      d: `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`,
      filled: i < numerator,
    })
  }
  return (
    <div className="fraction-pie">
      <svg viewBox="0 0 300 300">
        {slices.map((s) => (
          <path key={s.i} d={s.d}
            fill={s.filled ? (spec.color_filled || '#3b82f6') : (spec.color_empty || '#1c1c1e')}
            stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" />
        ))}
      </svg>
      <div className="fraction-label">
        {spec.label_numerator ?? numerator}/{spec.label_denominator ?? denominator}
      </div>
    </div>
  )
}

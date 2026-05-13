export default function BarChart({ spec }) {
  const W = 600, H = 320, PAD = 40
  const max = Math.max(...spec.values)
  const barW = (W - 2 * PAD) / spec.categories.length - 8

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="bar-chart">
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="currentColor" />
      {spec.values.map((v, i) => {
        const x = PAD + i * ((W - 2 * PAD) / spec.values.length) + 4
        const h = ((H - 2 * PAD) * v) / (max || 1)
        const y = H - PAD - h
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={h} fill="#3b82f6" rx="3" />
            <text x={x + barW / 2} y={H - PAD + 18} textAnchor="middle" fontSize="12">{spec.categories[i]}</text>
            <text x={x + barW / 2} y={y - 6} textAnchor="middle" fontSize="11" fill="#bdd4ec">{v}</text>
          </g>
        )
      })}
    </svg>
  )
}

export default function NumberLine({ spec }) {
  const { start, end, step = 1, marks = [], highlight_intervals = [] } = spec
  const W = 600, H = 120, PAD = 30
  const range = end - start
  const x = (v) => PAD + ((v - start) / range) * (W - 2 * PAD)

  const ticks = []
  for (let v = start; v <= end + 1e-9; v += step) ticks.push(v)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="number-line">
      {highlight_intervals.map(([a, b], i) => (
        <rect key={i} x={x(a)} y={H/2 - 18} width={x(b) - x(a)} height={36}
          fill="rgba(56,130,246,0.18)" rx="4" />
      ))}
      <line x1={PAD} y1={H/2} x2={W - PAD} y2={H/2} stroke="currentColor" strokeWidth="2" />
      {ticks.map((v) => (
        <g key={v}>
          <line x1={x(v)} y1={H/2 - 6} x2={x(v)} y2={H/2 + 6} stroke="currentColor" strokeWidth="1.5" />
          <text x={x(v)} y={H/2 + 24} textAnchor="middle" fontSize="13" fill="currentColor">{v}</text>
        </g>
      ))}
      {marks.map((m, i) => (
        <g key={`m${i}`}>
          <circle cx={x(m.value)} cy={H/2} r="7" fill={m.color || '#3b82f6'} />
          {m.label && <text x={x(m.value)} y={H/2 - 14} textAnchor="middle" fontSize="13" fill={m.color || '#3b82f6'}>{m.label}</text>}
        </g>
      ))}
    </svg>
  )
}

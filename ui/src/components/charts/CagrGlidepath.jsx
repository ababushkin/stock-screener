// CAGR glidepath chart — trailing-3y CAGR → Y1..Y5 projected CAGR per scenario.
// Pure SVG, no chart dependency. Mounted from ModelReport only for ESTABLISHED
// runs (method does NOT start with "pre-profit").

const SCENARIOS = [
  { key: 'bear', label: 'Bear', color: '#c62828' },
  { key: 'base', label: 'Base', color: '#1565c0' },
  { key: 'bull', label: 'Bull', color: '#2e7d32' }
];

// X positions: trailing CAGR + Y1..Y5
const X_LABELS = ['trailing 3y', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5'];

const WIDTH = 640;
const HEIGHT = 220;
const PAD_LEFT = 56;
const PAD_RIGHT = 72;
const PAD_TOP = 16;
const PAD_BOTTOM = 32;

function formatPct(value, digits = 1) {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

function capFootnote(growthRate) {
  if (!growthRate || growthRate.cap_applied !== true) return null;
  const trailing = growthRate.trailing_3y_cagr;
  const applied = growthRate.applied_base_cagr;
  const source = growthRate.cap_source ?? 'unknown';
  // Canonical phrasing: "capped from <trailing>% by <source> (<applied>%)"
  return `Base-case Y2–Y5 CAGR capped from ${formatPct(trailing)} by ${source} (${formatPct(applied)}).`;
}

export default function CagrGlidepath({ model }) {
  if (!model) return null;
  const method = typeof model.method === 'string' ? model.method : '';
  if (method.startsWith('pre-profit')) return null;

  const fcfTtm = model.fcf_ttm;
  const fcfNormalized = model.fcf_normalized;
  const scenarios = model.scenarios ?? {};
  const growthRate = model.growth_rate ?? {};
  const trailing = growthRate.trailing_3y_cagr;
  const hasTrailing = trailing != null && Number.isFinite(trailing);

  // Y1 anchor: prefer fcf_normalized if positive (handles capex-distorted TTM like AMZN),
  // fall back to fcf_ttm if positive, else null → skip Y1 to avoid nonsensical growth rate.
  const y1Anchor =
    (fcfNormalized != null && Number.isFinite(fcfNormalized) && fcfNormalized > 0)
      ? fcfNormalized
      : (Number.isFinite(fcfTtm) && fcfTtm > 0)
        ? fcfTtm
        : null;

  // Build series: [trailing?, y1?, y2, y3, y4, y5] per scenario. Drop the
  // trailing column entirely when growth_rate.trailing_3y_cagr is missing
  // (older pre-v1.11 reports), so we never plot NaN. Drop Y1 when y1Anchor
  // is null (negative TTM and no normalised alternative).
  const series = SCENARIOS.map(({ key, label, color }) => {
    const s = scenarios[key];
    if (!s || !Number.isFinite(s.y1_fcf) || !Number.isFinite(s.y2_5_cagr)) {
      return null;
    }
    const y25Cagr = s.y2_5_cagr;
    if (y1Anchor !== null) {
      const y1Cagr = s.y1_fcf / y1Anchor - 1;
      const points = hasTrailing
        ? [trailing, y1Cagr, y25Cagr, y25Cagr, y25Cagr, y25Cagr]
        : [y1Cagr, y25Cagr, y25Cagr, y25Cagr, y25Cagr];
      return { key, label, color, points };
    }
    // Y1 anchor unavailable — skip Y1 point
    const points = hasTrailing
      ? [trailing, y25Cagr, y25Cagr, y25Cagr, y25Cagr]
      : [y25Cagr, y25Cagr, y25Cagr, y25Cagr];
    return { key, label, color, points };
  }).filter(Boolean);

  if (series.length === 0) return null;

  const baseLabels = hasTrailing ? X_LABELS : X_LABELS.slice(1);
  const xLabels = y1Anchor !== null ? baseLabels : baseLabels.filter((l) => l !== 'Y1');

  // Y-axis domain: include trailing + all scenario points, pad 10%
  const allValues = series.flatMap((s) => s.points).filter((v) => v != null && Number.isFinite(v));
  if (allValues.length === 0) return null;

  let yMin = Math.min(0, ...allValues);
  let yMax = Math.max(...allValues);
  if (yMin === yMax) yMax = yMin + 0.1;
  const yPad = (yMax - yMin) * 0.1;
  yMin -= yPad;
  yMax += yPad;

  const plotW = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotH = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const xStep = xLabels.length > 1 ? plotW / (xLabels.length - 1) : 0;

  const xAt = (i) => PAD_LEFT + i * xStep;
  const yAt = (v) => PAD_TOP + plotH * (1 - (v - yMin) / (yMax - yMin));

  // Y-axis ticks: choose 4 ticks across the domain
  const tickCount = 4;
  const ticks = [];
  for (let i = 0; i <= tickCount; i += 1) {
    const v = yMin + ((yMax - yMin) * i) / tickCount;
    ticks.push(v);
  }

  // Zero baseline (when domain straddles 0)
  const zeroLine = yMin < 0 && yMax > 0 ? yAt(0) : null;

  const footnote = capFootnote(growthRate);

  return (
    <div className="chart-block">
      <div className="chart-title">CAGR glidepath</div>
      <div className="chart-legend">
        {SCENARIOS.map(({ key, label, color }) => (
          <span key={key} className="legend-item">
            <span className="legend-swatch" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
      <svg
        className="chart-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="CAGR glidepath chart"
      >
        {/* Y gridlines + tick labels */}
        {ticks.map((t, i) => (
          <g key={`tick-${i}`}>
            <line
              x1={PAD_LEFT}
              x2={WIDTH - PAD_RIGHT}
              y1={yAt(t)}
              y2={yAt(t)}
              stroke="#eee"
              strokeWidth="1"
            />
            <text
              x={PAD_LEFT - 8}
              y={yAt(t)}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize="11"
              fill="#777"
            >
              {formatPct(t, 0)}
            </text>
          </g>
        ))}

        {/* Zero baseline */}
        {zeroLine != null && (
          <line
            x1={PAD_LEFT}
            x2={WIDTH - PAD_RIGHT}
            y1={zeroLine}
            y2={zeroLine}
            stroke="#bbb"
            strokeWidth="1"
            strokeDasharray="3 3"
          />
        )}

        {/* X-axis tick labels */}
        {xLabels.map((label, i) => (
          <text
            key={`xlbl-${i}`}
            x={xAt(i)}
            y={HEIGHT - PAD_BOTTOM + 16}
            textAnchor="middle"
            fontSize="11"
            fill="#777"
          >
            {label}
          </text>
        ))}

        {/* Series lines + point markers */}
        {series.map((s) => {
          const d = s.points
            .map((v, i) => `${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(2)},${yAt(v).toFixed(2)}`)
            .join(' ');
          return (
            <g key={s.key}>
              <path d={d} fill="none" stroke={s.color} strokeWidth="2" />
              {s.points.map((v, i) => (
                <circle
                  key={`pt-${i}`}
                  cx={xAt(i)}
                  cy={yAt(v)}
                  r="3"
                  fill={s.color}
                />
              ))}
            </g>
          );
        })}

        {/* Y5 endpoint labels — collapse when all scenarios converge within 2pp */}
        {(() => {
          const CONVERGE_THRESHOLD = 0.02;
          const MIN_SEP = 14; // px
          const lastIdx = series[0].points.length - 1;
          const lx = xAt(lastIdx) + 8;
          const items = series.map((s) => ({
            key: s.key,
            color: s.color,
            value: s.points[lastIdx],
            rawY: yAt(s.points[lastIdx]),
          }));
          const vals = items.map((it) => it.value);
          const spread = Math.max(...vals) - Math.min(...vals);
          if (spread <= CONVERGE_THRESHOLD) {
            const avgY = items.reduce((sum, it) => sum + it.rawY, 0) / items.length;
            const avgVal = vals.reduce((a, b) => a + b, 0) / vals.length;
            return (
              <text
                x={lx}
                y={avgY}
                dominantBaseline="middle"
                fontSize="11"
                fill="#555"
                fontWeight="600"
              >
                {`all ≈ ${formatPct(avgVal)}`}
              </text>
            );
          }
          // Collision avoidance: sort by rawY, push apart by MIN_SEP
          const adj = [...items]
            .sort((a, b) => a.rawY - b.rawY)
            .map((it) => ({ ...it, adjY: it.rawY }));
          for (let i = 1; i < adj.length; i += 1) {
            if (adj[i].adjY - adj[i - 1].adjY < MIN_SEP) {
              adj[i].adjY = adj[i - 1].adjY + MIN_SEP;
            }
          }
          return adj.map((it) => (
            <g key={it.key}>
              {Math.abs(it.adjY - it.rawY) > 3 && (
                <line
                  x1={lx - 4}
                  y1={it.rawY}
                  x2={lx - 4}
                  y2={it.adjY}
                  stroke={it.color}
                  strokeWidth="0.7"
                  strokeOpacity="0.5"
                />
              )}
              <text
                x={lx}
                y={it.adjY}
                dominantBaseline="middle"
                fontSize="11"
                fill={it.color}
                fontWeight="600"
              >
                {formatPct(it.value)}
              </text>
            </g>
          ));
        })()}
      </svg>
      <p className="chart-caption">How fast the model thinks FCF compounds — and where the consensus/fallback ceiling clamps it.</p>
      {footnote && <p className="chart-footnote">{footnote}</p>}
    </div>
  );
}

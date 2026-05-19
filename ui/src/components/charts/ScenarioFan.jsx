// Scenario fan chart — Y1..Y5 FCF/share per bear/base/bull, with per-share
// terminal IV diamond markers and a horizontal current-price reference line.
// Single per-share axis across the whole chart.

const SCENARIOS = [
  { key: 'bear', label: 'Bear', color: '#c62828' },
  { key: 'base', label: 'Base', color: '#1565c0' },
  { key: 'bull', label: 'Bull', color: '#2e7d32' }
];

const Y_LABELS = ['Y1', 'Y2', 'Y3', 'Y4', 'Y5'];

const WIDTH = 640;
const HEIGHT = 260;
const PAD_LEFT = 64;
const PAD_RIGHT = 80;
const PAD_TOP = 16;
const PAD_BOTTOM = 32;

const CURRENT_COLOR = '#1a1a1a';

function formatDollar(value, digits = 2) {
  if (value == null || !Number.isFinite(value)) return '—';
  const n = Number(value);
  if (Math.abs(n) >= 1000) return `$${n.toFixed(0)}`;
  return `$${n.toFixed(digits)}`;
}

export default function ScenarioFan({ model }) {
  if (!model) return null;
  const method = typeof model.method === 'string' ? model.method : '';
  if (method.startsWith('pre-profit')) return null;

  const shares = model.shares_diluted;
  const currentPrice = model.current_price;
  const scenarios = model.scenarios ?? {};
  if (
    shares == null ||
    !Number.isFinite(shares) ||
    shares <= 0
  ) {
    return null;
  }

  // Build per-share FCF series for each scenario.
  const series = SCENARIOS.map(({ key, label, color }) => {
    const s = scenarios[key];
    if (!s || !Number.isFinite(s.y1_fcf) || !Number.isFinite(s.y2_5_cagr)) {
      return null;
    }
    const y1ps = s.y1_fcf / shares;
    const points = [y1ps];
    let running = y1ps;
    for (let i = 0; i < 4; i += 1) {
      running *= 1 + s.y2_5_cagr;
      points.push(running);
    }
    return {
      key,
      label,
      color,
      points,
      iv: Number.isFinite(s.intrinsic_value_per_share)
        ? s.intrinsic_value_per_share
        : null
    };
  }).filter(Boolean);

  if (series.length === 0) return null;

  // Collect all values that need to fit on the axis.
  const fanValues = series.flatMap((s) => s.points);
  const ivValues = series.map((s) => s.iv).filter((v) => v != null);
  const refValues = Number.isFinite(currentPrice) ? [currentPrice] : [];
  const allValues = [...fanValues, ...ivValues, ...refValues];
  if (allValues.length === 0) return null;

  let yMin = Math.min(0, ...allValues);
  let yMax = Math.max(...allValues);
  if (yMin === yMax) yMax = yMin + 1;
  const yPad = (yMax - yMin) * 0.08;
  yMin -= yPad;
  yMax += yPad;

  const plotW = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotH = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const xStep = plotW / (Y_LABELS.length - 1);

  const xAt = (i) => PAD_LEFT + i * xStep;
  const yAt = (v) => PAD_TOP + plotH * (1 - (v - yMin) / (yMax - yMin));

  const tickCount = 5;
  const ticks = [];
  for (let i = 0; i <= tickCount; i += 1) {
    ticks.push(yMin + ((yMax - yMin) * i) / tickCount);
  }

  // Current-price line position
  const currentY = Number.isFinite(currentPrice) ? yAt(currentPrice) : null;

  // Diamond size
  const DIAMOND = 6;

  return (
    <div className="chart-block">
      <div className="chart-title">Scenario fan (per share)</div>
      <div className="chart-legend">
        {SCENARIOS.map(({ key, label, color }) => (
          <span key={key} className="legend-item">
            <span className="legend-swatch" style={{ background: color }} />
            {label}
          </span>
        ))}
        <span className="legend-item">
          <span
            className="legend-swatch"
            style={{ background: CURRENT_COLOR, height: '2px', marginTop: '5px' }}
          />
          Current price
        </span>
        <span className="legend-item">
          <span className="legend-swatch legend-diamond" />
          Terminal IV
        </span>
      </div>
      <svg
        className="chart-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Scenario fan chart"
      >
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
              {formatDollar(t, 0)}
            </text>
          </g>
        ))}

        {Y_LABELS.map((label, i) => (
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

        {/* Current-price reference line */}
        {currentY != null && (
          <g>
            <line
              x1={PAD_LEFT}
              x2={WIDTH - PAD_RIGHT}
              y1={currentY}
              y2={currentY}
              stroke={CURRENT_COLOR}
              strokeWidth="1.5"
              strokeDasharray="6 4"
            />
            <text
              x={WIDTH - PAD_RIGHT + 6}
              y={currentY}
              dominantBaseline="middle"
              fontSize="11"
              fontWeight="600"
              fill={CURRENT_COLOR}
            >
              {formatDollar(currentPrice)}
            </text>
          </g>
        )}

        {/* Fan lines */}
        {series.map((s) => {
          const d = s.points
            .map((v, i) => `${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(2)},${yAt(v).toFixed(2)}`)
            .join(' ');
          return (
            <g key={`fan-${s.key}`}>
              <path d={d} fill="none" stroke={s.color} strokeWidth="2" />
              {s.points.map((v, i) => (
                <circle
                  key={`fpt-${s.key}-${i}`}
                  cx={xAt(i)}
                  cy={yAt(v)}
                  r="2.5"
                  fill={s.color}
                />
              ))}
            </g>
          );
        })}

        {/* Terminal IV diamond markers + value labels at Y5 */}
        {series.map((s) => {
          if (s.iv == null) return null;
          const cx = xAt(Y_LABELS.length - 1);
          const cy = yAt(s.iv);
          const diamond = `${cx},${cy - DIAMOND} ${cx + DIAMOND},${cy} ${cx},${cy + DIAMOND} ${cx - DIAMOND},${cy}`;
          return (
            <g key={`iv-${s.key}`}>
              <polygon
                points={diamond}
                fill={s.color}
                stroke="#fff"
                strokeWidth="1.5"
              />
              <text
                x={cx + DIAMOND + 6}
                y={cy}
                dominantBaseline="middle"
                fontSize="11"
                fontWeight="600"
                fill={s.color}
              >
                {formatDollar(s.iv)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

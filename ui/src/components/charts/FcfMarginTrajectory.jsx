// FCF margin trajectory chart — surfaces the "base case assumes today's clean
// FCF margin holds flat" assumption.
//
// X-axis: 3y history (oldest → newest) → TTM → Y1..Y5 flat at fcf_margin_ttm.
// Two thin lines (clean vs reported); SBC drag = shaded area between them.

const WIDTH = 640;
const HEIGHT = 220;
const PAD_LEFT = 56;
const PAD_RIGHT = 56;
const PAD_TOP = 16;
const PAD_BOTTOM = 32;

const CLEAN_COLOR = '#1565c0';
const REPORTED_COLOR = '#9c27b0';
const DRAG_FILL = 'rgba(156, 39, 176, 0.12)';

const FALLBACK_NOTE = '3y history unavailable — re-run /stock-model with v1.11+ for trajectory.';

function formatPct(value, digits = 1) {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

function shortYear(year) {
  if (!year) return '';
  // year format: "YYYY-MM-DD"
  return String(year).slice(0, 4);
}

export default function FcfMarginTrajectory({ model }) {
  if (!model) return null;
  const method = typeof model.method === 'string' ? model.method : '';
  if (method.startsWith('pre-profit')) return null;

  const cleanTtm = model.fcf_margin_ttm;
  const reportedTtm = model.fcf_margin_ttm_reported;
  if (cleanTtm == null && reportedTtm == null) return null;

  const historical = Array.isArray(model.historical_fcf_margins)
    ? model.historical_fcf_margins
    : [];

  // historical_fcf_margins[] is newest-first in the schema. Reverse so x-axis
  // moves past → future. Exclude the TTM-year row to avoid double-counting
  // (TTM is its own anchor between history and projection).
  const histAsc = [...historical].reverse();
  // Drop the newest historical entry if it duplicates TTM (same fiscal-year
  // value as fcf_margin_ttm). We compare by clean margin within epsilon.
  let histTrimmed = histAsc;
  if (histAsc.length > 0 && cleanTtm != null) {
    const last = histAsc[histAsc.length - 1];
    if (
      last.fcf_margin_clean != null &&
      Math.abs(last.fcf_margin_clean - cleanTtm) < 1e-6
    ) {
      histTrimmed = histAsc.slice(0, -1);
    }
  }

  const hasHistory = histTrimmed.length > 0;

  // Build the canonical x-axis labels and a points array per series.
  // Columns: [hist...n], 'TTM', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5'
  const histLabels = histTrimmed.map((h) => shortYear(h.year));
  const projLabels = ['TTM', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5'];
  const xLabels = [...histLabels, ...projLabels];

  const cleanPoints = [
    ...histTrimmed.map((h) =>
      h.fcf_margin_clean != null ? h.fcf_margin_clean : null
    ),
    cleanTtm ?? null,
    cleanTtm ?? null,
    cleanTtm ?? null,
    cleanTtm ?? null,
    cleanTtm ?? null,
    cleanTtm ?? null
  ];
  const reportedPoints = [
    ...histTrimmed.map((h) =>
      h.fcf_margin_reported != null ? h.fcf_margin_reported : null
    ),
    reportedTtm ?? null,
    reportedTtm ?? null,
    reportedTtm ?? null,
    reportedTtm ?? null,
    reportedTtm ?? null,
    reportedTtm ?? null
  ];

  const allValues = [...cleanPoints, ...reportedPoints].filter(
    (v) => v != null && Number.isFinite(v)
  );
  if (allValues.length === 0) return null;

  let yMin = Math.min(0, ...allValues);
  let yMax = Math.max(...allValues);
  if (yMin === yMax) yMax = yMin + 0.1;
  const yPad = (yMax - yMin) * 0.1;
  yMin -= yPad;
  yMax += yPad;

  const plotW = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotH = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const colCount = xLabels.length;
  const xStep = colCount > 1 ? plotW / (colCount - 1) : 0;

  const xAt = (i) => PAD_LEFT + i * xStep;
  const yAt = (v) => PAD_TOP + plotH * (1 - (v - yMin) / (yMax - yMin));

  const tickCount = 4;
  const ticks = [];
  for (let i = 0; i <= tickCount; i += 1) {
    ticks.push(yMin + ((yMax - yMin) * i) / tickCount);
  }
  const zeroLine = yMin < 0 && yMax > 0 ? yAt(0) : null;

  // Build the SBC-drag polygon: across columns where both clean and reported
  // are present, walk forward on reported (upper), then backward on clean.
  const dragIndices = [];
  for (let i = 0; i < colCount; i += 1) {
    if (
      cleanPoints[i] != null &&
      reportedPoints[i] != null &&
      Number.isFinite(cleanPoints[i]) &&
      Number.isFinite(reportedPoints[i])
    ) {
      dragIndices.push(i);
    }
  }
  let dragPath = '';
  if (dragIndices.length >= 2) {
    const upper = dragIndices
      .map((i, idx) =>
        `${idx === 0 ? 'M' : 'L'}${xAt(i).toFixed(2)},${yAt(reportedPoints[i]).toFixed(2)}`
      )
      .join(' ');
    const lower = [...dragIndices]
      .reverse()
      .map((i) => `L${xAt(i).toFixed(2)},${yAt(cleanPoints[i]).toFixed(2)}`)
      .join(' ');
    dragPath = `${upper} ${lower} Z`;
  }

  const buildLinePath = (points) => {
    const segments = [];
    let started = false;
    for (let i = 0; i < points.length; i += 1) {
      const v = points[i];
      if (v == null || !Number.isFinite(v)) {
        started = false;
        continue;
      }
      segments.push(`${started ? 'L' : 'M'}${xAt(i).toFixed(2)},${yAt(v).toFixed(2)}`);
      started = true;
    }
    return segments.join(' ');
  };

  const cleanPath = buildLinePath(cleanPoints);
  const reportedPath = buildLinePath(reportedPoints);

  // Vertical divider between history+TTM and projection (Y1..Y5).
  // Position: between TTM column and Y1 column.
  const ttmIdx = histLabels.length; // index of 'TTM'
  const dividerX = ttmIdx + 1 < colCount ? (xAt(ttmIdx) + xAt(ttmIdx + 1)) / 2 : null;

  return (
    <div className="chart-block">
      <div className="chart-title">FCF margin trajectory</div>
      <div className="chart-legend">
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: CLEAN_COLOR }} />
          Clean (SBC-stripped)
        </span>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: REPORTED_COLOR }} />
          Reported
        </span>
        <span className="legend-item">
          <span
            className="legend-swatch"
            style={{ background: DRAG_FILL, border: '1px solid #d1c4e9' }}
          />
          SBC drag
        </span>
      </div>
      <svg
        className="chart-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="FCF margin trajectory chart"
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
              {formatPct(t, 0)}
            </text>
          </g>
        ))}

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

        {dividerX != null && (
          <line
            x1={dividerX}
            x2={dividerX}
            y1={PAD_TOP}
            y2={HEIGHT - PAD_BOTTOM}
            stroke="#bbb"
            strokeWidth="1"
            strokeDasharray="2 4"
          />
        )}

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

        {/* SBC drag shaded area */}
        {dragPath && <path d={dragPath} fill={DRAG_FILL} stroke="none" />}

        {/* Reported line */}
        {reportedPath && (
          <path d={reportedPath} fill="none" stroke={REPORTED_COLOR} strokeWidth="2" />
        )}
        {reportedPoints.map((v, i) =>
          v != null && Number.isFinite(v) ? (
            <circle
              key={`rep-${i}`}
              cx={xAt(i)}
              cy={yAt(v)}
              r="2.5"
              fill={REPORTED_COLOR}
            />
          ) : null
        )}

        {/* Clean line */}
        {cleanPath && (
          <path d={cleanPath} fill="none" stroke={CLEAN_COLOR} strokeWidth="2" />
        )}
        {cleanPoints.map((v, i) =>
          v != null && Number.isFinite(v) ? (
            <circle
              key={`cln-${i}`}
              cx={xAt(i)}
              cy={yAt(v)}
              r="2.5"
              fill={CLEAN_COLOR}
            />
          ) : null
        )}
      </svg>
      {!hasHistory && <p className="chart-footnote">{FALLBACK_NOTE}</p>}
    </div>
  );
}

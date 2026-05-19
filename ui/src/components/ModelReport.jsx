import {
  verdictClass,
  formatCurrency,
  formatPercent,
  formatBillions
} from '../lib/formatters.js';

const PRE_PROFIT_NOTE = 'Visual breakdown is ESTABLISHED-only for v1.';

function HeaderCell({ label, value }) {
  return (
    <div className="model-header-cell">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

function IvCell({ label, value, accent }) {
  return (
    <div className={`iv-cell${accent ? ` iv-cell-${accent}` : ''}`}>
      <div className="label">{label}</div>
      <div className="value">{formatCurrency(value)}</div>
    </div>
  );
}

export default function ModelReport({ stage }) {
  if (!stage) {
    return <p className="empty">No model data in this report.</p>;
  }

  const {
    method,
    profit_stage,
    base_wacc,
    ntm_revenue,
    fcf_margin_ttm,
    current_price,
    intrinsic_value_range = {},
    range_vs_price,
    position_sizing = {}
  } = stage;

  const isPreProfit = typeof method === 'string' && method.startsWith('pre-profit');
  const rangeClass = `badge ${verdictClass(range_vs_price)}`;
  const signalVerdict = position_sizing.signal_verdict;
  const signalClass = signalVerdict ? `badge ${verdictClass(signalVerdict)}` : null;

  return (
    <div className="card">
      <h2>
        Model
        {range_vs_price && <span className={rangeClass}>{range_vs_price}</span>}
        {profit_stage && (
          <span style={{ color: '#777', fontWeight: 400, fontSize: '0.85rem' }}>
            {profit_stage}
          </span>
        )}
      </h2>

      <div className="model-header">
        <HeaderCell label="Method" value={method ?? '—'} />
        <HeaderCell label="Base WACC" value={formatPercent(base_wacc)} />
        <HeaderCell label="NTM Revenue" value={formatBillions(ntm_revenue)} />
        <HeaderCell label="Clean FCF Margin TTM" value={formatPercent(fcf_margin_ttm)} />
      </div>

      <div className="iv-range">
        <IvCell label="Bear" value={intrinsic_value_range.bear} accent="bear" />
        <IvCell label="Base" value={intrinsic_value_range.base} accent="base" />
        <IvCell label="Bull" value={intrinsic_value_range.bull} accent="bull" />
        <IvCell label="Current" value={current_price} accent="current" />
      </div>

      {position_sizing.band && (
        <div className="position-sizing">
          <div className="position-sizing-line">
            <span className="label">Position sizing</span>
            <span className="band">{position_sizing.band}</span>
            {signalVerdict && <span className={signalClass}>{signalVerdict}</span>}
          </div>
          {position_sizing.rationale && (
            <p className="rationale">{position_sizing.rationale}</p>
          )}
        </div>
      )}

      {isPreProfit && <p className="empty pre-profit-note">{PRE_PROFIT_NOTE}</p>}
    </div>
  );
}

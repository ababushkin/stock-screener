import { verdictClass, ratioLabel, formatRatio } from '../lib/formatters.js';

export default function ScreenReport({ stage }) {
  if (!stage) {
    return <p className="empty">No screen data in this report.</p>;
  }

  const { verdict, profit_stage, ratios = {}, rationale } = stage;
  const badgeClass = `badge ${verdictClass(verdict)}`;

  return (
    <div className="card">
      <h2>
        Screen
        <span className={badgeClass}>{verdict ?? 'UNKNOWN'}</span>
        {profit_stage && <span style={{ color: '#777', fontWeight: 400, fontSize: '0.85rem' }}>
          {profit_stage}
        </span>}
      </h2>

      <div className="ratios">
        {Object.entries(ratios).map(([key, value]) => (
          <div key={key} className="ratio">
            <div className="label">{ratioLabel(key)}</div>
            <div className="value">{formatRatio(value)}</div>
          </div>
        ))}
      </div>

      {rationale && <p className="rationale">{rationale}</p>}
    </div>
  );
}

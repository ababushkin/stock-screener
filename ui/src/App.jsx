import { useMemo, useState } from 'react';
import { loadReports } from './lib/reports.js';
import ScreenReport from './components/ScreenReport.jsx';
import ModelReport from './components/ModelReport.jsx';

const TABS = ['Screen', 'Signal', 'Model', 'Timing', 'Summary'];

export default function App() {
  const reports = useMemo(() => loadReports(), []);
  const [selectedPath, setSelectedPath] = useState(reports[0]?.path ?? null);
  const [tab, setTab] = useState('Screen');

  const current = reports.find((r) => r.path === selectedPath) ?? reports[0];

  if (!current) {
    return (
      <div className="app">
        <h1>Equity Research</h1>
        <p className="empty">No reports found in <code>reports/</code>.</p>
      </div>
    );
  }

  const { data } = current;
  const stages = data.stages ?? {};

  return (
    <div className="app">
      <div className="header">
        <h1>{data.ticker}{data.company ? ` — ${data.company}` : ''}</h1>
        <span className="date">{data.date}</span>
        <select
          className="picker"
          name="report"
          aria-label="Select report"
          value={current.path}
          onChange={(e) => setSelectedPath(e.target.value)}
        >
          {reports.map((r) => (
            <option key={r.path} value={r.path}>
              {r.ticker} — {r.dateStr}
            </option>
          ))}
        </select>
      </div>

      <div className="tabs">
        {TABS.map((name) => {
          const key = name.toLowerCase();
          const hasData = key === 'summary' ? true : Boolean(stages[key]);
          return (
            <button
              key={name}
              className={`tab ${tab === name ? 'active' : ''}`}
              onClick={() => setTab(name)}
              disabled={!hasData}
            >
              {name}
            </button>
          );
        })}
      </div>

      {tab === 'Screen' && <ScreenReport stage={stages.screen} />}
      {tab === 'Model' && <ModelReport stage={stages.model} />}
      {tab !== 'Screen' && tab !== 'Model' && (
        <p className="empty">{tab} view not yet implemented.</p>
      )}
    </div>
  );
}

export function verdictClass(verdict) {
  switch ((verdict || '').toUpperCase()) {
    case 'PASS':
    case 'BUY':
    case 'ACT NOW':
    case 'MARGIN OF SAFETY':
    case 'WITHIN BEAR-BASE':
      return 'pass';
    case 'WATCH':
    case 'CONDITIONAL':
    case 'WAIT FOR CATALYST':
    case 'WITHIN BASE-BULL':
      return 'watch';
    case 'SKIP':
    case 'CAUTION':
    case 'WAIT FOR BETTER ENTRY':
    case 'ABOVE BULL':
      return 'skip';
    default:
      return 'unknown';
  }
}

const RATIO_LABELS = {
  pe_ratio: 'P/E',
  ps_ratio: 'P/S',
  ev_ebitda: 'EV/EBITDA',
  pfcf: 'P/FCF',
  ev_revenue: 'EV/Revenue'
};

export function ratioLabel(key) {
  return RATIO_LABELS[key] ?? key;
}

export function formatRatio(value) {
  if (value == null || Number.isNaN(value)) return '—';
  return Number(value).toFixed(1);
}

function isNum(value) {
  return value != null && !Number.isNaN(Number(value));
}

export function formatCurrency(value) {
  if (!isNum(value)) return '—';
  const n = Number(value);
  if (Math.abs(n) >= 1000) return `$${n.toFixed(0)}`;
  return `$${n.toFixed(2)}`;
}

export function formatPercent(value, digits = 1) {
  if (!isNum(value)) return '—';
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

export function formatBillions(value) {
  if (!isNum(value)) return '—';
  const billions = Number(value) / 1e9;
  if (Math.abs(billions) >= 100) return `$${billions.toFixed(0)}B`;
  return `$${billions.toFixed(1)}B`;
}

export function formatPerShare(value) {
  if (!isNum(value)) return '—';
  return `$${Number(value).toFixed(2)}/sh`;
}

export function verdictClass(verdict) {
  switch ((verdict || '').toUpperCase()) {
    case 'PASS':
    case 'BUY':
    case 'ACT NOW':
      return 'pass';
    case 'WATCH':
    case 'CONDITIONAL':
    case 'WAIT FOR CATALYST':
      return 'watch';
    case 'SKIP':
    case 'CAUTION':
    case 'WAIT FOR BETTER ENTRY':
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

const modules = import.meta.glob('../../../reports/*.json', { eager: true });

function parseFilename(path) {
  const file = path.split('/').pop().replace(/\.json$/, '');
  const [ticker, dateStr] = file.split('_');
  return { ticker, dateStr };
}

export function loadReports() {
  const reports = Object.entries(modules).map(([path, mod]) => {
    const { ticker, dateStr } = parseFilename(path);
    return { path, ticker, dateStr, data: mod.default ?? mod };
  });
  reports.sort((a, b) => b.dateStr.localeCompare(a.dateStr) || b.ticker.localeCompare(a.ticker));
  return reports;
}

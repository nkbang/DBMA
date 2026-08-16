export function formatCount(n) {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString('en-US')
}

export function formatPercent(p) {
  if (p === null || p === undefined) return '0.0%'
  return `${p.toFixed(1)}%`
}

export function formatEta(seconds) {
  if (seconds === null || seconds === undefined || !isFinite(seconds)) return '—'
  const total = Math.max(0, Math.round(seconds))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  return `${h}h ${m}m`
}

export function formatSecPerItem(v) {
  if (v === null || v === undefined) return '—'
  return `${v.toFixed(2)} sec/item`
}

export function formatThroughput(v) {
  if (v === null || v === undefined) return '—'
  return `${Math.round(v)} / hour`
}

export function volumeLabel(identifier) {
  const m = /Vol(\d+)$/.exec(identifier || '')
  return m ? `VOL.${m[1]}` : identifier || '—'
}

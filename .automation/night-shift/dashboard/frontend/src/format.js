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

export function formatGB(bytes) {
  if (bytes === null || bytes === undefined) return '—'
  return `${(bytes / 1e9).toFixed(1)} GB`
}

export function formatExpiresIn(isoString) {
  if (!isoString) return '—'
  const ms = new Date(isoString).getTime() - Date.now()
  if (!isFinite(ms)) return '—'
  if (ms <= 0) return 'expiring…'
  const totalMin = Math.round(ms / 60000)
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

// UNKNOWN/N/A fields (GPU temp/power/clock/pstate/XID, power_throttle, ...)
// share one formatter so "not obtainable here" always reads the same way.
export function formatOrUnknown(v, suffix = '') {
  if (v === null || v === undefined) return 'UNKNOWN'
  return `${v}${suffix}`
}

export function formatBytesPerSec(v) {
  if (v === null || v === undefined) return '—'
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} MB/s`
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)} KB/s`
  return `${Math.round(v)} B/s`
}

export function formatClockTime(epochSeconds) {
  if (!epochSeconds) return '—'
  const d = new Date(epochSeconds * 1000)
  return d.toLocaleTimeString('en-US', { hour12: false })
}

export function formatAgo(epochSeconds) {
  if (!epochSeconds) return '—'
  const s = Math.max(0, Math.round(Date.now() / 1000 - epochSeconds))
  if (s < 60) return `${s}s ago`
  return `${Math.floor(s / 60)}m ${s % 60}s ago`
}

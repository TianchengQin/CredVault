// ---------------------------------------------------------------- password generator

export const POOLS = {
  upper: 'ABCDEFGHJKLMNPQRSTUVWXYZ',
  lower: 'abcdefghijkmnopqrstuvwxyz',
  digits: '23456789',
  symbols: '!@#$%^&*()-_=+[]{};:,.?',
}
const AMBIGUOUS = { upper: 'IO', lower: 'l', digits: '01' }

/** Uniform random integer in [0, max) without modulo bias. */
function randomIndex(max) {
  const limit = Math.floor(0x100000000 / max) * max
  const buf = new Uint32Array(1)
  do crypto.getRandomValues(buf); while (buf[0] >= limit)
  return buf[0] % max
}

export function generatePassword({ length = 20, upper = true, lower = true, digits = true, symbols = true, ambiguous = false } = {}) {
  const sets = Object.entries({ upper, lower, digits, symbols })
    .filter(([, on]) => on)
    .map(([k]) => POOLS[k] + (ambiguous ? AMBIGUOUS[k] || '' : ''))
  if (!sets.length) sets.push(POOLS.lower)
  const all = sets.join('')
  // one from each selected set, the rest from the union, then shuffle
  const chars = sets.map((s) => s[randomIndex(s.length)])
  while (chars.length < length) chars.push(all[randomIndex(all.length)])
  for (let i = chars.length - 1; i > 0; i--) {
    const j = randomIndex(i + 1)
    ;[chars[i], chars[j]] = [chars[j], chars[i]]
  }
  return chars.slice(0, length).join('')
}

// ---------------------------------------------------------------- strength estimate

const LEVELS = [
  { label: 'Very weak', tone: 'danger' },
  { label: 'Weak', tone: 'danger' },
  { label: 'Fair', tone: 'warn' },
  { label: 'Strong', tone: 'ok' },
  { label: 'Excellent', tone: 'ok' },
]

/** Rough entropy-based score 0..4. Good enough for a meter, not a policy. */
export function passwordStrength(pw = '') {
  if (!pw) return { score: 0, bits: 0, ...LEVELS[0] }
  let pool = 0
  if (/[a-z]/.test(pw)) pool += 26
  if (/[A-Z]/.test(pw)) pool += 26
  if (/\d/.test(pw)) pool += 10
  if (/[^A-Za-z0-9]/.test(pw)) pool += 32
  const unique = new Set(pw).size
  let bits = Math.log2(Math.max(pool, 2)) * pw.length * Math.min(1, unique / Math.max(4, pw.length * 0.6))
  if (/^(.)\1+$/.test(pw) || /^(?:password|qwerty|123456|letmein|admin)/i.test(pw)) bits = Math.min(bits, 10)
  const score = bits < 28 ? 0 : bits < 40 ? 1 : bits < 60 ? 2 : bits < 90 ? 3 : 4
  return { score, bits: Math.round(bits), ...LEVELS[score] }
}

// ---------------------------------------------------------------- misc helpers

/** Only allow http(s) links; blocks javascript:, data: etc. from shared items. */
export function safeHref(url) {
  if (!url) return null
  const candidate = /^[a-z][a-z0-9+.-]*:/i.test(url) ? url : `https://${url}`
  try {
    const u = new URL(candidate)
    return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : null
  } catch {
    return null
  }
}

export function displayHost(url) {
  try { return new URL(safeHref(url)).host } catch { return url }
}

const HUES = [256, 210, 168, 140, 32, 340, 12, 290, 190, 48]
export function monogramColor(text = '') {
  let h = 0
  for (const c of text) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return HUES[h % HUES.length]
}

export function initials(name = '') {
  const words = name.trim().split(/[\s._-]+/).filter(Boolean)
  return ((words[0]?.[0] || '?') + (words[1]?.[0] || '')).toUpperCase()
}

export function timeAgo(iso) {
  if (!iso) return ''
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  const units = [[60, 'second'], [60, 'minute'], [24, 'hour'], [30, 'day'], [12, 'month'], [Infinity, 'year']]
  let v = s
  for (const [step, unit] of units) {
    if (Math.abs(v) < step) {
      const n = Math.max(1, Math.round(v))
      return s < 45 ? 'just now' : `${n} ${unit}${n === 1 ? '' : 's'} ago`
    }
    v /= step
  }
  return ''
}

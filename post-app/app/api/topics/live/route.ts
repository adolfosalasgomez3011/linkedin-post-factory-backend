import { NextRequest, NextResponse } from 'next/server'
import { listManagedSources } from '@/lib/neon'

type TopicSuggestion = {
  rank: number
  topic_name: string
  topic_name_es?: string
  published_at?: string
  reasoning?: string
  source?: string
  source_title?: string
  source_url?: string
  source_curated?: boolean
  key_findings?: Array<{ finding: string; source_attribution: string }>
  trend_score?: number
  strategic_score?: number
  recency_score?: number
  channel_fit_score?: number
  momentum_score?: number
  suggested_pillar?: string
  suggested_format?: string
}

type Article = {
  title: string
  source: string
  url: string
  source_domain: string
  publishedAt: string
  description: string
  query: string
  bucket: string
  region_bias: 'latam' | 'north_america' | 'south_africa_australia' | 'global'
  recency_score: number
  momentum_score: number
  channel_fit_score: number
  strategic_score: number
  regional_priority_score: number
  source_quality_score: number
  trend_score: number
}

type FeedSource = {
  name: string
  url: string
}

type QuerySeed = {
  query: string
  bucket: string
  region_bias: 'latam' | 'north_america' | 'south_africa_australia' | 'global'
}

const CHANNEL_QUERY_MAP: Record<string, QuerySeed[]> = {
  personal_career: [
    { query: 'latin america mining operations leadership general manager', bucket: 'personal_ops', region_bias: 'latam' },
    { query: 'peru mining operational transformation strategy', bucket: 'personal_ops', region_bias: 'latam' },
    { query: 'hatch advisory principal mining transformation latam', bucket: 'personal_ops', region_bias: 'latam' },
    { query: 'asset management reliability mining leadership', bucket: 'goalpraxis_signal', region_bias: 'global' },
    { query: 'mining fleet visibility operational control', bucket: 'goalpraxis_signal', region_bias: 'global' },
    { query: 'copper price trend latin america north america mining market', bucket: 'market_prices', region_bias: 'latam' },
    { query: 'lithium market trend south america mining', bucket: 'market_prices', region_bias: 'latam' },
    { query: 'north america mining productivity maintenance strategy', bucket: 'market_prices', region_bias: 'north_america' },
    { query: 'south africa australia mining operations trend', bucket: 'market_prices', region_bias: 'south_africa_australia' },
  ],
  goalpraxis_company: [
    { query: 'minepulse asset visibility mining operations latin america', bucket: 'locate', region_bias: 'latam' },
    { query: 'mining fleet utilization shift productivity latency peru chile', bucket: 'optimize', region_bias: 'latam' },
    { query: 'mine geofence safety alerts operational control copper mine', bucket: 'protect', region_bias: 'latam' },
    { query: 'lorawan mining iot asset tracking north america', bucket: 'locate', region_bias: 'north_america' },
    { query: 'predictive maintenance mining equipment uptime', bucket: 'optimize', region_bias: 'global' },
    { query: 'copper market movement mine productivity costs americas', bucket: 'market_prices', region_bias: 'latam' },
  ],
  other: [
    { query: 'industrial AI operations americas', bucket: 'signals', region_bias: 'north_america' },
    { query: 'digital transformation heavy industry market trends', bucket: 'signals', region_bias: 'global' },
    { query: 'industrial data strategy operations performance', bucket: 'signals', region_bias: 'global' },
    { query: 'asset performance management industrial sites', bucket: 'signals', region_bias: 'global' },
  ],
}

const FALLBACK_QUERY_MAP: Record<string, QuerySeed[]> = {
  personal_career: [
    { query: 'mining industry', bucket: 'market_prices', region_bias: 'global' },
    { query: 'latin america mining', bucket: 'personal_ops', region_bias: 'latam' },
    { query: 'mining maintenance reliability', bucket: 'goalpraxis_signal', region_bias: 'global' },
  ],
  goalpraxis_company: [
    { query: 'mining industry', bucket: 'market_prices', region_bias: 'global' },
    { query: 'mining operations productivity', bucket: 'optimize', region_bias: 'global' },
    { query: 'mining safety', bucket: 'protect', region_bias: 'global' },
    { query: 'asset tracking mining', bucket: 'locate', region_bias: 'global' },
  ],
  other: [
    { query: 'industrial operations', bucket: 'signals', region_bias: 'global' },
    { query: 'digital transformation industry', bucket: 'signals', region_bias: 'global' },
  ],
}

type TopicCacheEntry = {
  topics: TopicSuggestion[]
  updatedAt: string
  fetchedAtMs: number
}

const TOPIC_CACHE_TTL_MS = 10 * 60 * 1000
const TOPIC_CACHE_STALE_MAX_MS = 6 * 60 * 60 * 1000
const TOPIC_CACHE = new Map<string, TopicCacheEntry>()

const CHANNEL_KEYWORDS: Record<string, string[]> = {
  personal_career: ['coo', 'leadership', 'operations', 'asset', 'maintenance', 'decision', 'mining', 'market', 'price', 'trend', 'copper', 'lithium'],
  goalpraxis_company: ['asset', 'tracking', 'visibility', 'fleet', 'utilization', 'safety', 'geofence', 'maintenance', 'lorawan', 'iot', 'productivity', 'uptime'],
  other: ['industrial', 'operations', 'digital', 'data', 'automation', 'technology'],
}

const CURATED_SOURCES: Record<string, string[]> = {
  personal_career: [
    'Reuters', 'Bloomberg', 'Financial Times', 'The Wall Street Journal', 'Harvard Business Review',
    'McKinsey', 'Boston Consulting Group', 'Deloitte', 'World Economic Forum', 'MINING.COM',
    'Mining Journal', 'The Northern Miner'
  ],
  goalpraxis_company: [
    'Reuters', 'MINING.COM', 'International Mining', 'Global Mining Review', 'Engineering & Mining Journal',
    'CIM Magazine', 'Mining Journal', 'Epiroc', 'Komatsu', 'Caterpillar', 'Sandvik', 'Hexagon Mining'
  ],
  other: [
    'Reuters', 'Bloomberg', 'Financial Times', 'World Economic Forum', 'MIT Technology Review',
    'McKinsey', 'Deloitte'
  ],
}

const CURATED_SOURCE_DOMAINS: Record<string, string[]> = {
  personal_career: [
    'reuters.com', 'bloomberg.com', 'ft.com', 'wsj.com', 'hbr.org',
    'mckinsey.com', 'deloitte.com', 'weforum.org', 'mining.com', 'mining-journal.com',
    'northernminer.com'
  ],
  goalpraxis_company: [
    'reuters.com', 'mining.com', 'im-mining.com', 'globalminingreview.com', 'e-mj.com',
    'cim.org', 'mining-journal.com', 'komatsu.com', 'caterpillar.com', 'sandvik.com',
    'hexagon.com', 'epiroc.com'
  ],
  other: [
    'reuters.com', 'bloomberg.com', 'ft.com', 'technologyreview.com', 'mckinsey.com', 'deloitte.com'
  ],
}

const CHANNEL_FEEDS: Record<string, FeedSource[]> = {
  personal_career: [
    { name: 'Reuters', url: 'https://www.reuters.com/world/americas/rss' },
    { name: 'MINING.COM', url: 'https://www.mining.com/feed/' },
    { name: 'The Northern Miner', url: 'https://www.northernminer.com/feed/' },
    { name: 'Harvard Business Review', url: 'https://hbr.org/feed' },
  ],
  goalpraxis_company: [
    { name: 'MINING.COM', url: 'https://www.mining.com/feed/' },
    { name: 'International Mining', url: 'https://im-mining.com/feed/' },
    { name: 'Global Mining Review', url: 'https://www.globalminingreview.com/feed/' },
    { name: 'Engineering & Mining Journal', url: 'https://www.e-mj.com/feed/' },
  ],
  other: [
    { name: 'Reuters', url: 'https://www.reuters.com/world/rss' },
    { name: 'MIT Technology Review', url: 'https://www.technologyreview.com/feed/' },
    { name: 'MINING.COM', url: 'https://www.mining.com/feed/' },
  ],
}

async function resolveChannelFeeds(channel: string): Promise<FeedSource[]> {
  try {
    const managed = await listManagedSources(channel)
    if (managed.length > 0) {
      return managed.map((item) => ({ name: item.name, url: item.url }))
    }
    return []
  } catch {
    return []
  }
}

function isWithinDays(publishedAt: string, daysBack: number): boolean {
  if (!publishedAt) return false
  const published = new Date(publishedAt)
  if (Number.isNaN(published.getTime())) return false
  const ageMs = Date.now() - published.getTime()
  return ageMs >= 0 && ageMs <= daysBack * 24 * 60 * 60 * 1000
}

const LATAM_TERMS = ['latin america', 'latam', 'chile', 'peru', 'argentina', 'mexico', 'brazil', 'south america', 'andes']
const NORTH_AMERICA_TERMS = ['canada', 'usa', 'united states', 'north america']
const SOUTH_AFRICA_AUSTRALIA_TERMS = ['south africa', 'australia', 'queensland', 'western australia']

const PERSONAL_PROFILE_TERMS = [
  'general manager',
  'coo',
  'advisory principal',
  'hatch',
  'ferreyros',
  'chinalco',
  'southern copper',
  'asset management',
  'maintenance',
  'reliability',
  'contract renewal',
  'business transformation',
]

const MOMENTUM_TERMS = ['new', 'launch', 'announces', 'record', 'growth', 'breakthrough', 'investment', 'adoption', 'deploy', 'expands', 'partnership']

function extractTag(text: string, tag: string): string {
  const re = new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`, 'i')
  const match = text.match(re)
  return match?.[1]?.trim() || ''
}

function decodeEntities(value: string): string {
  return value
    .replace(/^<!\[CDATA\[/, '')
    .replace(/\]\]>$/, '')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .trim()
}

function cleanText(value: string): string {
  const decoded = decodeEntities(value)
  return decoded
    .replace(/<a\b[^>]*>/gi, ' ')
    .replace(/<\/a>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/https?:\/\/\S+/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function cleanLink(value: string): string {
  const decoded = decodeEntities(value)
  return decoded
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/** Extract plain text from HTML body, focusing on main content paragraphs */
function extractArticleBody(html: string): string {
  // Remove script, style, noscript tags
  let cleaned = html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/<noscript\b[^<]*(?:(?!<\/noscript>)<[^<]*)*<\/noscript>/gi, '')
    
  // Extract article/main content if available
  const articleMatch = cleaned.match(/<article[^>]*>([\s\S]*?)<\/article>/i)
  const mainMatch = cleaned.match(/<main[^>]*>([\s\S]*?)<\/main>/i)
  const contentMatch = cleaned.match(/<div[^>]*(?:class|id)=["\']?content["\']?[^>]*>([\s\S]{100,10000}?)<\/div>/i)
  const bodyMatch = cleaned.match(/<body[^>]*>([\s\S]*?)<\/body>/i)
  
  const extracted = articleMatch?.[1] || mainMatch?.[1] || contentMatch?.[1] || bodyMatch?.[1] || cleaned
  
  // Extract paragraphs and keep first 3000 chars of meaningful content
  const paragraphs = extracted.match(/<p[^>]*>([\s\S]*?)<\/p>/gi) || []
  const text = paragraphs
    .slice(0, 15)
    .map(p => cleanText(p.replace(/<[^>]+>/g, ' ')))
    .filter(t => t.length > 20)
    .join(' ')
  
  return text.substring(0, 3000)
}

const PAYWALL_SIGNALS = [
  'subscribe for access',
  'subscriber exclusive',
  'subscriber-only',
  'your first complimentary story',
  'sign in to read',
  'subscribe to read',
  'this is a subscriber',
  'unlimited access',
  'digital subscription',
  'subscribe now',
  'create a free account',
  'register to read',
  'already a subscriber',
  'claim offer',
]

function isPaywallContent(text: string): boolean {
  const lower = text.toLowerCase()
  const hits = PAYWALL_SIGNALS.filter(sig => lower.includes(sig)).length
  if (hits < 2) return false
  // Estimate substantive text after stripping paywall-flagged lines
  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 30)
  const nonPaywallChars = lines
    .filter(l => !PAYWALL_SIGNALS.some(sig => l.toLowerCase().includes(sig)))
    .reduce((acc, l) => acc + l.length, 0)
  return nonPaywallChars < 600
}

/** Fetch full article HTML from URL with timeout and error handling.
 *  For Google News URLs, uses Jina AI directly (handles the full redirect chain).
 *  For regular URLs, tries direct HTML fetch first, then falls back to Jina.
 *  Returns empty string for paywalled pages so key_findings stays undefined. */
async function fetchArticleContent(url: string): Promise<string> {
  if (!url || !url.startsWith('http')) return ''

  const isGNews = isGoogleNewsUrl(url)

  // --- Attempt 1: direct fetch (skip for Google News opaque redirect URLs) ---
  if (!isGNews) {
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 4000)
      const response = await fetch(url, {
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
      })
      clearTimeout(timeout)
      if (response.ok) {
        const html = await response.text()
        const body = extractArticleBody(html)
        if (body.length > 200) return body   // good enough — skip Jina
      }
    } catch {
      // fall through to Jina
    }
  }

  // --- Attempt 2: Jina AI reader (handles JS-rendered pages, free, no key needed) ---
  try {
    const jinaUrl = `https://r.jina.ai/${url}`
    const controller2 = new AbortController()
    const timeout2 = setTimeout(() => controller2.abort(), 8000)
    const response2 = await fetch(jinaUrl, {
      cache: 'no-store',
      signal: controller2.signal,
      headers: { 'Accept': 'text/plain', 'X-Return-Format': 'text' },
    })
    clearTimeout(timeout2)
    if (response2.ok) {
      const raw = await response2.text()
      // Jina returns clean markdown text — strip nav junk (links, image refs) and truncate
      const cleaned = raw
        .replace(/!\[.*?\]\(.*?\)/g, '')       // remove images
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // flatten links to text
        .replace(/^\s*[*\-]\s.+$/gm, '')         // strip bullet nav items
        .replace(/\n{3,}/g, '\n\n')
        .trim()
      // Reject paywall pages — return '' so key_findings is not set for this article
      if (isPaywallContent(cleaned)) return ''
      if (cleaned.length > 150) return cleaned.substring(0, 3000)
    }
  } catch {
    // both strategies failed
  }

  return ''
}

/** Extract statistics/data points from text using regex (works on any text, no API needed) */
function extractStatsFromText(text: string, sourceName: string): Array<{ finding: string; source_attribution: string }> {
  if (!text || text.length < 30) return []

  // Match sentences containing a number, percentage, multiplier, or clear magnitude phrase
  const statPatterns = [
    /[^.!?]*(?:\d+(?:\.\d+)?%)[^.!?]*[.!?]/g,                            // sentences with %
    /[^.!?]*(?:\d+(?:\.\d+)?\s*(?:times|x))[^.!?]*[.!?]/gi,             // e.g. "2x" or "1.5 times"
    /[^.!?]*(?:doubled|tripled|halved|quadrupled)[^.!?]*[.!?]/gi,        // "doubled" etc.
    /[^.!?]*(?:decreased|increased|grew|declined|fell|rose)\s+by\s+\d+[^.!?]*[.!?]/gi, // changed by N
    /[^.!?]*(?:from \d{4} to \d{4})[^.!?]*[.!?]/gi,                     // date ranges
    /[^.!?]*(?:\$\d+[bmk]?)[^.!?]*[.!?]/gi,                             // dollar amounts
  ]

  const found = new Set<string>()
  for (const pattern of statPatterns) {
    const matches = text.match(pattern) || []
    for (const m of matches) {
      const clean = m.replace(/\s+/g, ' ').trim()
      if (clean.length > 20 && clean.length < 200 && !found.has(clean)) {
        found.add(clean)
      }
    }
    if (found.size >= 3) break
  }

  const attribution = sourceName ? `(${sourceName})` : ''
  return Array.from(found).slice(0, 3).map((finding) => ({ finding, source_attribution: attribution }))
}

/** Extract key findings from article content using Gemini — with regex fallback */
async function extractKeyFindings(articleBody: string, title: string, source: string, descriptionText?: string): Promise<Array<{ finding: string; source_attribution: string }>> {
  // Always try regex first on whatever text we have (fast, no API)
  const textForRegex = [articleBody, descriptionText].filter(Boolean).join(' ')
  const regexFindings = extractStatsFromText(textForRegex, source)

  // Use article body when available; fall back to description for Gemini context
  const geminiText = articleBody && articleBody.length > 50
    ? articleBody.substring(0, 2500)
    : (descriptionText || '').substring(0, 800)

  if (!geminiText || geminiText.length < 30) {
    return regexFindings
  }

  try {
    const apiKey = process.env.GOOGLE_API_KEY
    if (!apiKey) return regexFindings

    const prompt = `Extract the 3 most compelling, citable findings from this article. These findings will be used as factual anchors in a LinkedIn post — they MUST be specific, verifiable claims from the article itself.

ARTICLE TITLE: ${title}
ARTICLE SOURCE: ${source}

ARTICLE CONTENT:
${geminiText}

Return a JSON array only, no markdown fences:
[
  {
    "finding": "Exact or closely paraphrased sentence from the article (max 200 chars)",
    "source_attribution": "(${source})"
  }
]

EXTRACTION RULES — apply in this order:
1. HARD DATA FIRST: sentences with percentages, multipliers, dollar amounts, "doubled/halved/tripled", or named study results
2. NAMED EVENTS / DECISIONS: specific company actions cited (e.g. "X shut down Y", "Z left company to start..."), named research findings (e.g. "a study found that..."), or specific product/technology claims
3. CONCRETE COMPARISONS: before/after contrasts, failure modes, or performance limits described with specifics (e.g. "works until forced to detour, then fails completely")
4. ATTRIBUTED CLAIMS: statements from named experts, researchers, or institutions quoted or referenced in the article

STRICT RULES:
- Every finding MUST come from the article text above. Do NOT invent or generalise.
- Do NOT write generic summaries like "AI is improving" — cite the specific mechanism or event.
- If the article has no hard numbers but has named studies or decisions, those ARE valid findings.
- Max 3 findings. If fewer than 3 strong ones exist, return only what is truly supported.`

    const controller = new AbortController()
    const extractTimeout = setTimeout(() => controller.abort(), 8000)

    // CRITICAL: API key must be in query param for Gemini REST API
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: 600, temperature: 0.1 },
      }),
      signal: controller.signal,
    })

    clearTimeout(extractTimeout)
    if (!response.ok) return regexFindings.length > 0 ? regexFindings : []

    const data = await response.json()
    const responseText = data.candidates?.[0]?.content?.parts?.[0]?.text || ''

    const jsonMatch = responseText.match(/\[[\s\S]*\]/)
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0])
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed.slice(0, 3)
      }
    }
    // Gemini returned nothing useful → fall back to regex
    return regexFindings
  } catch {
    return regexFindings
  }
}

function getUrlHostname(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase()
  } catch {
    return ''
  }
}

function isGoogleNewsUrl(url: string): boolean {
  const host = getUrlHostname(url)
  return host.includes('news.google.com')
}

function isCuratedDomain(url: string, channel: string): boolean {
  const host = getUrlHostname(url)
  const curatedDomains = CURATED_SOURCE_DOMAINS[channel] || CURATED_SOURCE_DOMAINS.other
  return curatedDomains.some((domain) => host.endsWith(domain) || host.includes(`.${domain}`) || host === domain)
}

async function resolvePublisherUrl(url: string): Promise<string> {
  if (!url || !isGoogleNewsUrl(url)) return url
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 2000)
    const response = await fetch(url, {
      method: 'GET',
      redirect: 'follow',
      cache: 'no-store',
      signal: controller.signal,
    })
    clearTimeout(timeout)
    const finalUrl = response.url || url
    return finalUrl
  } catch {
    return url
  }
}

function computeRecencyScore(publishedAt: string): number {
  if (!publishedAt) return 50
  const published = new Date(publishedAt)
  if (Number.isNaN(published.getTime())) return 50
  const hours = Math.max((Date.now() - published.getTime()) / 3_600_000, 0)
  if (hours <= 24) return 100
  if (hours <= 72) return 90
  if (hours <= 168) return 75
  if (hours <= 336) return 60
  return 45
}

function computeMomentumScore(normalizedTitle: string): number {
  const hits = MOMENTUM_TERMS.filter((term) => normalizedTitle.includes(term)).length
  return Math.min(40 + hits * 12, 100)
}

function computeChannelFitScore(normalizedTitle: string, channel: string): number {
  const terms = CHANNEL_QUERY_MAP[channel] || CHANNEL_QUERY_MAP.other
  let hits = 0
  for (const seed of terms) {
    const tokens = seed.query.split(' ').filter((token) => token.length > 3)
    if (tokens.some((token) => normalizedTitle.includes(token))) {
      hits += 1
    }
  }
  return Math.min(40 + hits * 12, 100)
}

function computeRegionalPriorityScore(
  normalizedTitle: string,
  regionBias: 'latam' | 'north_america' | 'south_africa_australia' | 'global'
): number {
  const latamHits = LATAM_TERMS.filter((term) => normalizedTitle.includes(term)).length
  const northAmericaHits = NORTH_AMERICA_TERMS.filter((term) => normalizedTitle.includes(term)).length
  const southAfricaAustraliaHits = SOUTH_AFRICA_AUSTRALIA_TERMS.filter((term) => normalizedTitle.includes(term)).length

  let base = 54
  if (latamHits > 0) {
    base = 95
  } else if (northAmericaHits > 0) {
    base = 82
  } else if (southAfricaAustraliaHits > 0) {
    base = 68
  }

  if (regionBias === 'latam') {
    base += latamHits > 0 ? 6 : -4
  } else if (regionBias === 'north_america') {
    base += northAmericaHits > 0 ? 5 : -3
  } else if (regionBias === 'south_africa_australia') {
    base += southAfricaAustraliaHits > 0 ? 4 : -2
  }

  return Math.max(0, Math.min(100, base))
}

function computePersonalProfileScore(normalizedTitle: string, channel: string): number {
  if (channel !== 'personal_career') return 50
  const hits = PERSONAL_PROFILE_TERMS.filter((term) => normalizedTitle.includes(term)).length
  return Math.max(40, Math.min(100, 45 + hits * 11))
}

function computeStrategicScore(normalizedTitle: string, channel: string): number {
  const keys = CHANNEL_KEYWORDS[channel] || CHANNEL_KEYWORDS.other
  const hits = keys.filter((k) => normalizedTitle.includes(k)).length
  return Math.min(35 + hits * 13, 100)
}

/** Map known domain patterns to a human-readable publisher name */
function domainToPublisherName(url: string): string {
  try {
    const hostname = new URL(url).hostname.replace(/^www\./, '')
    const MAP: Record<string, string> = {
      'reuters.com': 'Reuters',
      'bloomberg.com': 'Bloomberg',
      'mining.com': 'MINING.com',
      'miningweekly.com': 'Mining Weekly',
      'miningjournal.com': 'Mining Journal',
      'miningglobal.com': 'Mining Global',
      'azomining.com': 'AZoMining',
      'metalbulletin.com': 'Metal Bulletin',
      'proactiveinvestors.com': 'Proactive Investors',
      'kitco.com': 'Kitco',
      'northernminer.com': 'Northern Miner',
      'ft.com': 'Financial Times',
      'wsj.com': 'Wall Street Journal',
      'economist.com': 'The Economist',
      'forbes.com': 'Forbes',
      'techcrunch.com': 'TechCrunch',
      'weforum.org': 'World Economic Forum',
      'iea.org': 'IEA',
      'spglobal.com': 'S&P Global',
      'woodmac.com': 'Wood Mackenzie',
      'mckinsey.com': 'McKinsey',
      'deloitte.com': 'Deloitte',
      'pwc.com': 'PwC',
      'bcg.com': 'BCG',
      'hatch.com': 'Hatch',
      'komatsu.com': 'Komatsu',
      'caterpillar.com': 'Caterpillar',
      'sandvik.com': 'Sandvik',
      'epiroc.com': 'Epiroc',
    }
    if (MAP[hostname]) return MAP[hostname]
    // Capitalize first segment: e.g. "miningweekly.co.za" → "Miningweekly"
    const segment = hostname.split('.')[0]
    return segment.charAt(0).toUpperCase() + segment.slice(1)
  } catch {
    return ''
  }
}

function normalizeSourceName(source?: string): string {
  return (source || '').toLowerCase().replace(/\s+/g, ' ').trim()
}

function isCuratedSource(source: string, channel: string): boolean {
  const normalized = normalizeSourceName(source)
  const curated = CURATED_SOURCES[channel] || CURATED_SOURCES.other
  return curated.some((s) => normalized.includes(s.toLowerCase()))
}

function computeSourceQualityScore(source: string, channel: string): number {
  if (!source) return 45
  if (isCuratedSource(source, channel)) return 92
  return 58
}

function buildArticleUrl(rawUrl: string, _title: string): string {
  if (rawUrl && rawUrl.startsWith('http')) return rawUrl
  return ''
}

function suggestPillar(channel: string, title: string): string {
  const t = title.toLowerCase()

  if (channel === 'goalpraxis_company') {
    // Safety / Geofence
    if (/safety|geofence|incident|accident|fatality|fatalities|hazard|risk|injury|injuries|exclusion zone|seatbelt|fatigue|ppe|regulation|compliance/.test(t))
      return 'Protect: Safety & Geofence Control'
    // Utilization / Productivity
    if (/utilization|productivity|shift|downtime|kpi|throughput|haul|loading|cycle time|dispatch|efficiency|output|oee|uptime|performance|ton|tonne|payload/.test(t))
      return 'Optimize: Utilization & Shift Productivity'
    // Asset / Location Visibility
    if (/asset|tracking|gps|personnel|visibility|locate|position|real.time|monitor|iot|sensor|beacon|telematics|shadow fleet|fleet/.test(t))
      return 'Locate: Asset & Personnel Visibility'
    // Pilot / ROI / Deployment
    if (/pilot|roi|return on invest|business case|deployment|implementation|rollout|proof of concept|poc|trial|cost saving|value proposition/.test(t))
      return 'Pilot ROI & Deployment Strategy'
    return 'MinePulse Operational Intelligence'
  }

  if (channel === 'personal_career') {
    // LatAm region — check first so geography beats generic keywords
    if (/latam|latin america|chile|per[uú]|argentina|bolivia|colombia|brazil|brasil|mexico|m[eé]xico|codelco|antofagasta|andes|sudamerica|south america|latin/.test(t))
      return 'Mining Transformation in LatAm'
    // Asset / Equipment / Maintenance
    if (/asset|maintenance|reliability|equipment|komatsu|caterpillar|sandvik|epiroc|fleet|wear|spare parts|oem|predictive|cbm|condition monitoring|haul truck|shovel|drill/.test(t))
      return 'Asset Management Excellence'
    // COO / Strategy / Technology / Digital
    if (/coo|chief operating|strategy|digital|technology|ai |artificial intelligence|data|analytics|platform|system|decision|innovation|transformation|program|automation|cloud|software|saas/.test(t))
      return 'COO Readiness & Decision Systems'
    // Operations leadership / production
    if (/leadership|operations|operator|mine manager|general manager|capacity|production|output|workforce|labor|talent|culture|people|executive|vp |vice president|director/.test(t))
      return 'Executive Operations Leadership'
    // Career / personal brand / presence (narrower — catch-all only if above don't match)
    return 'Career Narrative & Executive Presence'
  }

  // channel === 'other'
  if (/data|analytics|ai |machine learning|automation|cloud|platform|software/.test(t)) return 'Technology Signals'
  if (/operations|operational|process|efficiency|performance/.test(t)) return 'Operating Models'
  if (/leadership|culture|talent|workforce|people/.test(t)) return 'Leadership and Execution'
  if (/governance|compliance|policy|regulation|risk/.test(t)) return 'Data and Governance'
  return 'Digital Program Lessons'
}

function suggestFormat(title: string): string {
  const t = title.toLowerCase()
  if (t.includes('how to') || t.includes('playbook') || t.includes('framework')) return 'How-To'
  if (t.includes('market') || t.includes('report') || t.includes('forecast') || t.includes('roi')) return 'Data'
  if (t.includes('deployment') || t.includes('pilot') || t.includes('case')) return 'Case Study'
  if (t.includes('?')) return 'Question'
  return 'Insight'
}

async function fetchRssArticles(query: string, limit: number): Promise<Array<{
  title: string
  source: string
  url: string
  publishedAt: string
  description: string
  query: string
}>> {
  const url = `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=en-US&gl=US&ceid=US:en`
  try {
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), 8000)
    const response = await fetch(url, {
      cache: 'no-store',
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml,application/xml,text/xml,*/*',
      },
    })
    clearTimeout(t)
    const xml = await response.text()
    const items = xml.match(/<item>[\s\S]*?<\/item>/g) || []
    return items.slice(0, limit).map((itemXml) => {
      const rawTitle = cleanText(extractTag(itemXml, 'title'))
      const rawLink = cleanLink(extractTag(itemXml, 'link'))
      const pubDate = cleanText(extractTag(itemXml, 'pubDate'))
      const description = cleanText(extractTag(itemXml, 'description'))
      let title = rawTitle
      let source = 'Google News'
      if (rawTitle.includes(' - ')) {
        const idx = rawTitle.lastIndexOf(' - ')
        title = rawTitle.slice(0, idx).trim()
        source = rawTitle.slice(idx + 3).trim() || source
      }
      return { title, source, url: rawLink, publishedAt: pubDate, description, query }
    })
  } catch {
    return []
  }
}

async function fetchFromCuratedFeed(feed: FeedSource, limit: number): Promise<Array<{
  title: string
  source: string
  url: string
  source_domain: string
  publishedAt: string
  description: string
  query: string
}>> {
  try {
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), 8000)
    const response = await fetch(feed.url, {
      cache: 'no-store',
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml,application/xml,text/xml,*/*',
      },
    })
    clearTimeout(t)
    if (!response.ok) return []
    const xml = await response.text()
    const items = xml.match(/<item>[\s\S]*?<\/item>/g) || []

    const parsed = items.slice(0, limit).map((itemXml) => {
      const rawTitle = cleanText(extractTag(itemXml, 'title'))
      const rawLink = cleanLink(extractTag(itemXml, 'link'))
      const pubDate = cleanText(extractTag(itemXml, 'pubDate'))
      const description = cleanText(extractTag(itemXml, 'description'))
      const source_domain = getUrlHostname(rawLink)

      return {
        title: rawTitle,
        source: feed.name,
        url: rawLink,
        source_domain,
        publishedAt: pubDate,
        description,
        query: `feed:${feed.name}`,
      }
    })

    return parsed.filter((item) => Boolean(item.title && item.url))
  } catch {
    return []
  }
}

function normalizeTitleKey(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function buildQueryPlan(channel: string): QuerySeed[] {
  const primary = CHANNEL_QUERY_MAP[channel] || CHANNEL_QUERY_MAP.other
  const fallback = FALLBACK_QUERY_MAP[channel] || FALLBACK_QUERY_MAP.other
  const seen = new Set<string>()
  const merged = [...primary, ...fallback]
  const unique: QuerySeed[] = []

  for (const seed of merged) {
    const key = seed.query.toLowerCase().trim()
    if (!key || seen.has(key)) continue
    seen.add(key)
    unique.push(seed)
  }

  return unique
}

function makeReasoningSummary(article: Article, channel: string): string {
  const lead = article.description && article.description.length > 24
    ? article.description
    : `${article.source} reports a fresh signal related to ${article.bucket.replace('_', ' ')}.`

  const channelTag = channel === 'goalpraxis_company'
    ? 'GoalPraxis relevance: operational visibility, utilization, and safety execution.'
    : channel === 'personal_career'
      ? 'Personal relevance: leadership decisions, mine operations, and market impact.'
      : 'Relevance: industrial operations and transformation signal.'

  return `${lead} ${channelTag}`.replace(/\s+/g, ' ').trim().slice(0, 260)
}

function diversifyPersonalTopics(articles: Article[], count: number): Article[] {
  const grouped: Record<string, Article[]> = {
    personal_ops: [],
    goalpraxis_signal: [],
    market_prices: [],
  }
  for (const item of articles) {
    if (grouped[item.bucket]) {
      grouped[item.bucket].push(item)
    }
  }

  const selected: Article[] = []
  const used = new Set<string>()
  const quota: Array<{ bucket: keyof typeof grouped; count: number }> = [
    { bucket: 'personal_ops', count: 3 },
    { bucket: 'goalpraxis_signal', count: 3 },
    { bucket: 'market_prices', count: 2 },
  ]

  for (const q of quota) {
    for (const candidate of grouped[q.bucket]) {
      const key = normalizeTitleKey(candidate.title)
      if (used.has(key)) continue
      selected.push(candidate)
      used.add(key)
      if (selected.length >= count || selected.filter((a) => a.bucket === q.bucket).length >= q.count) break
    }
  }

  if (selected.length >= count) return selected.slice(0, count)

  for (const candidate of articles) {
    const key = normalizeTitleKey(candidate.title)
    if (used.has(key)) continue
    selected.push(candidate)
    used.add(key)
    if (selected.length >= count) break
  }

  return selected.slice(0, count)
}

function diversifyByDomain(articles: Article[], count: number): Article[] {
  const selected: Article[] = []
  const domainCounts = new Map<string, number>()

  for (const article of articles) {
    const domain = article.source_domain || getUrlHostname(article.url) || 'unknown'
    const currentCount = domainCounts.get(domain) || 0
    if (currentCount >= 2) continue
    selected.push(article)
    domainCounts.set(domain, currentCount + 1)
    if (selected.length >= count) return selected
  }

  for (const article of articles) {
    if (selected.includes(article)) continue
    selected.push(article)
    if (selected.length >= count) break
  }

  return selected.slice(0, count)
}

/** Strip common domain-prefix patterns from RSS article titles used as fallback */
function cleanRawTitle(title: string): string {
  // Remove "source.com reports that..." / "xyz.com says that..." patterns
  const domainPrefixRe = /^[\w-]+\.(?:com|net|org|io|co)\s+(?:reports?|says?|announces?|warns?|reveals?|confirms?|shows?|finds?|informs?)\s+(?:that\s+)?/i
  const cleaned = title.replace(domainPrefixRe, '').trim()
  return cleaned || title
}

/** One batched Gemini call that generates compelling bilingual headlines for all articles at once */
async function generateBilingualTitles(articles: Article[]): Promise<Array<{ en: string; es: string }>> {
  const apiKey = process.env.GOOGLE_API_KEY
  if (!apiKey || articles.length === 0) {
    return articles.map(a => ({ en: cleanRawTitle(a.title), es: '' }))
  }

  const articleList = articles.map((a, i) => {
    const desc = (a as unknown as { description?: string }).description || ''
    return `${i + 1}. TITLE: ${a.title}\n   SOURCE: ${a.source}\n   DESCRIPTION: ${desc.substring(0, 200)}`
  }).join('\n\n')

  const prompt = `You are a LinkedIn content strategist for a mining operations executive in Latin America.

Generate compelling bilingual card headlines for ${articles.length} news articles below. Each headline must:
- Be 8–12 words max
- Lead with the KEY INSIGHT or business implication — NEVER start with a domain name, "reports that", "informs that", or similar filler
- Sound like a headline that makes a mining COO or GM want to read more
- Spanish version must feel native and punchy — not a word-for-word translation

Return ONLY a valid JSON array with exactly ${articles.length} objects. No markdown fences, no extra text:
[{"en":"...","es":"..."},{"en":"...","es":"..."},...]

ARTICLES:
${articleList}`

  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 12000)
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { maxOutputTokens: 900, temperature: 0.45 },
        }),
        signal: controller.signal,
      }
    )
    clearTimeout(timeout)

    if (!response.ok) {
      return articles.map(a => ({ en: cleanRawTitle(a.title), es: '' }))
    }

    const data = await response.json()
    const raw: string = data.candidates?.[0]?.content?.parts?.[0]?.text || ''
    const jsonMatch = raw.match(/\[[\s\S]*\]/)
    if (jsonMatch) {
      const parsed: Array<{ en?: string; es?: string }> = JSON.parse(jsonMatch[0])
      if (Array.isArray(parsed) && parsed.length === articles.length) {
        return parsed.map((t, i) => ({
          en: (t.en && t.en.trim()) ? t.en.trim() : cleanRawTitle(articles[i].title),
          es: (t.es && t.es.trim()) ? t.es.trim() : '',
        }))
      }
    }
  } catch {
    // fall through to deterministic fallback
  }

  return articles.map(a => ({ en: cleanRawTitle(a.title), es: '' }))
}

export async function GET(request: NextRequest) {
  const channel = request.nextUrl.searchParams.get('channel') || 'goalpraxis_company'
  const count = Math.min(Math.max(Number(request.nextUrl.searchParams.get('count') || '8'), 1), 12)
  const daysBack = Math.min(Math.max(Number(request.nextUrl.searchParams.get('days_back') || '30'), 1), 180)
  const pillar = request.nextUrl.searchParams.get('pillar') || ''
  const debug = request.nextUrl.searchParams.get('debug') === '1'

  const now = Date.now()
  // Cache key includes pillar so each pillar gets its own independently-ranked article list
  const cacheKey = `${channel}:${daysBack}:${pillar}`
  const cached = TOPIC_CACHE.get(cacheKey)
  if (!debug && cached && (now - cached.fetchedAtMs) <= TOPIC_CACHE_TTL_MS) {
    return NextResponse.json({
      channel,
      topics: cached.topics.slice(0, count),
      updated_at: cached.updatedAt,
      cache: 'fresh',
      stale: false,
    })
  }

  const queries: QuerySeed[] = []
  const feeds = await resolveChannelFeeds(channel)
  if (feeds.length === 0) {
    return NextResponse.json({ error: `No managed sources configured for ${channel}.` }, { status: 400 })
  }
  const seen = new Set<string>()
  const seenTitles = new Set<string>()
  const collected: Article[] = []

  // ── Fetch all curated feeds in parallel ─────────────────────────────────────
  // Fetch more articles per feed so different pillars can pull different top results from the pool
  const feedResults = await Promise.all(feeds.map((feed) => fetchFromCuratedFeed(feed, 10)))
    if (debug) {
      const debugFeedInfo = feedResults.map((articles, i) => ({ feed: feeds[i].name, count: articles.length, sample: articles[0]?.title || null }))
      const sampleQuery = queries[0]
      // Also probe each feed directly for status code
      const feedProbes = await Promise.all(feeds.map(async (feed) => {
        try {
          const ctrl = new AbortController()
          const tt = setTimeout(() => ctrl.abort(), 5000)
          const r = await fetch(feed.url, { signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } })
          clearTimeout(tt)
          const xml = await r.text()
          const items = xml.match(/<item>/g) || []
          return { feed: feed.name, status: r.status, items: items.length, preview: xml.slice(0, 200) }
        } catch (e: unknown) { return { feed: feed.name, status: String(e), items: 0, preview: '' } }
      }))
      // Test a broader Google News query
      let broadTest: { status: number | string; items: number; preview?: string } = { status: 'not tested', items: 0 }
      try {
        const ctrl2 = new AbortController()
        const tt2 = setTimeout(() => ctrl2.abort(), 5000)
        const r2 = await fetch('https://news.google.com/rss/search?q=mining+industry&hl=en-US&gl=US&ceid=US:en', { signal: ctrl2.signal, headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } })
        clearTimeout(tt2)
        const xml2 = await r2.text()
        const items2 = xml2.match(/<item>/g) || []
        broadTest = { status: r2.status, items: items2.length, preview: xml2.slice(0, 300) }
      } catch (e: unknown) { broadTest = { status: String(e), items: 0 } }
      let googleTest: { status: number | string; items: number; preview?: string } = { status: 'not tested', items: 0 }
      try {
        const testUrl = `https://news.google.com/rss/search?q=${encodeURIComponent(sampleQuery.query)}&hl=en-US&gl=US&ceid=US:en`
        const ctrl = new AbortController()
        const tt = setTimeout(() => ctrl.abort(), 5000)
        const r = await fetch(testUrl, { signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } })
        clearTimeout(tt)
        const xml = await r.text()
        const items = xml.match(/<item>/g) || []
        googleTest = { status: r.status, items: items.length, preview: xml.slice(0, 400) }
      } catch (e: unknown) { googleTest = { status: String(e), items: 0 } }
      return NextResponse.json({ debug: true, feeds: debugFeedInfo, feedProbes, googleTest, broadTest, channel })
    }
  for (const feedArticles of feedResults) {
    for (const a of feedArticles) {
      const titleKey = normalizeTitleKey(a.title)
      if (!isWithinDays(a.publishedAt, daysBack)) continue
      if (!a.url || seen.has(a.url) || seenTitles.has(titleKey)) continue
      seen.add(a.url)
      seenTitles.add(titleKey)

      const normalized = a.title.toLowerCase()
      const recency_score = computeRecencyScore(a.publishedAt)
      const momentum_score = computeMomentumScore(normalized)
      const channel_fit_score = computeChannelFitScore(normalized, channel)
      const strategic_score = computeStrategicScore(normalized, channel)
      const regional_priority_score = computeRegionalPriorityScore(normalized, 'global')
      const personal_profile_score = computePersonalProfileScore(normalized, channel)
      const source_quality_score = 100
      const trend_score = Number((
        recency_score * 0.18 +
        momentum_score * 0.14 +
        channel_fit_score * 0.18 +
        strategic_score * 0.18 +
        regional_priority_score * 0.14 +
        source_quality_score * 0.12 +
        (channel === 'personal_career' ? personal_profile_score * 0.06 : 0)
      ).toFixed(1))

      collected.push({
        ...a,
        recency_score,
        momentum_score,
        channel_fit_score,
        strategic_score,
        regional_priority_score,
        source_quality_score,
        trend_score,
        bucket: 'curated_feed',
        region_bias: 'global',
      })
    }
  }

  // Google News enrichment intentionally disabled here.
  // Load Topics is sourced only from managed feed URLs for transparency.

  const curatedFirst = collected
    .filter((a) => isCuratedDomain(a.url, channel) || isCuratedSource(a.source, channel))
    .sort((a, b) => b.trend_score - a.trend_score)
  const nonCurated = collected
    .filter((a) => !(isCuratedDomain(a.url, channel) || isCuratedSource(a.source, channel)))
    .sort((a, b) => b.trend_score - a.trend_score)

  const sorted = [...curatedFirst, ...nonCurated]

  // When a pillar is requested, pull matching articles to the front of the selection pool
  // so the expensive AI step (bilingual titles + key findings) processes the most relevant articles.
  let diversified: Article[]
  if (pillar) {
    const matched = sorted
      .filter((a) => suggestPillar(channel, a.title) === pillar)
      .sort((a, b) => b.trend_score - a.trend_score)
    const unmatched = sorted
      .filter((a) => suggestPillar(channel, a.title) !== pillar)
      .sort((a, b) => b.trend_score - a.trend_score)
    diversified = diversifyByDomain([...matched, ...unmatched], count)
  } else {
    const selected = channel === 'personal_career'
      ? diversifyPersonalTopics(sorted, count)
      : sorted.slice(0, count)
    diversified = diversifyByDomain(selected, count)
  }

  // Start AI bilingual title generation in parallel with article content fetching (one batch call)
  const bilingualTitlesPromise = generateBilingualTitles(diversified)

  const ranked = await Promise.all(diversified
    .map<Promise<TopicSuggestion>>(async (a, idx) => {
      const articleBody = await fetchArticleContent(a.url)
      // Pass description as fallback source for regex extraction when article body is unavailable
      const descriptionText = (a as { description?: string }).description || ''
      const [keyFindings, bilingualTitles] = await Promise.all([
        extractKeyFindings(articleBody, a.title, a.source || '', descriptionText),
        bilingualTitlesPromise,  // shared promise — resolved once, reused by all map callbacks
      ])
      const biTitle = bilingualTitles[idx] || { en: cleanRawTitle(a.title), es: '' }

      return {
        rank: idx + 1,
        topic_name: biTitle.en,
        topic_name_es: biTitle.es || undefined,
        published_at: a.publishedAt,
        reasoning: makeReasoningSummary(a, channel),
        source: (a.source && a.source !== 'Google News') ? a.source : (domainToPublisherName(a.url) || a.source || ''),
        source_title: a.title,
        source_url: buildArticleUrl(a.url, a.title),
        source_curated: isCuratedSource(a.source, channel),
        key_findings: keyFindings.length > 0 ? keyFindings : undefined,
        trend_score: a.trend_score,
        strategic_score: a.strategic_score,
        recency_score: a.recency_score,
        channel_fit_score: a.channel_fit_score,
        momentum_score: a.momentum_score,
        suggested_pillar: suggestPillar(channel, a.title),
        suggested_format: suggestFormat(a.title),
      }
    }))


  if (ranked.length > 0) {
    TOPIC_CACHE.set(cacheKey, {
      topics: ranked.slice(0, 12),
      updatedAt: new Date().toISOString(),
      fetchedAtMs: now,
    })
  }

  if (ranked.length === 0) {
    return NextResponse.json({ error: `No articles found in the last ${daysBack} days from configured sources.` }, { status: 404 })
  }

  return NextResponse.json({
    channel,
    topics: ranked,
    updated_at: new Date().toISOString(),
    cache: 'miss',
    stale: false,
    degraded: ranked.length === 0,
  })
}

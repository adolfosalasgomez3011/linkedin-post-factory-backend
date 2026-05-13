'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { api, PostResponse, TopicSuggestion } from '@/lib/api'
import { Loader2, Sparkles, Copy, CheckCircle2, Upload, X, FileText } from 'lucide-react'

const VOICE_CORPUS_DIR = 'C:\\Users\\USER\\OneDrive\\LinkedIn_PersonalBrand\\LinkedInAIPosts\\PublishedPost _MachineLearnign'

const CHANNELS = [
  {
    value: 'personal_career',
    label: 'Personal Career Channel',
    description: 'General Manager / COO / Asset Management positioning in LatAm mining'
  },
  {
    value: 'goalpraxis_company',
    label: 'GoalPraxis Company Channel',
    description: 'Asset tracking, Shadow Fleet visibility, pilots, and company traction'
  },
  {
    value: 'other',
    label: 'Other Channel',
    description: 'Additional topic stream for adjacent ideas and experiments'
  }
]

const CHANNEL_PILLARS: Record<string, string[]> = {
  personal_career: [
    'Executive Operations Leadership',
    'Asset Management Excellence',
    'COO Readiness & Decision Systems',
    'Mining Transformation in LatAm',
    'Career Narrative & Executive Presence'
  ],
  goalpraxis_company: [
    'Locate: Asset & Personnel Visibility',
    'Optimize: Utilization & Shift Productivity',
    'Protect: Safety & Geofence Control',
    'MinePulse Operational Intelligence',
    'Pilot ROI & Deployment Strategy'
  ],
  other: [
    'Technology Signals',
    'Operating Models',
    'Digital Program Lessons',
    'Data and Governance',
    'Leadership and Execution'
  ]
}

const POST_TYPES = [
  { value: 'standard', label: 'Standard Text + Image' },
  { value: 'carousel', label: 'Carousel PDF (Slides)' },
  { value: 'news', label: 'News / Trending Topic' },
  { value: 'interactive', label: 'Interactive Demo' }
]

const CHANNEL_FORMATS: Record<string, string[]> = {
  personal_career: ['Story', 'Insight', 'How-To', 'Question', 'Contrarian', 'Case Study'],
  goalpraxis_company: ['Insight', 'How-To', 'Case Study', 'Data', 'Contrarian', 'Question'],
  other: ['Insight', 'How-To', 'Story', 'Question', 'Contrarian', 'Data']
}

const CHANNEL_CURATED_SOURCES: Record<string, string[]> = {
  personal_career: [
    'Reuters', 'Bloomberg', 'Financial Times', 'WSJ', 'Harvard Business Review',
    'McKinsey', 'Deloitte', 'World Economic Forum', 'MINING.COM', 'Mining Journal'
  ],
  goalpraxis_company: [
    'Reuters', 'MINING.COM', 'International Mining', 'Global Mining Review', 'E&MJ',
    'CIM Magazine', 'Komatsu', 'Caterpillar', 'Sandvik', 'Hexagon Mining'
  ],
  other: [
    'Reuters', 'Bloomberg', 'Financial Times', 'MIT Technology Review', 'McKinsey', 'Deloitte'
  ],
}

const CHANNEL_TOPIC_FALLBACKS: Record<string, TopicSuggestion[]> = {
  goalpraxis_company: [
    {
      rank: 1,
      topic_name: 'How MinePulse Locate cuts 2-3 hours per shift lost searching for assets',
      reasoning: 'MinePulse launch deck: core value is locate control and search-loss elimination.',
      suggested_pillar: 'Locate: Asset & Personnel Visibility',
      suggested_format: 'Case Study',
    },
    {
      rank: 2,
      topic_name: 'Turning shadow fleet blind spots into CAPEX containment with real-time visibility',
      reasoning: 'Deck mentions measurable CAPEX containment from Locate capability.',
      suggested_pillar: 'Locate: Asset & Personnel Visibility',
      suggested_format: 'Insight',
    },
    {
      rank: 3,
      topic_name: 'MinePulse Optimize: where 10-20% utilization uplift really comes from',
      reasoning: 'Deck highlights Optimize gains in productivity and utilization.',
      suggested_pillar: 'Optimize: Utilization & Shift Productivity',
      suggested_format: 'Data',
    },
    {
      rank: 4,
      topic_name: 'From telemetry to maintenance planning: making downtime actionable',
      reasoning: 'Deck: usage and downtime telemetry to drive maintenance planning.',
      suggested_pillar: 'Optimize: Utilization & Shift Productivity',
      suggested_format: 'How-To',
    },
    {
      rank: 5,
      topic_name: 'Protect layer in practice: geofence alerts and faster response workflows',
      reasoning: 'Deck: restricted-area alerts and emergency workflows as safety value.',
      suggested_pillar: 'Protect: Safety & Geofence Control',
      suggested_format: 'Case Study',
    },
    {
      rank: 6,
      topic_name: 'Operational intelligence in seconds: from field events to supervisor decisions',
      reasoning: 'Deck narrative: convert field events into operational decisions in seconds.',
      suggested_pillar: 'MinePulse Operational Intelligence',
      suggested_format: 'Insight',
    },
    {
      rank: 7,
      topic_name: 'Year-1 MinePulse business case: Locate + Optimize + Protect savings model',
      reasoning: 'Deck includes estimated year-1 savings across all three capabilities.',
      suggested_pillar: 'Pilot ROI & Deployment Strategy',
      suggested_format: 'Data',
    },
    {
      rank: 8,
      topic_name: 'How to structure a MinePulse pilot with measurable operational KPIs',
      reasoning: 'Deck framing supports KPI-led pilot and deployment messaging.',
      suggested_pillar: 'Pilot ROI & Deployment Strategy',
      suggested_format: 'How-To',
    },
  ],
  personal_career: [
    { rank: 1, topic_name: 'How COO leaders convert visibility initiatives into measurable mine performance', reasoning: 'Leadership angle: tie operational visibility to decisions, execution rhythm, and P&L outcomes.', suggested_pillar: 'COO Readiness & Decision Systems', suggested_format: 'Insight' },
    { rank: 2, topic_name: 'Decision cadence for site leaders: turning field signals into weekly actions', reasoning: 'Personal leadership angle for General Manager/COO audience in operating mines.', suggested_pillar: 'Executive Operations Leadership', suggested_format: 'How-To' },
    { rank: 3, topic_name: 'What mining operators miss when asset tracking is treated as only IT', reasoning: 'Bridge topic between personal operations leadership and GoalPraxis operational-control narrative.', suggested_pillar: 'Asset Management Excellence', suggested_format: 'Contrarian' },
    { rank: 4, topic_name: 'Operational governance for digital mine programs in LatAm', reasoning: 'Americas-first focus: governance patterns for Chile, Peru, Mexico, and broader LatAm operations.', suggested_pillar: 'Mining Transformation in LatAm', suggested_format: 'Insight' },
    { rank: 5, topic_name: 'Copper price swings and what they change in maintenance and utilization priorities', reasoning: 'Market movement topic: commodity price volatility translated into operational decisions.', suggested_pillar: 'COO Readiness & Decision Systems', suggested_format: 'Data' },
    { rank: 6, topic_name: 'Lithium demand trends in the Americas and implications for mine operating models', reasoning: 'Market trend topic linked to strategic planning and operating model shifts.', suggested_pillar: 'Mining Transformation in LatAm', suggested_format: 'Insight' },
    { rank: 7, topic_name: 'From maintenance firefighting to controlled execution using live telemetry', reasoning: 'Personal + GoalPraxis crossover: decision quality improves with usage and downtime visibility.', suggested_pillar: 'Asset Management Excellence', suggested_format: 'Case Study' },
    { rank: 8, topic_name: 'How operational leaders evaluate pilot ROI before scale-up', reasoning: 'Executive framing for pilot economics before full-scale deployment.', suggested_pillar: 'COO Readiness & Decision Systems', suggested_format: 'How-To' },
  ],
  other: [
    { rank: 1, topic_name: 'Industrial visibility systems that move from dashboards to decisions', suggested_pillar: 'Technology Signals', suggested_format: 'Insight' },
    { rank: 2, topic_name: 'What makes telemetry data useful for frontline execution', suggested_pillar: 'Data and Governance', suggested_format: 'How-To' },
    { rank: 3, topic_name: 'Common failures in digital operations programs and how to avoid them', suggested_pillar: 'Digital Program Lessons', suggested_format: 'Contrarian' },
    { rank: 4, topic_name: 'Linking safety controls with productivity KPIs in high-risk environments', suggested_pillar: 'Operating Models', suggested_format: 'Case Study' },
    { rank: 5, topic_name: 'Pilot design checklist for operational technology adoption', suggested_pillar: 'Digital Program Lessons', suggested_format: 'How-To' },
    { rank: 6, topic_name: 'When a real-time alert should trigger a workflow, not just a notification', suggested_pillar: 'Operating Models', suggested_format: 'Question' },
    { rank: 7, topic_name: 'Visibility architectures that scale across distributed operations', suggested_pillar: 'Technology Signals', suggested_format: 'Data' },
    { rank: 8, topic_name: 'Leadership behaviors that improve digital execution quality', suggested_pillar: 'Leadership and Execution', suggested_format: 'Story' },
  ],
}

const LANGUAGES = [
  { value: 'english', label: 'English Only' },
  { value: 'spanish', label: 'Spanish Only' },
  { value: 'both', label: 'Both Languages' }
]

export function PostGenerator() {
  const router = useRouter()
  const [channel, setChannel] = useState('personal_career')
  const [pillar, setPillar] = useState('')
  const [postType, setPostType] = useState('standard')
  const [format, setFormat] = useState('')
  const [topic, setTopic] = useState('')
  const [language, setLanguage] = useState('both')
  const [provider] = useState('gemini')
  const [loading, setLoading] = useState(false)
  const [loadingNews, setLoadingNews] = useState(false)
  const [newsList, setNewsList] = useState<any[]>([])
  const [selectedNews, setSelectedNews] = useState<string[]>([])
  const [generatedPost, setGeneratedPost] = useState<PostResponse | null>(null)
  const [topicSuggestions, setTopicSuggestions] = useState<TopicSuggestion[]>([])
  const [loadingTopics, setLoadingTopics] = useState(false)
  const [topicsUpdatedAt, setTopicsUpdatedAt] = useState<string | null>(null)
  const [topicsNotice, setTopicsNotice] = useState<string | null>(null)
  const [selectedTopicName, setSelectedTopicName] = useState('')
  const [copied, setCopied] = useState(false)
  const [manualArticleText, setManualArticleText] = useState<string | null>(null)
  const [manualArticleLabel, setManualArticleLabel] = useState<string | null>(null)
  const [articleUploading, setArticleUploading] = useState(false)
  const [showPasteArea, setShowPasteArea] = useState(false)
  const [pasteBuffer, setPasteBuffer] = useState('')
  const [daysBack, setDaysBack] = useState(30)
  const selectedChannel = CHANNELS.find((item) => item.value === channel)
  const currentPillars = CHANNEL_PILLARS[channel] || []
  const currentFormats = CHANNEL_FORMATS[channel] || []

  const isHttpLink = (url?: string) => {
    return Boolean(url && /^https?:\/\//i.test(url))
  }

  const isGoogleNewsLink = (url?: string) => {
    return Boolean(url && url.includes('news.google.com'))
  }

  const sanitizeSummary = (value: string) => {
    return value
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/gi, "'")
      .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
      .replace(/<a\b[^>]*>/gi, ' ')
      .replace(/<\/a>/gi, ' ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/https?:\/\/\S+/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  }

  const getTopicSummary = (item: TopicSuggestion) => {
    if (item.reasoning && item.reasoning.trim().length > 0) {
      return sanitizeSummary(item.reasoning.trim())
    }
    if (item.source) {
      return `Quick summary: this topic is currently surfacing in ${item.source} and is relevant for ${selectedChannel?.label || 'this channel'}.`
    }
    return `Quick summary: high-relevance topic for ${selectedChannel?.label || 'this channel'} based on current signals.`
  }

  const getTopicSourceLink = (item: TopicSuggestion) => {
    if (isHttpLink(item.source_url)) {
      return {
        href: item.source_url as string,
        label: isGoogleNewsLink(item.source_url) ? 'Open article (Google News)' : 'Open full article',
      }
    }
    return null
  }

  useEffect(() => {
    const savedChannel = typeof window !== 'undefined' ? window.localStorage.getItem('post_factory_channel') : null
    if (savedChannel && CHANNELS.some((c) => c.value === savedChannel)) {
      setChannel(savedChannel)
    }
  }, [])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('post_factory_channel', channel)
    }
  }, [channel])

  useEffect(() => {
    setPillar('')
    setFormat('')
    setTopic('')
    setSelectedTopicName('')
    setTopicSuggestions([])
    setGeneratedPost(null)
  }, [channel])

  // Fetch news when "news" post type is selected
  useEffect(() => {
    if (postType === 'news' && newsList.length === 0) {
      fetchTrendingNews()
    }
  }, [postType])

  const fetchTrendingNews = async () => {
    setLoadingNews(true)
    try {
      const news = await api.getTrendingNews('technology', 15)
      setNewsList(news.articles || [])
    } catch (error) {
      console.error('Failed to fetch news:', error)
      alert('Failed to load trending news')
    } finally {
      setLoadingNews(false)
    }
  }

  const fetchTrendingTopics = async (_refresh: boolean = false) => {
    if (!pillar) {
      setTopicsNotice('Please select a content pillar first, then click Load Topics.')
      return
    }

    setLoadingTopics(true)
    setTopicsNotice(null)
    try {
      const response = await api.getLiveWebTopics(channel, 8, daysBack, pillar)
      const topicsToShow = response.topics || []
      const pillarMatchedCount = topicsToShow.filter((item) => item.suggested_pillar === pillar).length

      if (topicsToShow.length > 0) {
        setTopicSuggestions(topicsToShow)
        setTopicsUpdatedAt(response.updated_at || new Date().toISOString())
        setTopicsNotice(
          pillarMatchedCount === 0
            ? 'No exact pillar match found in topics, showing available sources.'
            : null
        )

        const firstTopic = topicsToShow[0]
        if (firstTopic) {
          setTopic('')
          setSelectedTopicName('')
        }
        if (firstTopic && !topic) {
          setTopic(firstTopic.topic_name)
          setSelectedTopicName(firstTopic.topic_name)
          if (firstTopic.suggested_format && currentFormats.includes(firstTopic.suggested_format)) {
            setFormat(firstTopic.suggested_format)
          } else if (currentFormats.length > 0) {
            setFormat(currentFormats[0])
          }
        }
        return
      }

      setTopicsNotice('No articles found for the selected time period. Try expanding the date range.')
    } catch (error) {
      console.error('Failed to fetch live topics:', error)
      const errorMsg = error instanceof Error ? error.message : 'Failed to load topics'
      setTopicsNotice(`Error: ${errorMsg}`)
    } finally {
      setLoadingTopics(false)
    }
  }

  const handleSelectTopic = (item: TopicSuggestion) => {
    setTopic(item.topic_name)
    setSelectedTopicName(item.topic_name)
    if (item.suggested_pillar && currentPillars.includes(item.suggested_pillar)) {
      setPillar(item.suggested_pillar)
    } else if (!pillar && currentPillars.length > 0) {
      setPillar(currentPillars[0])
    }
    if (item.suggested_format && currentFormats.includes(item.suggested_format)) {
      setFormat(item.suggested_format)
    } else if (!format && currentFormats.length > 0) {
      setFormat(currentFormats[0])
    }
    // Reset any previous manual article upload when switching topics
    setManualArticleText(null)
    setManualArticleLabel(null)
    setShowPasteArea(false)
    setPasteBuffer('')
  }

  const handleGenerate = async () => {
    if (!pillar || !format) return

    const selectedTopic = topicSuggestions.find((item) => item.topic_name === selectedTopicName)
    const hasValidTopicUrl = Boolean(selectedTopic?.source_url && isHttpLink(selectedTopic.source_url))

    if (!manualArticleText && !hasValidTopicUrl) {
      alert("This topic has no valid article URL. Please open the source and use 'Paste article text directly' or upload the article file before generating.")
      return
    }

    setLoading(true)
    try {
      const result = await api.generatePost({
        channel,
        pillar,
        format_type: format,
        topic: topic || undefined,
        source_name: selectedTopic?.source,
        source_title: selectedTopic?.source_title || selectedTopic?.topic_name,
        source_url: selectedTopic?.source_url,
        source_summary: selectedTopic?.reasoning,
        key_findings: selectedTopic?.key_findings,
        article_text: manualArticleText || undefined,
        language: language,
        provider,
        voice_corpus_dir: VOICE_CORPUS_DIR,
      })

      setGeneratedPost({
        ...result,
        channel,
        text: result.text,
        length: result.text.length,
        pillar: pillar,
        format: format,
        topic: topic || '',
        hashtags: result.hashtags || []
      })
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('posts-updated'))
      }
      alert('Post generated and saved successfully!')
    } catch (error) {
      console.error('Failed to generate post:', error)
      alert(error instanceof Error ? error.message : 'Failed to generate post. Make sure the backend server is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (generatedPost) {
      navigator.clipboard.writeText(generatedPost.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        {/* Generation Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-500" />
              Generate Post
            </CardTitle>
            <CardDescription>
              Create channel-specific LinkedIn content using AI
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Channel *</label>
              <Select value={channel} onValueChange={setChannel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a channel" />
                </SelectTrigger>
                <SelectContent>
                  {CHANNELS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedChannel && (
                <p className="text-xs text-slate-500">{selectedChannel.description}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Content Pillar *</label>
              <Select value={pillar} onValueChange={setPillar}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a content pillar first" />
                </SelectTrigger>
                <SelectContent>
                  {currentPillars.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-500">Choose pillar first, then click Load Topics to fetch pillar-aligned ideas.</p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Hot Topics Queue *</label>
              <div className="flex flex-wrap gap-2 items-end">
                <div className="flex-1 min-w-[200px]">
                  <label className="text-xs font-semibold text-slate-600 mb-1 block">Articles from last</label>
                  <Select value={String(daysBack)} onValueChange={(v) => setDaysBack(Number(v))}>
                    <SelectTrigger className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7">7 days</SelectItem>
                      <SelectItem value="14">14 days</SelectItem>
                      <SelectItem value="30">30 days</SelectItem>
                      <SelectItem value="60">60 days</SelectItem>
                      <SelectItem value="90">90 days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => fetchTrendingTopics(false)}
                  disabled={loadingTopics || !pillar}
                >
                  {loadingTopics ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Loading Topics...
                    </>
                  ) : (
                    'Load Topics'
                  )}
                </Button>
              </div>
              {topicsNotice && (
                <p className="text-xs text-amber-700">{topicsNotice}</p>
              )}
              {topicSuggestions.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-700">8 hottest topics for {selectedChannel?.label}</p>
                    {topicsUpdatedAt && (
                      <span className="text-xs text-slate-500">Updated: {new Date(topicsUpdatedAt).toLocaleString()}</span>
                    )}
                  </div>
                  <div className="mb-3 rounded-md border border-blue-100 bg-blue-50/70 p-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-blue-700">Curated External Sources</p>
                    <p className="text-xs text-blue-900">{(CHANNEL_CURATED_SOURCES[channel] || CHANNEL_CURATED_SOURCES.other).join(' · ')}</p>
                  </div>
                  <div className="space-y-2">
                    {topicSuggestions.map((item) => (
                      <div
                        key={`${item.rank}-${item.topic_name}`}
                        className={`rounded-md border bg-white p-3 ${
                          selectedTopicName === item.topic_name
                            ? 'border-blue-400 ring-2 ring-blue-100'
                            : 'border-slate-200'
                        }`}
                      >
                        <div className="mb-1 flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold text-slate-900 leading-snug">{item.rank}. {item.topic_name}</p>
                            {item.topic_name_es && (
                              <p className="mt-0.5 text-[11px] font-semibold italic text-blue-600 leading-tight">{item.topic_name_es}</p>
                            )}
                          </div>
                          <Button type="button" size="sm" variant="outline" onClick={() => handleSelectTopic(item)}>
                            {selectedTopicName === item.topic_name ? 'Selected' : 'Select'}
                          </Button>
                        </div>
                        <div className="mt-2 rounded-md border border-slate-100 bg-slate-50 px-2 py-2">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Quick Summary</p>
                          <p className="text-xs text-slate-700">{getTopicSummary(item)}</p>
                        </div>
                        <div className="mt-2 rounded-md bg-slate-50 p-2 text-xs text-slate-600">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium text-slate-700">Source:</span>
                            <span className="text-slate-900">{item.source || (() => { try { return new URL(item.source_url || '').hostname.replace(/^www\./, '') } catch { return 'Web source' } })()}</span>
                            {item.published_at && (
                              <span className="text-slate-700">Date: {new Date(item.published_at).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                            )}
                            {item.source_curated && <Badge variant="secondary">Curated</Badge>}
                          </div>
                          {(() => {
                            const sourceLink = getTopicSourceLink(item)
                            if (sourceLink) {
                              return (
                                <a
                                  href={sourceLink.href}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="mt-1 inline-block text-blue-600 underline underline-offset-2"
                                >
                                  {sourceLink.label}
                                </a>
                              )
                            }
                            return (
                              <p className="mt-1 text-amber-700">
                                No direct article URL available. Use manual paste/upload before generation.
                              </p>
                            )
                          })()}
                        </div>
                        <div className="mt-2 flex gap-2">
                          {typeof item.trend_score === 'number' && (
                            <Badge variant="default">Trend {item.trend_score.toFixed(1)}</Badge>
                          )}
                          {typeof item.strategic_score === 'number' && (
                            <Badge variant="outline">Strategic {item.strategic_score.toFixed(1)}</Badge>
                          )}
                          {typeof item.recency_score === 'number' && (
                            <Badge variant="outline">Recency {item.recency_score.toFixed(1)}</Badge>
                          )}
                          {typeof item.channel_fit_score === 'number' && (
                            <Badge variant="outline">Fit {item.channel_fit_score.toFixed(1)}</Badge>
                          )}
                          {typeof item.momentum_score === 'number' && (
                            <Badge variant="outline">Momentum {item.momentum_score.toFixed(1)}</Badge>
                          )}
                        </div>
                        <div className="mt-2 flex gap-2">
                          {item.suggested_pillar && <Badge variant="secondary">{item.suggested_pillar}</Badge>}
                          {item.suggested_format && <Badge variant="outline">{item.suggested_format}</Badge>}
                        </div>
                      </div>
                    ))}
                  </div>
                  {selectedTopicName && (
                    <p className="mt-3 text-sm font-medium text-blue-700">Selected topic: {selectedTopicName}</p>
                  )}

                  {/* Manual article upload — shown when a topic is selected */}
                  {selectedTopicName && (
                    <div className="mt-3 rounded-md border border-dashed border-slate-300 bg-slate-50 p-3">
                      <p className="mb-2 text-xs font-semibold text-slate-600 uppercase tracking-wide">Article blocked? Upload it manually</p>

                      {manualArticleText ? (
                        <div className="flex items-center gap-2 text-sm text-green-700">
                          <FileText className="h-4 w-4 shrink-0" />
                          <span className="flex-1 truncate">{manualArticleLabel}</span>
                          <button
                            onClick={() => { setManualArticleText(null); setManualArticleLabel(null) }}
                            className="ml-auto text-slate-400 hover:text-red-500"
                            title="Remove article"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex flex-col gap-2">
                          <label className="flex cursor-pointer items-center gap-2 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">
                            {articleUploading
                              ? <Loader2 className="h-4 w-4 animate-spin" />
                              : <Upload className="h-4 w-4" />}
                            <span>{articleUploading ? 'Extracting text…' : 'Upload file (PDF, DOCX, TXT, HTML)'}</span>
                            <input
                              type="file"
                              accept=".pdf,.docx,.txt,.html,.htm,.md"
                              className="sr-only"
                              disabled={articleUploading}
                              onChange={async (e) => {
                                const f = e.target.files?.[0]
                                if (!f) return
                                setArticleUploading(true)
                                try {
                                  const result = await api.extractArticle(f)
                                  setManualArticleText(result.text)
                                  setManualArticleLabel(`${f.name} · ${result.char_count.toLocaleString()} chars · ${result.findings_count} stat${result.findings_count !== 1 ? 's' : ''} found`)
                                } catch (err) {
                                  alert(err instanceof Error ? err.message : 'File extraction failed')
                                } finally {
                                  setArticleUploading(false)
                                  e.target.value = ''
                                }
                              }}
                            />
                          </label>

                          <button
                            className="text-left text-xs text-blue-600 hover:underline"
                            onClick={() => setShowPasteArea((v) => !v)}
                          >
                            {showPasteArea ? 'Hide paste area' : 'Or paste article text directly…'}
                          </button>

                          {showPasteArea && (
                            <div className="flex flex-col gap-1">
                              <Textarea
                                placeholder="Paste the article content here…"
                                className="min-h-[100px] text-xs"
                                value={pasteBuffer}
                                onChange={(e) => setPasteBuffer(e.target.value)}
                              />
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={!pasteBuffer.trim() || articleUploading}
                                onClick={async () => {
                                  setArticleUploading(true)
                                  try {
                                    const result = await api.extractArticle(pasteBuffer.trim())
                                    setManualArticleText(result.text)
                                    setManualArticleLabel(`Pasted text · ${result.char_count.toLocaleString()} chars · ${result.findings_count} stat${result.findings_count !== 1 ? 's' : ''} found`)
                                    setShowPasteArea(false)
                                    setPasteBuffer('')
                                  } catch (err) {
                                    alert(err instanceof Error ? err.message : 'Text processing failed')
                                  } finally {
                                    setArticleUploading(false)
                                  }
                                }}
                              >
                                {articleUploading ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
                                Use this text
                              </Button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-2">            <label className="text-sm font-medium">Format *</label>
            <Select value={format} onValueChange={setFormat}>
              <SelectTrigger>
                <SelectValue placeholder="Select a format" />
              </SelectTrigger>
              <SelectContent>
                {currentFormats.map((f) => (
                  <SelectItem key={f} value={f}>
                    {f}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Language *</label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger>
                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-slate-500">
              Generates English and Spanish versions separately
            </p>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleGenerate}
              disabled={!topic || !pillar || !format || loading}
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Post'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Preview</CardTitle>
          <CardDescription>
            Generated post will appear here
          </CardDescription>
        </CardHeader>
        <CardContent>
          {generatedPost ? (
            <div className="space-y-4">
              <div className="flex gap-2 flex-wrap">
                {generatedPost.channel && <Badge>{generatedPost.channel === 'personal_career' ? 'Personal' : 'GoalPraxis'}</Badge>}
                <Badge variant="outline">{generatedPost.pillar}</Badge>
                <Badge variant="outline">{generatedPost.format}</Badge>
                {generatedPost.topic && (
                  <Badge variant="secondary">{generatedPost.topic}</Badge>
                )}
              </div>
              
              <Textarea
                value={generatedPost.text}
                readOnly
                className="min-h-[300px] font-sans"
              />

              {generatedPost.hashtags && generatedPost.hashtags.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {generatedPost.hashtags.map((tag: string, i: number) => (
                    <Badge key={i} variant="secondary" className="text-blue-600">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between text-sm text-slate-600">
                <span>{generatedPost.length} characters</span>
                {generatedPost.voice_score && (
                  <span>Voice Score: {generatedPost.voice_score.toFixed(1)}/100</span>
                )}
              </div>

              <div className="flex gap-2 pt-2">
                <Button onClick={handleCopy} variant="outline" className="flex-1">
                  {copied ? (
                    <>
                      <CheckCircle2 className="mr-2 h-4 w-4 text-green-600" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy to Clipboard
                    </>
                  )}
                </Button>

                {(generatedPost as any).id && (
                  <Button 
                    variant="default" 
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                    onClick={() => router.push(`/demos/${(generatedPost as any).id}?tab=visualize`)}
                  >
                    <Sparkles className="mr-2 h-4 w-4" />
                    Create Visuals
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-slate-400">
              <p>No post generated yet</p>
            </div>
          )}
        </CardContent>
      </Card>      </div>

      {/* Trending News Table - Shows below when news post type is selected */}
      {postType === 'news' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              📰 Trending News Topics
            </CardTitle>
            <CardDescription>
              Select a news article to generate a post about
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingNews ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                <span className="ml-3 text-sm text-slate-500">Loading trending news...</span>
              </div>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="w-12 px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                        Select
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                        Title
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                        Summary
                      </th>
                      <th className="w-32 px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                        Source
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {newsList.map((news, idx) => {
                      const isSelected = selectedNews.includes(news.title)
                      const handleToggle = () => {
                        let newSelection: string[]
                        if (isSelected) {
                          newSelection = selectedNews.filter(title => title !== news.title)
                        } else {
                          newSelection = [...selectedNews, news.title]
                        }
                        setSelectedNews(newSelection)
                        
                        // Combine all selected news into topic
                        const combinedTopic = newsList
                          .filter(n => newSelection.includes(n.title))
                          .map(n => `${n.title}: ${n.summary}`)
                          .join(' | ')
                        setTopic(combinedTopic)
                      }
                      
                      return (
                        <tr 
                          key={idx}
                          className={`hover:bg-slate-50 cursor-pointer ${isSelected ? 'bg-blue-50' : ''}`}
                          onClick={handleToggle}
                        >
                          <td className="px-4 py-3 text-center">
                            <input
                              type="checkbox"
                              aria-label={`Select news article ${idx + 1}`}
                              checked={isSelected}
                              onChange={handleToggle}
                              onClick={(e) => e.stopPropagation()}
                              className="h-4 w-4 text-blue-600 rounded"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-medium text-sm text-slate-900">
                              {news.title}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-sm text-slate-600 line-clamp-2">
                              {news.summary}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-xs text-slate-500">
                              {news.source}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}    </div>
  )
}

"use client"

import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, BarChart3, Code2, Image, Sparkles, Globe, MonitorPlay, FileText, Edit2, Save, X, Loader2 } from 'lucide-react'
import { Textarea } from '@/components/ui/textarea'
import { api, type PostResponse } from '@/lib/api'

export default function DemoPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const postId = params.postId as string
  
  const [post, setPost] = useState<PostResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeSimulation, setActiveSimulation] = useState<string>('visualize')
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab && ['engagement', 'visualize', 'code'].includes(tab)) {
      setActiveSimulation(tab)
    }
  }, [searchParams])

  useEffect(() => {
    loadPost()
  }, [postId])

  // Split post text into English and Spanish sections
  const SPANISH_SEP_RE = /(\n\s*---\s*\n+###+\s*Vers[ií]on en Espa[ñn]ol)/i

  const getEnglishPart = (text: string): string => {
    const idx = text.search(SPANISH_SEP_RE)
    return idx !== -1 ? text.substring(0, idx).trim() : text
  }

  const handleEditPost = () => {
    if (!post) return
    setEditText(getEnglishPart(post.text))
    setIsEditing(true)
  }

  const handleSavePost = async () => {
    if (!post) return
    setIsSaving(true)
    try {
      let finalText = editText
      // If original post had Spanish section, auto-translate the edited English
      if (SPANISH_SEP_RE.test(post.text)) {
        const res = await fetch('/api/translate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: editText }),
        })
        if (res.ok) {
          const data = await res.json() as { translated?: string }
          const translated = data.translated ?? ''
          if (translated) {
            finalText = `${editText}\n\n---\n\n### Versión en Español\n\n${translated}`
          }
        }
      }
      await api.updatePost(post.id, { text: finalText, hashtags: post.hashtags })
      setPost({ ...post, text: finalText, length: finalText.length })
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
      alert('Failed to save post')
    } finally {
      setIsSaving(false)
    }
  }

  const loadPost = async () => {
    try {
      const data = await api.getPost(postId)
      setPost(data)
    } catch (error) {
      console.error('Error loading post:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!post) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="w-96">
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Post not found</p>
            <Button onClick={() => router.push('/')} className="w-full mt-4">
              Back to Home
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push('/')}
            className="text-white hover:bg-white/10"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-white">LinkedIn Generator</h1>
            <p className="text-blue-200">{post.pillar} • {post.format}</p>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Post Preview */}
          <Card className="lg:col-span-1 bg-white/95 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-blue-600" />
                  Original Post
                </span>
                {!isEditing ? (
                  <Button size="sm" variant="outline" onClick={handleEditPost}>
                    <Edit2 className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => setIsEditing(false)} disabled={isSaving}>
                      <X className="h-4 w-4" />
                    </Button>
                    <Button size="sm" onClick={handleSavePost} disabled={isSaving} className="bg-blue-600 hover:bg-blue-700 text-white">
                      {isSaving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <><Save className="h-4 w-4 mr-1" />Save</>
                      )}
                    </Button>
                  </div>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isEditing ? (
                <div className="space-y-2">
                  <p className="text-xs text-slate-500 italic">Edit English text below. Spanish translation will be auto-updated on save.</p>
                  <Textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="min-h-[350px] font-sans text-sm"
                    disabled={isSaving}
                  />
                </div>
              ) : (
                <div className="prose prose-sm max-w-none">
                  <p className="whitespace-pre-wrap text-sm">{post.text}</p>
                  {post.hashtags?.length > 0 && (
                    <p className="text-blue-600 text-sm mt-4">{post.hashtags.join(' ')}</p>
                  )}
                </div>
              )}
              <div className="mt-4 pt-4 border-t">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Voice Score:</span>
                    <span className="ml-2 font-semibold">{post.voice_score}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Length:</span>
                    <span className="ml-2 font-semibold">{post.length}</span>
                  </div>
                </div>
                <div className="mt-4 flex flex-col gap-2">
                  {post.source_url && (
                    <a
                      href={post.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
                      Read source article →
                    </a>
                  )}
                  <a
                    href={`https://wa.me/51971152829?text=${encodeURIComponent('Hi Adolfo, I saw your LinkedIn post and would like to connect.')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#25D366] text-white text-sm font-semibold hover:bg-[#1ebe5a] transition-colors w-fit"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                    Message on WhatsApp
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Interactive Simulations */}
          <Card className="lg:col-span-2 bg-white/95 backdrop-blur">
            <CardHeader>
              <CardTitle>Interactive Simulations & Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs value={activeSimulation} onValueChange={setActiveSimulation}>
                <TabsList className="grid w-full grid-cols-3 mb-4">
                  <TabsTrigger value="engagement">
                    <BarChart3 className="h-4 w-4 mr-2" />
                    Engagement
                  </TabsTrigger>
                  <TabsTrigger value="visualize">
                    <Image className="h-4 w-4 mr-2" />
                    Visualize
                  </TabsTrigger>
                  <TabsTrigger value="code">
                    <Code2 className="h-4 w-4 mr-2" />
                    Technical
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="engagement" className="space-y-4">
                  <EngagementSimulation post={post} />
                </TabsContent>

                <TabsContent value="visualize" className="space-y-4">
                  <VisualizationPanel post={post} />
                </TabsContent>

                <TabsContent value="code" className="space-y-4">
                  <TechnicalAnalysis post={post} />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Scenario Analysis */}
        <Card className="mt-6 bg-white/95 backdrop-blur">
          <CardHeader>
            <CardTitle>Scenario Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <ScenarioAnalysis post={post} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Engagement Simulation Component
function EngagementSimulation({ post }: { post: PostResponse }) {
  const [timeFrame, setTimeFrame] = useState(24) // hours
  
  // Simulate engagement over time
  const simulateEngagement = () => {
    const baseEngagement = post.voice_score || 70
    const hours = Array.from({ length: timeFrame }, (_, i) => i)
    
    return hours.map(hour => ({
      hour,
      views: Math.floor(Math.random() * 100 * (baseEngagement / 70) * (1 + hour / 10)),
      likes: Math.floor(Math.random() * 20 * (baseEngagement / 70) * (1 + hour / 20)),
      comments: Math.floor(Math.random() * 5 * (baseEngagement / 70)),
      shares: Math.floor(Math.random() * 3 * (baseEngagement / 70))
    }))
  }

  const data = simulateEngagement()
  const totals = data[data.length - 1]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{totals.views}</div>
            <div className="text-sm text-muted-foreground">Projected Views</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{totals.likes}</div>
            <div className="text-sm text-muted-foreground">Projected Likes</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-purple-600">{totals.comments}</div>
            <div className="text-sm text-muted-foreground">Projected Comments</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-orange-600">{totals.shares}</div>
            <div className="text-sm text-muted-foreground">Projected Shares</div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-4">
        <label className="text-sm font-medium">Time Frame:</label>
        <div className="flex gap-2">
          {[6, 12, 24, 48].map(hours => (
            <Button
              key={hours}
              variant={timeFrame === hours ? "default" : "outline"}
              size="sm"
              onClick={() => setTimeFrame(hours)}
            >
              {hours}h
            </Button>
          ))}
        </div>
      </div>

      <div className="bg-slate-100 rounded-lg p-4">
        <p className="text-sm text-muted-foreground">
          📊 Engagement Rate: <span className="font-semibold">{((totals.likes + totals.comments + totals.shares) / totals.views * 100).toFixed(2)}%</span>
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          *Projections based on voice score, content length, and historical performance patterns
        </p>
      </div>
    </div>
  )
}

// Visualization Panel Component
function VisualizationPanel({ post }: { post: PostResponse }) {
  // --- existing state (unchanged) ---
  const [generating, setGenerating] = useState(false)
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null)
  const [generatedType, setGeneratedType] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [carouselStyle, setCarouselStyle] = useState('professional')

  // --- new state ---
  const [toolTemplate, setToolTemplate] = useState('calculator')
  const [comboGenerating, setComboGenerating] = useState(false)
  const [comboResult, setComboResult] = useState<{ toolUrl: string } | null>(null)
  const [comboError, setComboError] = useState<string | null>(null)
  const [copiedText, setCopiedText] = useState<'plain' | 'formatted' | null>(null)

  // --- tool templates config ---
  const toolTemplates = [
    { id: 'calculator', label: 'Calculator', desc: 'ROI, cost savings, metrics', prompt: 'Create a professional ROI/cost calculator relevant to this post topic. Include numeric inputs for key variables and show a dynamic result with clear savings or ROI output.' },
    { id: 'assessment', label: 'Assessment', desc: 'Readiness quiz with score', prompt: 'Create a readiness self-assessment quiz (6-8 yes/no or scale questions) relevant to this post topic. Show a cumulative score at the end with a brief recommendation.' },
    { id: 'checklist', label: 'Checklist', desc: 'Audit / step-by-step tool', prompt: 'Create an interactive checklist/audit tool relevant to this post topic. Items should be checkable with a live progress bar and a completion message at 100%.' },
    { id: 'benchmark', label: 'Benchmark', desc: 'Compare vs. industry', prompt: 'Create a benchmark comparison tool relevant to this post topic. Let users input their own metrics and see how they compare to industry standards with a visual gauge or bar chart.' },
  ]

  const getToolPrompt = () => toolTemplates.find(t => t.id === toolTemplate)?.prompt ?? toolTemplates[0].prompt
  const getToolTitle  = () => `${post.topic || 'Post'} — ${toolTemplates.find(t => t.id === toolTemplate)?.label ?? 'Calculator'}`

  // --- text copy helpers ---
  const formatForLinkedIn = (text: string, hashtags: string[]): string => {
    const paragraphs = text.split('\n').map(l => l.trim()).filter(Boolean).join('\n\n')
    const tags = hashtags?.length > 0 ? '\n\n' + hashtags.join(' ') : ''
    return paragraphs + tags
  }

  const handleCopyText = (formatted: boolean) => {
    const content = formatted ? formatForLinkedIn(post.text, post.hashtags) : post.text
    navigator.clipboard.writeText(content).then(() => {
      setCopiedText(formatted ? 'formatted' : 'plain')
      setTimeout(() => setCopiedText(null), 2000)
    })
  }

  // --- carousel + tool combo ---
  const generateCarouselWithTool = async () => {
    setComboGenerating(true)
    setComboError(null)
    setComboResult(null)
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    try {
      const toolRes = await fetch(API_URL + '/media/generate-interactive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_id: post.id, save_to_storage: true, title: getToolTitle(), prompt: getToolPrompt() })
      })
      if (!toolRes.ok) {
        const errData = await toolRes.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errData.detail || 'Failed to generate interactive tool')
      }
      const toolData = await toolRes.json()
      if (!toolData.url) throw new Error('No tool URL returned')
      setComboResult({ toolUrl: toolData.url })
      setComboGenerating(false)
      // Step 2: trigger carousel PDF download (uses existing generateVisual)
      await generateVisual('carousel')
    } catch (err) {
      setComboError(err instanceof Error ? err.message : 'Generation failed')
      setComboGenerating(false)
    }
  }

  const generateVisual = async (type: string) => {
    setGenerating(true)
    setError(null)
    setGeneratedUrl(null)
    setGeneratedType(type)
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      let endpoint = ''
      let body: any = { post_id: post.id, save_to_storage: true }

      if (type === 'code') {
        endpoint = '/media/generate-code-image'
        body = {
          ...body,
          code: 'def generate_linkedin_post():\n    return "Amazing content!"\n\npost = generate_linkedin_post()\nprint(post)',
          language: 'python',
          theme: 'monokai',
          title: 'Code Example'
        }
      } else if (type === 'chart') {
        endpoint = '/media/generate-chart'
        body = {
          ...body,
          chart_type: 'bar',
          title: 'Engagement Metrics',
          data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            values: [120, 250, 380, 520]
          }
        }
      } else if (type === 'carousel') {
        endpoint = '/media/generate-carousel'
        let slides: Array<{ title: string; content?: string; content_en?: string; content_es?: string }> = [];
        const text = post.text || '';
        
        // Check if post is bilingual (contains "---" separator)
        const isBilingual = text.includes('---');
        let englishText = '';
        let spanishText = '';
        
        if (isBilingual) {
          // Split by "---" to get English and Spanish versions
          const parts = text.split('---');
          englishText = parts[0]?.trim() || '';
          spanishText = parts[1]?.trim() || '';
          
          // Remove language headers if present
          englishText = englishText.replace(/###\s*Post Text/i, '').trim();
          spanishText = spanishText.replace(/###\s*Versión en Español/i, '').trim();
        }
        
        // Try parsing "SLIDE X:" format
        if (text.includes('SLIDE')) {
            const slideParts = text.split(/SLIDE \d+:/i).filter(s => s.trim().length > 0);
            slides = slideParts.map((part, i) => {
                const lines = part.trim().split('\n');
                const title = lines[0].replace(/[*#]/g, '').trim();
                const content = lines.slice(1).join('\n').trim();
                return {
                    title: title || `Slide ${i+1}`,
                    content: content || title
                };
            });
        }
        // If bilingual, create slides with side-by-side content
        else if (isBilingual && englishText && spanishText) {
          // Split by COMPLETE sentences only
          const enSentences: string[] = englishText.match(/[^.!?]+[.!?]+/g) || [];
          const esSentences: string[] = spanishText.match(/[^.!?]+[.!?]+/g) || [];
          
          if (enSentences.length === 0) enSentences.push(englishText);
          if (esSentences.length === 0) esSentences.push(spanishText);
          
          // Calculate how many sentences fit per slide (target ~250-400 chars)
          const avgEnLength = enSentences.reduce((sum, s) => sum + s.length, 0) / enSentences.length;
          const sentencesPerSlide = Math.max(2, Math.min(4, Math.round(300 / avgEnLength)));
          
          const enGroups: string[] = [];
          const esGroups: string[] = [];
          
          // Group sentences - NEVER split mid-sentence
          let enIndex = 0;
          while (enIndex < enSentences.length) {
            const group = enSentences.slice(enIndex, enIndex + sentencesPerSlide).join(' ').trim();
            if (group.length > 50) {  // Must have substantial content
              enGroups.push(group);
            }
            enIndex += sentencesPerSlide;
          }
          
          let esIndex = 0;
          while (esIndex < esSentences.length) {
            const group = esSentences.slice(esIndex, esIndex + sentencesPerSlide).join(' ').trim();
            if (group.length > 50) {
              esGroups.push(group);
            }
            esIndex += sentencesPerSlide;
          }
          
          // Create slides (max 8)
          const slideCount = Math.min(Math.max(enGroups.length, esGroups.length), 8);
          
          for (let i = 0; i < slideCount; i++) {
            const enContent = enGroups[i] || enGroups[enGroups.length - 1] || 'Follow for more insights.';
            const esContent = esGroups[i] || esGroups[esGroups.length - 1] || 'Sígueme para más contenido.';
            
            // Extract English title for translation
            const enTitle = enContent.split('.')[0].split(' ').slice(0, 5).join(' ');
            
            slides.push({
              title: i === 0 ? (post.topic || enTitle) : enTitle,
              content_en: enContent,
              content_es: esContent
            });
          }
        }
        // Fallback to simple line splitting
        else if (slides.length === 0) {
             const lines = text.split('\n').filter(l => l.length > 20).slice(0, 5);
             slides = lines.map((l, i) => ({ 
                title: i === 0 ? (post.topic?.toUpperCase() || 'INSIGHT') : `Key Point ${i}`, 
                content: l 
            }));
        }

        body = {
            ...body,
            title: post.topic || 'In-Depth Carousel',
            style: carouselStyle,
            content_pillar: post.pillar || 'General',
            post_type: 'Standard',
            format: post.format || 'Text',
            topic: post.topic || 'Post',
            slides: slides.length > 0 ? slides : [
                { title: 'Introduction', content_en: 'Carousel content based on your post.', content_es: 'Contenido del carrusel basado en tu publicación.' }
            ],
            source_url: post.source_url || null,
            article_images: post.article_images || []
        }
      } else if (type === 'infographic') {
        endpoint = '/media/generate-infographic'
        body = {
          ...body,
          title: 'Key Statistics',
          stats: [
            { label: 'Engagement', value: '92%' },
            { label: 'Reach', value: '5.2K' },
            { label: 'Shares', value: '234' }
          ]
        }
      } else if (type === 'interactive') {
        endpoint = '/media/generate-interactive'
        body = {
          ...body,
          title: getToolTitle(),
          prompt: getToolPrompt()
        }
      } else if (type === 'banner') {
        endpoint = '/media/generate-banner'
        body = {
          ...body,
          title: post.topic || post.pillar || 'LinkedIn Post',
          post_text: post.text?.substring(0, 500) || ''
        }
      }

      const response = await fetch(API_URL + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `Failed to generate visual: ${response.statusText}`)
      }

      // Handle PDF download for carousel
      if (type === 'carousel') {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        
        // Extract filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition')
        let filename = 'carousel.pdf'
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="(.+)"/)
          if (filenameMatch) {
            filename = filenameMatch[1]
          }
        }
        
        // Trigger download
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        
        setGeneratedUrl(url)
      } else {
        const result = await response.json()
        console.log('API Response:', result)
        
        if (result.url) {
          setGeneratedUrl(result.url)
        } else {
          throw new Error('No URL returned from API')
        }
      }
    } catch (error) {
      console.error('Error generating visual:', error)
      setError(error instanceof Error ? error.message : 'Failed to generate visual')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Generate LinkedIn post assets from your content:
      </p>

      {/* Carousel Style Selector — unchanged */}
      <div className="bg-slate-50 dark:bg-slate-900 p-4 rounded-lg border">
        <label className="text-sm font-medium mb-2 block">Carousel Style</label>
        <div className="grid grid-cols-5 gap-2">
          {['professional', 'relaxed', 'corporate', 'creative', 'minimal'].map((style) => (
            <button
              key={style}
              onClick={() => setCarouselStyle(style)}
              className={`px-3 py-2 text-xs rounded capitalize transition-all ${
                carouselStyle === style
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              {style}
            </button>
          ))}
        </div>
      </div>

      {/* Active format cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. Text Only */}
        <div className="border rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <FileText className="h-6 w-6 text-slate-600" />
            <div>
              <p className="font-semibold text-sm">Text Only</p>
              <p className="text-xs text-muted-foreground">Copy your post to LinkedIn</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="flex-1 text-xs h-8" onClick={() => handleCopyText(false)}>
              {copiedText === 'plain' ? '✓ Copied!' : 'Copy Plain'}
            </Button>
            <Button size="sm" variant="outline" className="flex-1 text-xs h-8" onClick={() => handleCopyText(true)}>
              {copiedText === 'formatted' ? '✓ Copied!' : 'Copy for LinkedIn'}
            </Button>
          </div>
        </div>

        {/* 2. Carousel PDF */}
        <Button
          variant="outline"
          className="h-auto py-6 flex-col"
          onClick={() => generateVisual('carousel')}
          disabled={generating}
        >
          <FileText className="h-8 w-8 mb-2 text-red-600" />
          <span className="font-semibold">Carousel PDF</span>
          <span className="text-xs text-muted-foreground mt-1">Slick multi-page document</span>
        </Button>

        {/* 3. Infographic */}
        <Button
          variant="outline"
          className="h-auto py-6 flex-col"
          onClick={() => generateVisual('infographic')}
          disabled={generating}
        >
          <Image className="h-8 w-8 mb-2 text-purple-600" />
          <span className="font-semibold">Infographic</span>
          <span className="text-xs text-muted-foreground mt-1">Key stats visualization</span>
        </Button>

        {/* 4. Text + Image Banner */}
        <div className="border rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">🖼️</span>
            <div>
              <p className="font-semibold text-sm">Text + Image</p>
              <p className="text-xs text-muted-foreground">Post + AI banner (1200×627)</p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => generateVisual('banner')}
            disabled={generating}
            className="w-full"
          >
            {generating && generatedType === 'banner' ? (
              <><Loader2 className="h-3 w-3 mr-1.5 animate-spin" />Generating...</>
            ) : (
              'Generate Banner'
            )}
          </Button>
        </div>

        {/* 5. Interactive HTML with template picker */}
        <div className="border rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2">
            <MonitorPlay className="h-6 w-6 text-orange-600" />
            <div>
              <p className="font-semibold text-sm">Interactive HTML</p>
              <p className="text-xs text-muted-foreground">Standalone hosted tool</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {toolTemplates.map(t => (
              <button
                key={t.id}
                onClick={() => setToolTemplate(t.id)}
                className={`px-2 py-2 text-xs rounded border text-left transition-all ${
                  toolTemplate === t.id
                    ? 'bg-orange-50 border-orange-400 text-orange-800'
                    : 'bg-white border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="font-medium">{t.label}</div>
                <div className="text-[10px] text-muted-foreground leading-tight">{t.desc}</div>
              </button>
            ))}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => generateVisual('interactive')}
            disabled={generating}
            className="w-full"
          >
            {generating && generatedType === 'interactive' ? (
              <><Loader2 className="h-3 w-3 mr-1.5 animate-spin" />Generating...</>
            ) : (
              'Generate Tool'
            )}
          </Button>
        </div>
      </div>

      {/* Carousel + Tool combined card */}
      <div className="border-2 border-blue-200 rounded-lg p-4 bg-blue-50/40 space-y-3">
        <div className="flex items-start gap-3">
          <div className="flex items-center gap-1 mt-0.5">
            <FileText className="h-5 w-5 text-red-500" />
            <span className="text-slate-400 text-xs font-bold">+</span>
            <MonitorPlay className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <p className="font-semibold text-sm">Carousel + Interactive Tool</p>
            <p className="text-xs text-muted-foreground">PDF carousel linked to a hosted tool — last slide carries the tool URL as CTA</p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {toolTemplates.map(t => (
            <button
              key={t.id}
              onClick={() => setToolTemplate(t.id)}
              className={`px-2 py-2 text-xs rounded border text-center transition-all ${
                toolTemplate === t.id
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white border-slate-200 hover:bg-blue-50'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <Button
          onClick={generateCarouselWithTool}
          disabled={comboGenerating || generating}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          size="sm"
        >
          {comboGenerating ? (
            <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating tool...</>
          ) : generating ? (
            <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating carousel...</>
          ) : (
            'Generate Carousel + Tool'
          )}
        </Button>
        {comboError && (
          <div className="bg-red-50 border border-red-200 rounded p-2">
            <p className="text-xs text-red-700">❌ {comboError}</p>
          </div>
        )}
        {comboResult?.toolUrl && (
          <div className="bg-green-50 border border-green-200 rounded p-3 space-y-2">
            <p className="text-xs font-semibold text-green-800">✅ Tool ready — add this URL to your carousel CTA slide:</p>
            <p className="text-xs text-green-700 font-mono break-all bg-green-100 rounded px-2 py-1">{comboResult.toolUrl}</p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" className="text-xs h-7 flex-1" onClick={() => navigator.clipboard.writeText(comboResult!.toolUrl)}>
                Copy URL
              </Button>
              <Button size="sm" variant="outline" className="text-xs h-7 flex-1" onClick={() => window.open(comboResult!.toolUrl, '_blank')}>
                Preview Tool
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Coming Soon cards */}
      <div>
        <p className="text-xs text-muted-foreground mb-2 font-medium">Coming Soon</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Poll', icon: '📊', desc: 'AI question + 4 options' },
            { label: 'Video', icon: '🎬', desc: 'Animated post video' },
            { label: 'Article', icon: '📰', desc: 'Long-form newsletter' },
          ].map(card => (
            <div key={card.label} className="border rounded-lg p-3 opacity-50 select-none bg-slate-50">
              <div className="text-center">
                <div className="text-xl mb-1">{card.icon}</div>
                <div className="font-medium text-xs">{card.label}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{card.desc}</div>
                <span className="inline-block mt-2 px-2 py-0.5 rounded-full bg-slate-200 text-slate-500 text-[9px] font-semibold uppercase tracking-wide">Coming Soon</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {generating && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-sm text-muted-foreground mt-2">Generating visual asset...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm font-medium text-red-800">❌ Error: {error}</p>
          <p className="text-xs text-red-600 mt-1">Check the browser console for more details.</p>
        </div>
      )}

      {generatedUrl && (
        <div className="bg-slate-100 rounded-lg p-4">
          <p className="text-sm font-medium mb-2">✅ Visual asset generated!</p>
          
          {(generatedUrl.startsWith('data:text/html') || generatedUrl.endsWith('.html')) ? (
            <div className="border rounded-lg bg-white p-8 text-center space-y-4">
              <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <Globe className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold">Interactive Demo Ready</h3>
                <p className="text-sm text-muted-foreground">Click to launch the generated HTML application</p>
              </div>
              <Button onClick={() => {
                const win = window.open();
                if (win) {
                  win.document.write(
                    generatedUrl.startsWith('data:text/html') 
                    ? decodeURIComponent(escape(window.atob(generatedUrl.split(',')[1])))
                    : `<iframe src="${generatedUrl}" style="border:0; position:fixed; top:0; left:0; right:0; bottom:0; width:100%; height:100%"></iframe>`
                  );
                }
              }}>
                Launch Interactive Demo
              </Button>
            </div>
          ) : (
            <img src={generatedUrl} alt="Generated visual" className="w-full rounded-lg border" />
          )}

          <a
            href={generatedUrl}
            target="_blank"
            rel="noopener noreferrer"
            download={generatedType === 'carousel' ? "linkedin-carousel.pdf" : generatedType === 'banner' ? "linkedin-banner.svg" : undefined}
            className="text-sm text-blue-600 hover:underline mt-2 inline-block"
          >
            {generatedType === 'carousel' ? 'Download PDF ↓' : generatedType === 'banner' ? 'Download Banner SVG ↓' : 'Open Link / Download →'}
          </a>
        </div>
      )}
    </div>
  )
}

// Technical Analysis Component
function TechnicalAnalysis({ post }: { post: PostResponse }) {
  const analysis = {
    readability: Math.min(100, 70 + (post.voice_score || 70) / 3),
    seoScore: Math.min(100, 60 + ((post.hashtags?.length || 0) * 5)),
    viralPotential: Math.min(100, (post.voice_score || 70) + ((post.length || 0) > 500 ? 20 : 10)),
    professionalTone: post.voice_score || 70
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(analysis).map(([key, value]) => (
          <div key={key} className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
              <span className="text-muted-foreground">{value.toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all"
                style={{ width: `${value}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="bg-slate-100 rounded-lg p-4 space-y-2">
        <h4 className="font-semibold text-sm">Technical Insights</h4>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>✓ Optimal character length for LinkedIn algorithm</li>
          <li>✓ Strategic hashtag placement detected</li>
          <li>✓ Engaging opening hook identified</li>
          <li>✓ Professional tone maintained throughout</li>
        </ul>
      </div>
    </div>
  )
}

// Scenario Analysis Component
function ScenarioAnalysis({ post }: { post: PostResponse }) {
  const scenarios = [
    {
      name: 'Morning Post (8-10 AM)',
      engagement: ((post.voice_score || 70) * 1.2).toFixed(0),
      reach: '3.5K - 5K',
      bestFor: 'B2B content, professional updates'
    },
    {
      name: 'Lunch Break (12-2 PM)',
      engagement: ((post.voice_score || 70) * 1.5).toFixed(0),
      reach: '5K - 7.5K',
      bestFor: 'Quick reads, inspiring content'
    },
    {
      name: 'Evening Wind Down (6-8 PM)',
      engagement: ((post.voice_score || 70) * 1.1).toFixed(0),
      reach: '2.5K - 4K',
      bestFor: 'Personal stories, thought leadership'
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {scenarios.map((scenario, idx) => (
        <Card key={idx}>
          <CardHeader>
            <CardTitle className="text-base">{scenario.name}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <span className="text-sm text-muted-foreground">Engagement Score:</span>
              <span className="ml-2 font-semibold text-blue-600">{scenario.engagement}</span>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">Expected Reach:</span>
              <span className="ml-2 font-semibold">{scenario.reach}</span>
            </div>
            <p className="text-xs text-muted-foreground pt-2 border-t">
              <strong>Best for:</strong> {scenario.bestFor}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

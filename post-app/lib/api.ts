const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export type PostStatus = 'draft' | 'review' | 'approved' | 'scheduled' | 'published' | 'raw' | 'posted'

export interface GeneratePostRequest {
  channel?: string
  pillar: string
  format_type: string
  topic?: string
  source_name?: string
  source_title?: string
  source_url?: string
  source_summary?: string
  key_findings?: Array<{ finding: string; source_attribution: string }>
  article_text?: string
  voice_corpus_dir?: string
  language?: string
  provider?: string
}

export interface PostResponse {
  id: string
  channel?: string
  pillar: string
  format: string
  topic: string
  text: string
  hashtags: string[]
  voice_score: number
  length: number
  created_at: string
  status: PostStatus
  source_url?: string
  article_images?: string[]
}

export interface TopicSuggestion {
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

export interface TopicsResponse {
  channel: string
  topics: TopicSuggestion[]
  updated_at: string
}

export interface DashboardResponse {
  overall_health: number
  health_grade: string
  summary: {
    total_posts_30d: number
    posts_per_week: number
    consistency: string
    balance_status: string
  }
  pillar_balance: {
    total_posts: number
    period_days?: number
    balance: Record<string, {
      current: number
      target: number
      diff: number
      status: string
    }>
    recommendations: string[]
  }
  posting_cadence: {
    total_posts?: number
    posts_per_week: number
    avg_gap_days?: number
    max_gap_days?: number
    consistency: string
    recommendations: string[]
  }
  next_recommended_pillar: string
}

export interface StatsResponse {
  total_posts: number
  published: number
  drafts: number
  avg_voice_score: number
  health: {
    score: number
    grade: string
  }
  posting: {
    posts_per_week: number
    consistency: string
  }
}

export const api = {
  async extractArticle(fileOrText: File | string): Promise<{ text: string; char_count: number; findings_count: number; findings: Array<{ finding: string; source_attribution: string }> }> {
    const form = new FormData()
    if (typeof fileOrText === 'string') {
      form.append('text', fileOrText)
    } else {
      form.append('file', fileOrText)
    }
    const res = await fetch(`${API_URL}/articles/extract`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      let errorMsg = 'Failed to extract article text'
      try { const b = await res.json(); if (b.detail) errorMsg = b.detail } catch {}
      throw new Error(errorMsg)
    }
    return res.json()
  },

  async generatePost(data: GeneratePostRequest): Promise<PostResponse> {
    const res = await fetch(`${API_URL}/posts/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!res.ok) {
      let errorMsg = 'Failed to generate post'
      try {
        const errBody = await res.json()
        if (errBody.detail) errorMsg = errBody.detail
      } catch {}
      throw new Error(errorMsg)
    }
    return res.json()
  },

  async batchGenerate(count: number, pillar?: string): Promise<{ message: string; count: number }> {
    const res = await fetch(`${API_URL}/posts/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count, pillar }),
    })
    if (!res.ok) throw new Error('Failed to batch generate')
    return res.json()
  },

  async checkVoice(text: string): Promise<{ score: number; grade: string; issues: string[] }> {
    const res = await fetch(`${API_URL}/posts/check-voice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    if (!res.ok) throw new Error('Failed to check voice')
    return res.json()
  },

  async getStats(): Promise<any> {
    const res = await fetch(`${API_URL}/stats`)
    if (!res.ok) throw new Error('Failed to get stats')
    return res.json()
  },

  async getDashboard(): Promise<DashboardResponse> {
    const res = await fetch(`${API_URL}/dashboard`)
    if (!res.ok) throw new Error('Failed to get dashboard')
    return res.json()
  },

  async listPosts(limit: number = 100, channel?: string): Promise<PostResponse[]> {
    const channelQuery = channel ? `&channel=${encodeURIComponent(channel)}` : ''
    const res = await fetch(`${API_URL}/posts?limit=${limit}${channelQuery}`)
    if (!res.ok) throw new Error('Failed to load posts')
    return res.json()
  },

  async getPost(postId: string): Promise<PostResponse> {
    const res = await fetch(`${API_URL}/posts/${postId}`)
    if (!res.ok) throw new Error('Failed to load post')
    return res.json()
  },

  async updatePost(postId: string, data: { text: string; hashtags?: string[] }): Promise<PostResponse> {
    const res = await fetch(`${API_URL}/posts/${postId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error('Failed to update post')
    return res.json()
  },

  async updatePostStatus(postId: string, status: PostStatus): Promise<void> {
    const existingPost = await fetch(`${API_URL}/posts/${postId}`)
    if (!existingPost.ok) throw new Error('Failed to load post for status update')
    const post = await existingPost.json() as PostResponse

    const res = await fetch(`${API_URL}/posts/${postId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: post.text,
        hashtags: post.hashtags,
        status,
      }),
    })
    if (!res.ok) throw new Error('Failed to update post status')
  },

  async deletePost(postId: string): Promise<void> {
    const res = await fetch(`${API_URL}/posts/${postId}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error('Failed to delete post')
  },

  async getTrendingNews(category: string = 'technology', count: number = 10): Promise<any> {
    const res = await fetch(`${API_URL}/news/trending?category=${category}&count=${count}`)
    if (!res.ok) throw new Error('Failed to fetch trending news')
    return res.json()
  },

  async getTrendingTopics(channel: string, refresh: boolean = false, daysBack: number = 30): Promise<TopicsResponse> {
    const res = await fetch(`${API_URL}/topics/trending?channel=${encodeURIComponent(channel)}&refresh=${refresh}&days_back=${daysBack}`)
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || 'Failed to fetch trending topics')
    }
    return res.json()
  },

  async getLiveWebTopics(channel: string, count: number = 8, daysBack: number = 30, pillar?: string): Promise<TopicsResponse> {
    const params = new URLSearchParams({ channel, count: String(count), days_back: String(daysBack) })
    if (pillar) params.set('pillar', pillar)
    const res = await fetch(`/api/topics/live?${params.toString()}`)
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.error || errData.detail || 'Failed to fetch live web topics')
    }
    return res.json()
  },
}

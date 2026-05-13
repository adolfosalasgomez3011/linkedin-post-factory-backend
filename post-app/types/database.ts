export type Database = {
  public: {
    Tables: {
      posts: {
        Row: {
          id: string
          pillar: string
          format: string
          topic: string | null
          text: string
          hashtags: string | null
          created_at: string
          status: 'draft' | 'review' | 'approved' | 'scheduled' | 'published' | 'raw' | 'posted'
          voice_score: number | null
          length: number | null
        }
        Insert: {
          id?: string
          pillar: string
          format: string
          topic?: string | null
          text: string
          hashtags?: string | null
          created_at?: string
          status?: 'draft' | 'review' | 'approved' | 'scheduled' | 'published' | 'raw' | 'posted'
          voice_score?: number | null
          length?: number | null
        }
        Update: {
          id?: string
          pillar?: string
          format?: string
          topic?: string | null
          text?: string
          hashtags?: string | null
          created_at?: string
          status?: 'draft' | 'review' | 'approved' | 'scheduled' | 'published' | 'raw' | 'posted'
          voice_score?: number | null
          length?: number | null
        }
      }
      engagement: {
        Row: {
          id: number
          post_id: string
          views: number
          likes: number
          comments: number
          shares: number
          engagement_rate: number | null
          updated_at: string
        }
      }
    }
  }
}

export type Post = Database['public']['Tables']['posts']['Row']
export type PostInsert = Database['public']['Tables']['posts']['Insert']
export type PostUpdate = Database['public']['Tables']['posts']['Update']
export type PostStatus = Post['status']

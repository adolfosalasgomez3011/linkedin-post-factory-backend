'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api, type PostResponse } from '@/lib/api'
import { TrendingUp, FileText, CheckCircle, Calendar as CalendarIcon } from 'lucide-react'
import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

export function Analytics() {
  const [posts, setPosts] = useState<PostResponse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPosts = async () => {
      setLoading(true)
      try {
        const data = await api.listPosts(500)
        setPosts(data)
      } catch (error) {
        console.error('Error loading posts:', error)
      }
      setLoading(false)
    }
    
    void fetchPosts()
  }, [])

  // Calculate statistics
  const totalPosts = posts.length
  const postedCount = posts.filter(p => p.status === 'published' || p.status === 'posted').length
  const scheduledCount = posts.filter(p => p.status === 'scheduled').length

  // Average voice score
  const avgVoiceScore = posts
    .filter(p => p.voice_score !== null)
    .reduce((acc, p) => acc + (p.voice_score || 0), 0) / posts.filter(p => p.voice_score !== null).length || 0

  // Posts by pillar
  const postsByPillar = posts.reduce((acc, post) => {
    acc[post.pillar] = (acc[post.pillar] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const pillarData = Object.entries(postsByPillar).map(([name, count]) => ({
    name,
    count
  }))

  // Posts by format
  const postsByFormat = posts.reduce((acc, post) => {
    acc[post.format] = (acc[post.format] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const formatData = Object.entries(postsByFormat).map(([name, count]) => ({
    name,
    count
  }))

  // Posts by status
  const postsByStatus = posts.reduce((acc, post) => {
    acc[post.status] = (acc[post.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const postsByChannel = posts.reduce((acc, post) => {
    const channelKey = post.channel || 'personal_career'
    acc[channelKey] = (acc[channelKey] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const statusData = Object.entries(postsByStatus).map(([name, value]) => ({
    name,
    value
  }))

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8']

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-slate-400">
          Loading analytics...
        </CardContent>
      </Card>
    )
  }

  if (totalPosts === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-slate-400">
          No data yet. Generate some posts to see analytics!
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Posts</CardTitle>
            <FileText className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalPosts}</div>
            <p className="text-xs text-slate-500 mt-1">
              All generated posts
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Published</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{postedCount}</div>
            <p className="text-xs text-slate-500 mt-1">
              {totalPosts > 0 ? ((postedCount / totalPosts) * 100).toFixed(0) : 0}% of total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Scheduled</CardTitle>
            <CalendarIcon className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{scheduledCount}</div>
            <p className="text-xs text-slate-500 mt-1">
              Ready to post
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Avg Voice Score</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgVoiceScore.toFixed(1)}</div>
            <p className="text-xs text-slate-500 mt-1">
              Out of 100
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Posts by Pillar */}
        <Card>
          <CardHeader>
            <CardTitle>Posts by Content Pillar</CardTitle>
            <CardDescription>Distribution across content pillars</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <RechartsBarChart data={pillarData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Posts by Format */}
        <Card>
          <CardHeader>
            <CardTitle>Posts by Format</CardTitle>
            <CardDescription>Distribution across post formats</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <RechartsBarChart data={formatData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#10b981" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Posts by Status */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Posts by Status</CardTitle>
            <CardDescription>Current workflow status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4 justify-center">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Performing Pillars */}
      <Card>
        <CardHeader>
          <CardTitle>Content Pillar Summary</CardTitle>
          <CardDescription>Overview of your content strategy</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {pillarData.sort((a, b) => b.count - a.count).map((pillar) => (
              <Badge key={pillar.name} variant="outline" className="text-base py-2 px-4">
                {pillar.name}: {pillar.count} posts
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Channel Split</CardTitle>
          <CardDescription>Personal career vs GoalPraxis company output</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {Object.entries(postsByChannel).map(([channel, count]) => (
              <Badge key={channel} variant="outline" className="text-base py-2 px-4">
                {channel === 'goalpraxis_company' ? 'GoalPraxis Company' : 'Personal Career'}: {count} posts
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

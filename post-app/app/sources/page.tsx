'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

type ChannelValue = 'personal_career' | 'goalpraxis_company' | 'other'

type SourceItem = {
  id: number
  channel: ChannelValue
  name: string
  url: string
  created_at: string
}

const CHANNEL_OPTIONS: Array<{ value: ChannelValue; label: string }> = [
  { value: 'personal_career', label: 'Personal Career' },
  { value: 'goalpraxis_company', label: 'GoalPraxis Company' },
  { value: 'other', label: 'Other' },
]

export default function SourcesPage() {
  const [channel, setChannel] = useState<ChannelValue>('goalpraxis_company')
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [sources, setSources] = useState<SourceItem[]>([])
  const [message, setMessage] = useState<string | null>(null)

  const visibleSources = useMemo(
    () => sources.filter((source) => source.channel === channel),
    [sources, channel]
  )

  const fetchSources = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const response = await fetch('/api/sources')
      if (!response.ok) throw new Error('Failed to load sources')
      const data = await response.json() as { sources: SourceItem[] }
      setSources(data.sources || [])
    } catch (error) {
      console.error(error)
      setMessage('Could not load sources. Check Neon configuration and try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchSources()
  }, [])

  const handleAdd = async () => {
    if (!name.trim() || !url.trim()) {
      setMessage('Name and URL are required.')
      return
    }

    setLoading(true)
    setMessage(null)
    try {
      const response = await fetch('/api/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, name, url }),
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({ error: 'Failed to add source' }))
        throw new Error(err.error || 'Failed to add source')
      }

      setName('')
      setUrl('')
      await fetchSources()
      setMessage('Source saved.')
    } catch (error) {
      console.error(error)
      setMessage(error instanceof Error ? error.message : 'Failed to add source')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    setLoading(true)
    setMessage(null)
    try {
      const response = await fetch(`/api/sources?id=${id}`, { method: 'DELETE' })
      if (!response.ok) {
        const err = await response.json().catch(() => ({ error: 'Failed to delete source' }))
        throw new Error(err.error || 'Failed to delete source')
      }
      await fetchSources()
      setMessage('Source removed.')
    } catch (error) {
      console.error(error)
      setMessage(error instanceof Error ? error.message : 'Failed to delete source')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Manage Topic Sources</h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">Add or remove RSS/source pages used for topic search.</p>
          </div>
          <Button
            asChild
            className="border border-slate-300 bg-white font-semibold text-slate-900 shadow-sm hover:bg-slate-100"
          >
            <Link href="/">Back to Post Factory</Link>
          </Button>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Add Source</CardTitle>
            <CardDescription>Sources are stored in Neon and used by the live topic route.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="mb-1 block text-sm font-medium">Channel</label>
                <Select value={channel} onValueChange={(v) => setChannel(v as ChannelValue)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHANNEL_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Source Name</label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Mining Weekly" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Source URL</label>
                <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.miningweekly.com/rss" />
              </div>
            </div>
            <Button
              onClick={handleAdd}
              disabled={loading}
              className="bg-blue-600 font-semibold text-white shadow-md shadow-blue-500/30 hover:bg-blue-700"
            >
              Save Source
            </Button>
            {message && <p className="text-sm text-slate-600 dark:text-slate-300">{message}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sources for {CHANNEL_OPTIONS.find((x) => x.value === channel)?.label}</CardTitle>
            <CardDescription>{visibleSources.length} configured source(s)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-3 flex items-center gap-2">
              <span className="text-sm text-slate-600">Filter channel:</span>
              <Select value={channel} onValueChange={(v) => setChannel(v as ChannelValue)}>
                <SelectTrigger className="w-[260px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CHANNEL_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Badge variant="secondary">Neon-backed</Badge>
            </div>

            <div className="space-y-2">
              {visibleSources.map((source) => (
                <div key={source.id} className="flex items-center justify-between rounded-md border border-slate-200 bg-white p-3">
                  <div>
                    <p className="font-medium text-slate-900">{source.name}</p>
                    <a href={source.url} target="_blank" rel="noreferrer" className="text-sm text-blue-600 underline underline-offset-2">
                      {source.url}
                    </a>
                  </div>
                  <Button
                    variant="destructive"
                    className="font-semibold shadow-md shadow-rose-500/30"
                    onClick={() => handleDelete(source.id)}
                    disabled={loading}
                  >
                    Delete
                  </Button>
                </div>
              ))}
              {visibleSources.length === 0 && (
                <p className="text-sm text-slate-500">No sources yet for this channel.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api, type PostResponse, type PostStatus } from '@/lib/api'
import { Search, Eye, Edit, Trash2, CheckCircle, Clock, Send, FileText, Sparkles } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useRouter } from 'next/navigation'

export function PostLibrary() {
  const router = useRouter()
  const [posts, setPosts] = useState<PostResponse[]>([])
  const [filteredPosts, setFilteredPosts] = useState<PostResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [channelFilter, setChannelFilter] = useState<string>('all')
  const [selectedPost, setSelectedPost] = useState<PostResponse | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editedText, setEditedText] = useState('')

  const loadPosts = async () => {
    setLoading(true)
    try {
      const data = await api.listPosts(200)
      setPosts(data)
    } catch (error) {
      console.error('Error loading posts:', error)
    }
    setLoading(false)
  }

  const filterPosts = React.useCallback(() => {
    let filtered = posts

    if (statusFilter !== 'all') {
      filtered = filtered.filter(post => post.status === statusFilter)
    }

    if (channelFilter !== 'all') {
      filtered = filtered.filter(post => (post.channel || 'personal_career') === channelFilter)
    }

    if (searchQuery) {
      filtered = filtered.filter(post =>
        post.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        post.pillar.toLowerCase().includes(searchQuery.toLowerCase()) ||
        post.topic?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    setFilteredPosts(filtered)
  }, [posts, searchQuery, statusFilter, channelFilter])

  React.useEffect(() => {
    loadPosts()
  }, [])

  React.useEffect(() => {
    const handlePostsUpdated = () => {
      void loadPosts()
    }

    window.addEventListener('posts-updated', handlePostsUpdated)
    return () => window.removeEventListener('posts-updated', handlePostsUpdated)
  }, [])

  React.useEffect(() => {
    filterPosts()
  }, [filterPosts])

  const updatePostStatus = async (postId: string, newStatus: PostStatus) => {
    try {
      await api.updatePostStatus(postId, newStatus)
      loadPosts()
    } catch (error) {
      console.error('Error updating status:', error)
      alert('Failed to update status')
    }
  }

  const deletePost = async (postId: string) => {
    if (!confirm('Are you sure you want to delete this post?')) return

    try {
      await api.deletePost(postId)
      loadPosts()
    } catch (error) {
      console.error('Error deleting post:', error)
      alert('Failed to delete post')
    }
  }

  const handleEdit = (post: PostResponse) => {
    setSelectedPost(post)
    setEditedText(post.text)
    setEditDialogOpen(true)
  }

  const saveEdit = async () => {
    if (!selectedPost) return

    try {
      await api.updatePost(selectedPost.id, {
        text: editedText,
        hashtags: selectedPost.hashtags || [],
      })
      setEditDialogOpen(false)
      loadPosts()
    } catch (error) {
      console.error('Error updating post:', error)
      alert('Failed to update post')
    }
  }

  const getStatusIcon = (status: PostStatus) => {
    switch (status) {
      case 'draft': return <FileText className="h-4 w-4" />
      case 'raw': return <FileText className="h-4 w-4" />
      case 'review': return <Eye className="h-4 w-4" />
      case 'approved': return <CheckCircle className="h-4 w-4" />
      case 'scheduled': return <Clock className="h-4 w-4" />
      case 'published': return <Send className="h-4 w-4" />
      case 'posted': return <Send className="h-4 w-4" />
    }
  }

  const getStatusColor = (status: PostStatus) => {
    switch (status) {
      case 'draft': return 'bg-slate-100 text-slate-700'
      case 'raw': return 'bg-slate-100 text-slate-700'
      case 'review': return 'bg-blue-100 text-blue-700'
      case 'approved': return 'bg-green-100 text-green-700'
      case 'scheduled': return 'bg-purple-100 text-purple-700'
      case 'published': return 'bg-emerald-100 text-emerald-700'
      case 'posted': return 'bg-emerald-100 text-emerald-700'
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Post Library</CardTitle>
          <CardDescription>
            Manage your generated LinkedIn posts
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search posts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="review">Review</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="scheduled">Scheduled</SelectItem>
                <SelectItem value="published">Published</SelectItem>
              </SelectContent>
            </Select>
            <Select value={channelFilter} onValueChange={setChannelFilter}>
              <SelectTrigger className="w-[210px]">
                <SelectValue placeholder="Filter by channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                <SelectItem value="personal_career">Personal Career</SelectItem>
                <SelectItem value="goalpraxis_company">GoalPraxis Company</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Posts Table */}
          {loading ? (
            <div className="text-center py-12 text-slate-400">Loading posts...</div>
          ) : filteredPosts.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              No posts found. Generate some posts to get started!
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Content</TableHead>
                    <TableHead>Channel</TableHead>
                    <TableHead>Pillar</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPosts.map((post) => (
                    <TableRow key={post.id}>
                      <TableCell className="max-w-md">
                        <div className="truncate font-medium">{post.text.substring(0, 60)}...</div>
                        {post.topic && (
                          <div className="text-sm text-slate-500">{post.topic}</div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{(post.channel || 'personal_career') === 'goalpraxis_company' ? 'GoalPraxis' : 'Personal'}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{post.pillar}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(post.status)}>
                          <span className="flex items-center gap-1">
                            {getStatusIcon(post.status)}
                            {post.status}
                          </span>
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-slate-500">
                        {(() => {
                          try {
                            const date = new Date(post.created_at);
                            if (isNaN(date.getTime())) return 'Unknown';
                            return formatDistanceToNow(date, { addSuffix: true });
                          } catch {
                            return 'Unknown';
                          }
                        })()}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-2 justify-end">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => router.push(`/demos/${post.id}`)}
                            title="View Interactive Demo"
                          >
                            <Sparkles className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleEdit(post)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Select
                            value={post.status}
                            onValueChange={(value) => updatePostStatus(post.id, value as PostStatus)}
                          >
                            <SelectTrigger className="w-[100px] h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="draft">Draft</SelectItem>
                              <SelectItem value="review">Review</SelectItem>
                              <SelectItem value="approved">Approved</SelectItem>
                              <SelectItem value="scheduled">Scheduled</SelectItem>
                              <SelectItem value="published">Published</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => deletePost(post.id)}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Post</DialogTitle>
            <DialogDescription>
              Make changes to your post content
            </DialogDescription>
          </DialogHeader>
          {selectedPost && (
            <div className="flex flex-col gap-4">
              <div className="flex gap-2">
                <Badge variant="outline">{selectedPost.pillar}</Badge>
                <Badge variant="outline">{selectedPost.format}</Badge>
              </div>
              <div className="max-h-[50vh] overflow-y-auto rounded-md border">
                <Textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  className="min-h-[300px] resize-none border-0 focus-visible:ring-0"
                />
              </div>
              <div className="flex gap-2 justify-end pt-2 border-t">
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={saveEdit}>
                  Save Changes
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}

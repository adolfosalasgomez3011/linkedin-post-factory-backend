import { NextRequest, NextResponse } from 'next/server'
import { addManagedSource, deleteManagedSource, listManagedSources } from '@/lib/neon'

function isValidHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

export async function GET(request: NextRequest) {
  try {
    const channel = request.nextUrl.searchParams.get('channel') || undefined
    const sources = await listManagedSources(channel)
    return NextResponse.json({ sources })
  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to load sources' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json() as { channel?: string; name?: string; url?: string }
    const channel = (body.channel || '').trim()
    const name = (body.name || '').trim()
    const url = (body.url || '').trim()

    if (!channel || !name || !url) {
      return NextResponse.json({ error: 'channel, name, and url are required' }, { status: 400 })
    }

    if (!isValidHttpUrl(url)) {
      return NextResponse.json({ error: 'url must be a valid http(s) URL' }, { status: 400 })
    }

    const created = await addManagedSource({ channel, name, url })
    return NextResponse.json({ source: created }, { status: 201 })
  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to add source' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const idParam = request.nextUrl.searchParams.get('id')
    const id = Number(idParam)
    if (!idParam || Number.isNaN(id) || id <= 0) {
      return NextResponse.json({ error: 'Valid source id is required' }, { status: 400 })
    }

    const deleted = await deleteManagedSource(id)
    if (!deleted) {
      return NextResponse.json({ error: 'Source not found' }, { status: 404 })
    }

    return NextResponse.json({ ok: true })
  } catch (error: unknown) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to delete source' },
      { status: 500 }
    )
  }
}

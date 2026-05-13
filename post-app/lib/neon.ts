import { neon } from '@neondatabase/serverless'

export type SourceChannel = 'personal_career' | 'goalpraxis_company' | 'other'

export type ManagedSource = {
  id: number
  channel: SourceChannel
  name: string
  url: string
  created_at: string
}

const VALID_CHANNELS: SourceChannel[] = ['personal_career', 'goalpraxis_company', 'other']

function getSqlClient() {
  const connectionString = process.env.NEON_DATABASE_URL || process.env.DATABASE_URL
  if (!connectionString) {
    throw new Error('NEON_DATABASE_URL (or DATABASE_URL) is not configured')
  }
  return neon(connectionString)
}

export function normalizeChannel(value: string): SourceChannel {
  return VALID_CHANNELS.includes(value as SourceChannel) ? (value as SourceChannel) : 'other'
}

export async function ensureSourcesTable() {
  const sql = getSqlClient()
  await sql`
    CREATE TABLE IF NOT EXISTS channel_sources (
      id BIGSERIAL PRIMARY KEY,
      channel TEXT NOT NULL,
      name TEXT NOT NULL,
      url TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(channel, name, url)
    )
  `
}

export async function listManagedSources(channel?: string): Promise<ManagedSource[]> {
  const sql = getSqlClient()
  await ensureSourcesTable()

  if (channel) {
    const normalized = normalizeChannel(channel)
    const rows = await sql`
      SELECT id, channel, name, url, created_at
      FROM channel_sources
      WHERE channel = ${normalized}
      ORDER BY created_at DESC, id DESC
    `
    return rows as ManagedSource[]
  }

  const rows = await sql`
    SELECT id, channel, name, url, created_at
    FROM channel_sources
    ORDER BY channel ASC, created_at DESC, id DESC
  `
  return rows as ManagedSource[]
}

export async function addManagedSource(input: { channel: string; name: string; url: string }): Promise<ManagedSource> {
  const sql = getSqlClient()
  await ensureSourcesTable()

  const channel = normalizeChannel(input.channel)
  const name = input.name.trim()
  const url = input.url.trim()

  const rows = await sql`
    INSERT INTO channel_sources (channel, name, url)
    VALUES (${channel}, ${name}, ${url})
    ON CONFLICT (channel, name, url) DO UPDATE
      SET name = EXCLUDED.name
    RETURNING id, channel, name, url, created_at
  `

  return rows[0] as ManagedSource
}

export async function deleteManagedSource(id: number): Promise<boolean> {
  const sql = getSqlClient()
  await ensureSourcesTable()
  const rows = await sql`DELETE FROM channel_sources WHERE id = ${id} RETURNING id`
  return rows.length > 0
}

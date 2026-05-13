import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { text } = await request.json() as { text: string }

    if (!text || typeof text !== 'string') {
      return NextResponse.json({ error: 'text is required' }, { status: 400 })
    }

    const apiKey = process.env.GOOGLE_API_KEY
    if (!apiKey) {
      return NextResponse.json({ error: 'API key not configured' }, { status: 500 })
    }

    const prompt = `Translate the following LinkedIn post from English to Spanish (Latin American Spanish).
Maintain the same professional tone, paragraph structure, line breaks, and emojis.
Keep hashtags in English — do not translate them.
Return ONLY the translated text, with no extra explanation or commentary.

Post to translate:
${text}`

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.3, maxOutputTokens: 2048 },
        }),
      }
    )

    if (!response.ok) {
      const err = await response.text()
      console.error('Gemini translate error:', err)
      return NextResponse.json({ error: 'Translation failed' }, { status: 502 })
    }

    const data = await response.json() as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> }
    const translated = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? ''

    return NextResponse.json({ translated })
  } catch (error) {
    console.error('Translation error:', error)
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}

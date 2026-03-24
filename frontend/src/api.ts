export type Voice = {
  voice_id: string
  name: string
  builtin?: boolean
}

export type CloneResponse = {
  voice_id: string
  name: string
}

export async function listVoices(signal?: AbortSignal): Promise<Voice[]> {
  const res = await fetch('/api/voices', { signal })
  if (!res.ok) {
    throw new Error(`Failed to list voices (${res.status})`)
  }
  return (await res.json()) as Voice[]
}

export async function cloneVoice(params: {
  file: File
  name?: string
  signal?: AbortSignal
}): Promise<CloneResponse> {
  const fd = new FormData()
  fd.append('file', params.file)
  if (params.name && params.name.trim() !== '') {
    fd.append('name', params.name.trim())
  }

  const res = await fetch('/api/clone', {
    method: 'POST',
    body: fd,
    signal: params.signal,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const json = (await res.json()) as { detail?: string }
      detail = json.detail ? `: ${json.detail}` : ''
    } catch {
      detail = ''
    }
    throw new Error(`Clone failed (${res.status})${detail}`)
  }
  return (await res.json()) as CloneResponse
}

export async function generateAudioStream(params: {
  text: string
  voice_id: string
  speed: number
  temperature: number
  language?: string
  signal?: AbortSignal
}): Promise<Response> {
  const res = await fetch('/api/generate_stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: params.text,
      voice_id: params.voice_id,
      speed: params.speed,
      temperature: params.temperature,
      language: params.language,
    }),
    signal: params.signal,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const json = (await res.json()) as { detail?: string }
      detail = json.detail ? `: ${json.detail}` : ''
    } catch {
      detail = ''
    }
    throw new Error(`Generate failed (${res.status})${detail}`)
  }
  return res
}

import { useEffect, useMemo, useState } from 'react'
import { cloneVoice, listVoices, type Voice } from '../api'

type Props = {
  selectedVoiceId: string
  onSelectVoiceId: (voiceId: string) => void
}

export function VoicesPanel(props: Props) {
  const [voices, setVoices] = useState<Voice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [cloning, setCloning] = useState(false)

  const sortedVoices = useMemo(() => {
    const copy = [...voices]
    copy.sort((a, b) => {
      if (!!a.builtin !== !!b.builtin) return a.builtin ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    return copy
  }, [voices])

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const next = await listVoices()
      setVoices(next)
      if (props.selectedVoiceId === '' && next.length > 0) {
        props.onSelectVoiceId(next[0].voice_id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load voices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function onClone() {
    setSuccess(null)
    setError(null)
    if (!file) {
      setError('Pick a reference audio file first.')
      return
    }

    setCloning(true)
    try {
      const res = await cloneVoice({ file, name })
      setSuccess(`Voice created: ${res.name}`)
      setName('')
      setFile(null)
      await refresh()
      props.onSelectVoiceId(res.voice_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Clone failed')
    } finally {
      setCloning(false)
    }
  }

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>Voice Cloning & Library</h2>
        <button className="button" onClick={() => void refresh()} disabled={loading || cloning}>
          Refresh
        </button>
      </div>

      <div className="muted">
        Upload 5–10s of clean speech to create a reusable voice embedding. Built-in voices show first.
      </div>

      <div className="field">
        <label>Voice name (optional)</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., Dad Narration" />
      </div>

      <div className="field">
        <label>Reference audio (.wav/.mp3)</label>
        <input
          type="file"
          accept="audio/wav,audio/x-wav,audio/mpeg,audio/mp3"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="row wrap" style={{ marginTop: 12 }}>
        <button className="button" onClick={() => void onClone()} disabled={cloning}>
          {cloning ? 'Cloning…' : 'Clone Voice'}
        </button>
        <span className="muted">
          Tip: keep background noise low. Output quality mirrors the sample.
        </span>
      </div>

      {error ? <div className="error">{error}</div> : null}
      {success ? <div className="success">{success}</div> : null}

      <div className="list" role="list" aria-label="Voices">
        {sortedVoices.length === 0 ? (
          <div className="muted">No voices yet.</div>
        ) : (
          sortedVoices.map((v) => {
            const selected = v.voice_id === props.selectedVoiceId
            return (
              <button
                key={v.voice_id}
                className="listItem"
                style={{
                  cursor: 'pointer',
                  outline: selected ? '2px solid rgba(34, 197, 94, 0.38)' : 'none',
                }}
                onClick={() => props.onSelectVoiceId(v.voice_id)}
                type="button"
              >
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 2 }}>
                  <strong>{v.name}</strong>
                  <small>{v.voice_id}</small>
                </div>
                <div className="row" style={{ gap: 8 }}>
                  {v.builtin ? <span className="pill">Built-in</span> : null}
                  {selected ? <span className="pill">Selected</span> : null}
                </div>
              </button>
            )
          })
        )}
      </div>
    </section>
  )
}


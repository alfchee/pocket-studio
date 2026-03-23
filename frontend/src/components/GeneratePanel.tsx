import { useEffect, useMemo, useState } from 'react'
import { generateAudio, listVoices, type Voice } from '../api'

type Props = {
  selectedVoiceId: string
  onSelectVoiceId: (voiceId: string) => void
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n))
}

export function GeneratePanel(props: Props) {
  const [voices, setVoices] = useState<Voice[]>([])
  const [loadingVoices, setLoadingVoices] = useState(false)

  const [text, setText] = useState('Hello! This is a Pocket Studio test.')
  const [speed, setSpeed] = useState(1.0)
  const [temperature, setTemperature] = useState(0.7)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)

  const canGenerate = props.selectedVoiceId !== '' && text.trim() !== '' && !busy

  const voiceOptions = useMemo(() => {
    const copy = [...voices]
    copy.sort((a, b) => {
      if (!!a.builtin !== !!b.builtin) return a.builtin ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    return copy
  }, [voices])

  async function refreshVoices() {
    setLoadingVoices(true)
    try {
      const next = await listVoices()
      setVoices(next)
      if (props.selectedVoiceId === '' && next.length > 0) {
        props.onSelectVoiceId(next[0].voice_id)
      }
    } finally {
      setLoadingVoices(false)
    }
  }

  useEffect(() => {
    void refreshVoices()
  }, [])

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  async function onGenerate() {
    setError(null)
    if (!canGenerate) return
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
      setAudioBlob(null)
    }

    const safeSpeed = clamp(speed, 0.5, 2.0)
    const safeTemp = clamp(temperature, 0.0, 1.5)

    setBusy(true)
    try {
      const blob = await generateAudio({
        text,
        voice_id: props.selectedVoiceId,
        speed: safeSpeed,
        temperature: safeTemp,
      })
      const url = URL.createObjectURL(blob)
      setAudioBlob(blob)
      setAudioUrl(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generate failed')
    } finally {
      setBusy(false)
    }
  }

  function download() {
    if (!audioBlob) return
    const a = document.createElement('a')
    const url = URL.createObjectURL(audioBlob)
    a.href = url
    a.download = 'pocket_studio.wav'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>TTS Generation</h2>
        <button className="button" onClick={() => void refreshVoices()} disabled={loadingVoices || busy}>
          Sync Voices
        </button>
      </div>

      <div className="muted">
        Paste text, select a voice, tweak speed and temperature, then generate a 24kHz WAV.
      </div>

      <div className="field">
        <label>Voice</label>
        <select value={props.selectedVoiceId} onChange={(e) => props.onSelectVoiceId(e.target.value)}>
          <option value="" disabled>
            Select a voice…
          </option>
          {voiceOptions.map((v) => (
            <option key={v.voice_id} value={v.voice_id}>
              {v.builtin ? `${v.name} (built-in)` : v.name}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label>Text</label>
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste your script here…" />
        <div className="muted">
          Characters: <span className="kbd">{text.length}</span>
        </div>
      </div>

      <div className="field">
        <label>Speed</label>
        <div className="sliderRow">
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.05}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
          />
          <span className="kbd">{speed.toFixed(2)}</span>
        </div>
      </div>

      <div className="field">
        <label>Temperature</label>
        <div className="sliderRow">
          <input
            type="range"
            min={0.0}
            max={1.5}
            step={0.05}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
          />
          <span className="kbd">{temperature.toFixed(2)}</span>
        </div>
      </div>

      <div className="row wrap" style={{ marginTop: 12 }}>
        <button className="button" onClick={() => void onGenerate()} disabled={!canGenerate}>
          {busy ? 'Generating…' : 'Generate WAV'}
        </button>
        <span className="muted">Tip: for longer scripts, generate in sections for easier editing.</span>
      </div>

      {error ? <div className="error">{error}</div> : null}

      {audioUrl ? (
        <div className="audio">
          <audio controls src={audioUrl} style={{ width: '100%' }} />
          <div className="audioActions">
            <button className="button" onClick={download}>
              Download WAV
            </button>
            <span className="muted">If playback fails, try downloading the file.</span>
          </div>
        </div>
      ) : null}
    </section>
  )
}


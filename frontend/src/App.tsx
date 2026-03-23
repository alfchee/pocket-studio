import { useEffect, useState } from 'react'
import { GeneratePanel } from './components/GeneratePanel'
import { VoicesPanel } from './components/VoicesPanel'

export function App() {
  const [selectedVoiceId, setSelectedVoiceId] = useState('')
  const [apiStatus, setApiStatus] = useState<'unknown' | 'ok' | 'down'>('unknown')

  useEffect(() => {
    let cancelled = false
    async function check() {
      try {
        const res = await fetch('/api/health')
        if (!cancelled) setApiStatus(res.ok ? 'ok' : 'down')
      } catch {
        if (!cancelled) setApiStatus('down')
      }
    }
    void check()
    const id = window.setInterval(check, 7000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  return (
    <div className="container">
      <header className="header">
        <div className="title">
          <h1>Pocket Studio</h1>
          <p>
            Local TTS voice studio · API{' '}
            <span className="kbd">/api</span>
          </p>
        </div>
        <div className="row">
          <span className="pill" style={{
            background:
              apiStatus === 'ok'
                ? 'rgba(34, 197, 94, 0.12)'
                : apiStatus === 'down'
                  ? 'rgba(239, 68, 68, 0.14)'
                  : 'rgba(250, 250, 250, 0.08)',
            borderColor:
              apiStatus === 'ok'
                ? 'rgba(34, 197, 94, 0.22)'
                : apiStatus === 'down'
                  ? 'rgba(239, 68, 68, 0.22)'
                  : 'rgba(255, 255, 255, 0.10)',
          }}>
            {apiStatus === 'ok' ? 'API Online' : apiStatus === 'down' ? 'API Offline' : 'Checking…'}
          </span>
        </div>
      </header>

      <main className="grid">
        <VoicesPanel selectedVoiceId={selectedVoiceId} onSelectVoiceId={setSelectedVoiceId} />
        <GeneratePanel selectedVoiceId={selectedVoiceId} onSelectVoiceId={setSelectedVoiceId} />
      </main>
    </div>
  )
}

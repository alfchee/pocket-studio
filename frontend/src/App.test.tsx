import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'

type MockResponse = {
  ok: boolean
  status: number
  json?: () => Promise<unknown>
  blob?: () => Promise<Blob>
  headers?: Headers
}

function mockJson(ok: boolean, status: number, payload: unknown): MockResponse {
  return {
    ok,
    status,
    json: async () => payload,
    headers: new Headers({ 'content-type': 'application/json' }),
  }
}

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith('/api/health')) return mockJson(true, 200, { status: 'ok' })
        if (url.endsWith('/api/voices')) {
          return mockJson(true, 200, [
            { voice_id: 'alba', name: 'alba', builtin: true },
            { voice_id: 'local-1', name: 'Local Voice' },
          ])
        }
        return mockJson(false, 404, { detail: 'not found' })
      }),
    )
  })

  it('renders shell and loads voices', async () => {
    render(<App />)
    expect(screen.getByText('Pocket Studio')).toBeInTheDocument()
    expect(await screen.findByText('API Online')).toBeInTheDocument()

    const voicesList = await screen.findByRole('list', { name: 'Voices' })
    expect(within(voicesList).getByText('Local Voice')).toBeInTheDocument()
    expect(within(voicesList).getAllByText('alba').length).toBeGreaterThan(0)
  })
})

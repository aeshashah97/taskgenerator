import { useState } from 'react'
import { Button } from './ui/button'
import { fetchGoogleDoc } from '../api/client'

const MAX_CHARS = 50_000

interface Props {
  onSowReady: (text: string) => void
  disabled: boolean
}

export function InputPanel({ onSowReady, disabled }: Props) {
  const [mode, setMode] = useState<'paste' | 'url'>('paste')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [urlError, setUrlError] = useState<string | null>(null)
  const [fetchingUrl, setFetchingUrl] = useState(false)

  const charCount = text.length
  const overLimit = charCount > MAX_CHARS

  async function handleFetchUrl() {
    setUrlError(null)
    setFetchingUrl(true)
    try {
      const fetched = await fetchGoogleDoc(url)
      setText(fetched)
      setMode('paste')
      onSowReady(fetched)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Failed to fetch document'
      setUrlError(message)
    } finally {
      setFetchingUrl(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        {(['paste', 'url'] as const).map((m) => (
          <button
            key={m}
            className={`text-sm px-3 py-1 rounded ${mode === m ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-700'}`}
            onClick={() => setMode(m)}
            disabled={disabled}
          >
            {m === 'paste' ? 'Paste Text' : 'Google Doc URL'}
          </button>
        ))}
      </div>

      {mode === 'paste' && (
        <div className="flex flex-col gap-1">
          <textarea
            className={`w-full h-48 p-2 border rounded text-sm font-mono resize-y ${overLimit ? 'border-red-500' : 'border-slate-300'}`}
            placeholder="Paste your SOW / WBS content here…"
            value={text}
            onChange={(e) => { setText(e.target.value); onSowReady(e.target.value) }}
            disabled={disabled}
          />
          <span className={`text-xs ${overLimit ? 'text-red-500 font-semibold' : 'text-slate-400'}`}>
            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
            {overLimit && ' — over limit, please shorten'}
          </span>
        </div>
      )}

      {mode === 'url' && (
        <div className="flex flex-col gap-1">
          <div className="flex gap-2">
            <input
              className="flex-1 border border-slate-300 rounded px-2 py-1.5 text-sm"
              placeholder="https://docs.google.com/document/d/…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={fetchingUrl || disabled}
            />
            <Button size="sm" onClick={handleFetchUrl} disabled={!url.trim() || fetchingUrl || disabled}>
              {fetchingUrl ? 'Fetching…' : 'Fetch'}
            </Button>
          </div>
          {urlError && <p className="text-xs text-red-500">{urlError}</p>}
        </div>
      )}
    </div>
  )
}

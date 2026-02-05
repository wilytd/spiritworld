'use client'

import { useState } from 'react'
import { addMinutes, addHours, addDays, format } from 'date-fns'

interface SnoozeDialogProps {
  taskTitle: string
  onSnooze: (durationMinutes?: number, until?: string) => Promise<void>
  onCancel: () => void
}

const presetDurations = [
  { label: '15 minutes', minutes: 15 },
  { label: '1 hour', minutes: 60 },
  { label: '4 hours', minutes: 240 },
  { label: '1 day', minutes: 1440 },
  { label: '3 days', minutes: 4320 },
  { label: '1 week', minutes: 10080 },
]

export default function SnoozeDialog({ taskTitle, onSnooze, onCancel }: SnoozeDialogProps) {
  const [mode, setMode] = useState<'preset' | 'custom'>('preset')
  const [customDate, setCustomDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handlePresetSnooze = async (minutes: number) => {
    setIsSubmitting(true)
    try {
      await onSnooze(minutes, undefined)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCustomSnooze = async () => {
    if (!customDate) return
    setIsSubmitting(true)
    try {
      await onSnooze(undefined, customDate)
    } finally {
      setIsSubmitting(false)
    }
  }

  const buttonStyle = {
    padding: '0.5rem 1rem',
    backgroundColor: '#334155',
    border: 'none',
    borderRadius: '0.375rem',
    color: '#f8fafc',
    cursor: 'pointer',
    fontSize: '0.875rem',
    transition: 'background-color 0.15s',
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 50,
    }}>
      <div style={{
        backgroundColor: '#1e293b',
        borderRadius: '0.5rem',
        padding: '1.5rem',
        width: '100%',
        maxWidth: '400px',
      }}>
        <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.25rem' }}>Snooze Task</h2>
        <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1rem' }}>
          {taskTitle}
        </p>

        {/* Mode selector */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <button
            onClick={() => setMode('preset')}
            style={{
              ...buttonStyle,
              backgroundColor: mode === 'preset' ? '#2563eb' : '#334155',
            }}
          >
            Preset
          </button>
          <button
            onClick={() => setMode('custom')}
            style={{
              ...buttonStyle,
              backgroundColor: mode === 'custom' ? '#2563eb' : '#334155',
            }}
          >
            Custom
          </button>
        </div>

        {mode === 'preset' ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            {presetDurations.map(({ label, minutes }) => {
              const wakeTime = addMinutes(new Date(), minutes)
              return (
                <button
                  key={minutes}
                  onClick={() => handlePresetSnooze(minutes)}
                  disabled={isSubmitting}
                  style={{
                    ...buttonStyle,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    padding: '0.75rem',
                    opacity: isSubmitting ? 0.5 : 1,
                  }}
                >
                  <span>{label}</span>
                  <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                    {format(wakeTime, 'MMM d, h:mm a')}
                  </span>
                </button>
              )
            })}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                Snooze until
              </label>
              <input
                type="datetime-local"
                value={customDate}
                onChange={(e) => setCustomDate(e.target.value)}
                min={format(new Date(), "yyyy-MM-dd'T'HH:mm")}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '0.375rem',
                  color: '#f8fafc',
                  fontSize: '0.875rem',
                }}
              />
            </div>
            <button
              onClick={handleCustomSnooze}
              disabled={!customDate || isSubmitting}
              style={{
                ...buttonStyle,
                backgroundColor: !customDate || isSubmitting ? '#1e40af' : '#2563eb',
                cursor: !customDate || isSubmitting ? 'not-allowed' : 'pointer',
              }}
            >
              {isSubmitting ? 'Snoozing...' : 'Snooze'}
            </button>
          </div>
        )}

        <button
          onClick={onCancel}
          style={{
            ...buttonStyle,
            width: '100%',
            marginTop: '1rem',
            backgroundColor: 'transparent',
            border: '1px solid #334155',
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

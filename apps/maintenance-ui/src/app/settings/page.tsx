'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'

interface NotificationPreference {
  id: number
  channel: 'mesh' | 'email' | 'webhook'
  enabled: boolean
  config: Record<string, any> | null
  min_priority: string
  categories: string[] | null
  quiet_hours_start: string | null
  quiet_hours_end: string | null
}

interface PreferenceFormData {
  channel: 'mesh' | 'email' | 'webhook'
  enabled: boolean
  email?: string
  webhook_url?: string
  webhook_format?: string
  min_priority: string
  categories: string
  quiet_hours_start: string
  quiet_hours_end: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const priorities = ['low', 'medium', 'high', 'critical']
const categories = ['network', 'security', 'backup', 'monitoring', 'hardware', 'software', 'other']

export default function SettingsPage() {
  const [preferences, setPreferences] = useState<NotificationPreference[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingPref, setEditingPref] = useState<NotificationPreference | null>(null)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [testResult, setTestResult] = useState<{ id: number; success: boolean; message: string } | null>(null)

  useEffect(() => {
    fetchPreferences()
  }, [])

  async function fetchPreferences() {
    try {
      const response = await fetch(`${API_URL}/api/notifications/preferences`)
      if (response.ok) {
        setPreferences(await response.json())
      }
    } catch (error) {
      console.error('Failed to fetch preferences:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreatePreference(data: PreferenceFormData) {
    const body = buildRequestBody(data)
    const response = await fetch(`${API_URL}/api/notifications/preferences`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (response.ok) {
      setShowForm(false)
      fetchPreferences()
    }
  }

  async function handleUpdatePreference(data: PreferenceFormData) {
    if (!editingPref) return
    const body = buildRequestBody(data)
    const response = await fetch(`${API_URL}/api/notifications/preferences/${editingPref.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (response.ok) {
      setEditingPref(null)
      fetchPreferences()
    }
  }

  async function handleDeletePreference(id: number) {
    if (!confirm('Delete this notification preference?')) return
    const response = await fetch(`${API_URL}/api/notifications/preferences/${id}`, {
      method: 'DELETE',
    })
    if (response.ok) {
      fetchPreferences()
    }
  }

  async function handleTestPreference(id: number) {
    setTestingId(id)
    setTestResult(null)
    try {
      const response = await fetch(`${API_URL}/api/notifications/test/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Test notification from Aegis Mesh Settings' }),
      })
      const result = await response.json()
      setTestResult({
        id,
        success: result.success,
        message: result.success ? 'Test sent successfully!' : result.error || 'Failed to send test',
      })
    } catch (error) {
      setTestResult({ id, success: false, message: 'Network error' })
    } finally {
      setTestingId(null)
    }
  }

  function buildRequestBody(data: PreferenceFormData) {
    const config: Record<string, any> = {}
    if (data.channel === 'email' && data.email) {
      config.email = data.email
    } else if (data.channel === 'webhook') {
      if (data.webhook_url) config.webhook_url = data.webhook_url
      if (data.webhook_format) config.format = data.webhook_format
    }

    return {
      channel: data.channel,
      enabled: data.enabled,
      config: Object.keys(config).length > 0 ? config : null,
      min_priority: data.min_priority,
      categories: data.categories ? data.categories.split(',').map(c => c.trim()).filter(Boolean) : null,
      quiet_hours_start: data.quiet_hours_start || null,
      quiet_hours_end: data.quiet_hours_end || null,
    }
  }

  function getChannelLabel(channel: string) {
    switch (channel) {
      case 'mesh': return 'Mesh Network'
      case 'email': return 'Email'
      case 'webhook': return 'Webhook'
      default: return channel
    }
  }

  const cardStyle = {
    backgroundColor: '#1e293b',
    borderRadius: '0.5rem',
    padding: '1rem',
    marginBottom: '0.75rem',
  }

  const buttonStyle = {
    padding: '0.25rem 0.5rem',
    fontSize: '0.75rem',
    border: 'none',
    borderRadius: '0.25rem',
    cursor: 'pointer',
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Notification Settings</h1>
          <p style={{ color: '#94a3b8', marginTop: '0.25rem', fontSize: '0.875rem' }}>
            Configure how and when you receive task notifications
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <a
            href="/"
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#334155',
              color: 'white',
              borderRadius: '0.375rem',
              textDecoration: 'none',
            }}
          >
            Back
          </a>
          <button
            onClick={() => setShowForm(true)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
            }}
          >
            + Add Channel
          </button>
        </div>
      </header>

      {loading ? (
        <p>Loading preferences...</p>
      ) : preferences.length === 0 ? (
        <div style={cardStyle}>
          <p style={{ color: '#64748b', margin: 0 }}>
            No notification channels configured. Add one to start receiving alerts.
          </p>
        </div>
      ) : (
        preferences.map(pref => (
          <div key={pref.id} style={{ ...cardStyle, opacity: pref.enabled ? 1 : 0.6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1rem' }}>
                  {getChannelLabel(pref.channel)}
                  {!pref.enabled && <span style={{ color: '#64748b', marginLeft: '0.5rem' }}>(Disabled)</span>}
                </h3>
                <div style={{ color: '#94a3b8', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                  {pref.channel === 'email' && pref.config?.email && (
                    <p style={{ margin: 0 }}>Email: {pref.config.email}</p>
                  )}
                  {pref.channel === 'webhook' && pref.config?.webhook_url && (
                    <p style={{ margin: 0 }}>URL: {pref.config.webhook_url}</p>
                  )}
                  <p style={{ margin: '0.25rem 0 0' }}>
                    Min priority: {pref.min_priority}
                    {pref.categories && ` | Categories: ${pref.categories.join(', ')}`}
                  </p>
                  {pref.quiet_hours_start && pref.quiet_hours_end && (
                    <p style={{ margin: '0.25rem 0 0' }}>
                      Quiet hours: {pref.quiet_hours_start} - {pref.quiet_hours_end}
                    </p>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => handleTestPreference(pref.id)}
                  disabled={testingId === pref.id}
                  style={{ ...buttonStyle, backgroundColor: '#22c55e', color: 'white' }}
                >
                  {testingId === pref.id ? 'Testing...' : 'Test'}
                </button>
                <button
                  onClick={() => setEditingPref(pref)}
                  style={{ ...buttonStyle, backgroundColor: '#3b82f6', color: 'white' }}
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDeletePreference(pref.id)}
                  style={{ ...buttonStyle, backgroundColor: '#ef4444', color: 'white' }}
                >
                  Delete
                </button>
              </div>
            </div>
            {testResult && testResult.id === pref.id && (
              <div style={{
                marginTop: '0.5rem',
                padding: '0.5rem',
                backgroundColor: testResult.success ? '#166534' : '#991b1b',
                borderRadius: '0.25rem',
                fontSize: '0.875rem',
              }}>
                {testResult.message}
              </div>
            )}
          </div>
        ))
      )}

      {/* Form Modal */}
      {(showForm || editingPref) && (
        <PreferenceForm
          preference={editingPref}
          onSubmit={editingPref ? handleUpdatePreference : handleCreatePreference}
          onCancel={() => {
            setShowForm(false)
            setEditingPref(null)
          }}
        />
      )}
    </main>
  )
}

function PreferenceForm({
  preference,
  onSubmit,
  onCancel,
}: {
  preference: NotificationPreference | null
  onSubmit: (data: PreferenceFormData) => Promise<void>
  onCancel: () => void
}) {
  const { register, handleSubmit, watch, formState: { isSubmitting } } = useForm<PreferenceFormData>({
    defaultValues: preference ? {
      channel: preference.channel,
      enabled: preference.enabled,
      email: preference.config?.email || '',
      webhook_url: preference.config?.webhook_url || '',
      webhook_format: preference.config?.format || 'generic',
      min_priority: preference.min_priority,
      categories: preference.categories?.join(', ') || '',
      quiet_hours_start: preference.quiet_hours_start || '',
      quiet_hours_end: preference.quiet_hours_end || '',
    } : {
      channel: 'mesh',
      enabled: true,
      min_priority: 'low',
      webhook_format: 'generic',
    },
  })

  const selectedChannel = watch('channel')

  const inputStyle = {
    width: '100%',
    padding: '0.5rem',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '0.375rem',
    color: '#f8fafc',
    fontSize: '0.875rem',
  }

  const labelStyle = {
    display: 'block',
    marginBottom: '0.25rem',
    color: '#94a3b8',
    fontSize: '0.875rem',
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
        maxWidth: '450px',
        maxHeight: '90vh',
        overflow: 'auto',
      }}>
        <h2 style={{ margin: '0 0 1rem', fontSize: '1.25rem' }}>
          {preference ? 'Edit Channel' : 'Add Notification Channel'}
        </h2>

        <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={labelStyle}>Channel</label>
            <select {...register('channel')} style={inputStyle}>
              <option value="mesh">Mesh Network</option>
              <option value="email">Email</option>
              <option value="webhook">Webhook (Slack/Discord)</option>
            </select>
          </div>

          {selectedChannel === 'email' && (
            <div>
              <label style={labelStyle}>Email Address</label>
              <input {...register('email')} type="email" style={inputStyle} placeholder="alerts@example.com" />
            </div>
          )}

          {selectedChannel === 'webhook' && (
            <>
              <div>
                <label style={labelStyle}>Webhook URL</label>
                <input {...register('webhook_url')} style={inputStyle} placeholder="https://hooks.slack.com/..." />
              </div>
              <div>
                <label style={labelStyle}>Format</label>
                <select {...register('webhook_format')} style={inputStyle}>
                  <option value="generic">Generic</option>
                  <option value="slack">Slack</option>
                  <option value="discord">Discord</option>
                </select>
              </div>
            </>
          )}

          <div>
            <label style={labelStyle}>Minimum Priority</label>
            <select {...register('min_priority')} style={inputStyle}>
              {priorities.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <p style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              Only notify for tasks at this priority level or higher
            </p>
          </div>

          <div>
            <label style={labelStyle}>Categories (optional)</label>
            <input {...register('categories')} style={inputStyle} placeholder="network, security, backup" />
            <p style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              Comma-separated. Leave empty for all categories.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={labelStyle}>Quiet Hours Start</label>
              <input type="time" {...register('quiet_hours_start')} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Quiet Hours End</label>
              <input type="time" {...register('quiet_hours_end')} style={inputStyle} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input type="checkbox" {...register('enabled')} id="enabled" style={{ width: '1rem', height: '1rem' }} />
            <label htmlFor="enabled" style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
              Enabled
            </label>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button
              type="button"
              onClick={onCancel}
              style={{
                flex: 1,
                padding: '0.5rem',
                backgroundColor: '#334155',
                border: 'none',
                borderRadius: '0.375rem',
                color: '#f8fafc',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                flex: 1,
                padding: '0.5rem',
                backgroundColor: isSubmitting ? '#1e40af' : '#2563eb',
                border: 'none',
                borderRadius: '0.375rem',
                color: '#f8fafc',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
              }}
            >
              {isSubmitting ? 'Saving...' : preference ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

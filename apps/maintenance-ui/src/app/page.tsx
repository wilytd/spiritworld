'use client'

import { useState, useEffect } from 'react'
import TaskForm from '../components/TaskForm'
import SnoozeDialog from '../components/SnoozeDialog'

interface Task {
  id: number
  title: string
  description: string | null
  category: string
  priority: string
  status: string
  due_date: string | null
  mesh_notify: boolean
  snooze_until: string | null
  recurrence_rule: string | null
}

interface SystemStatus {
  service: string
  version: string
  database: string
  mesh_bridge: string
  uptime_seconds: number
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)

  // Modal states
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [showRecurringForm, setShowRecurringForm] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [snoozeTask, setSnoozeTask] = useState<Task | null>(null)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  async function fetchData() {
    try {
      const [tasksRes, statusRes] = await Promise.all([
        fetch(`${API_URL}/api/tasks/`),
        fetch(`${API_URL}/api/status/`)
      ])

      if (tasksRes.ok) {
        setTasks(await tasksRes.json())
      }
      if (statusRes.ok) {
        setStatus(await statusRes.json())
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateTask(data: any) {
    const response = await fetch(`${API_URL}/api/tasks/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...data,
        due_date: data.due_date || null,
      }),
    })
    if (response.ok) {
      setShowTaskForm(false)
      fetchData()
    }
  }

  async function handleCreateRecurringTask(data: any) {
    const response = await fetch(`${API_URL}/api/tasks/recurring`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (response.ok) {
      setShowRecurringForm(false)
      fetchData()
    }
  }

  async function handleUpdateTask(data: any) {
    if (!editingTask) return
    const response = await fetch(`${API_URL}/api/tasks/${editingTask.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...data,
        due_date: data.due_date || null,
      }),
    })
    if (response.ok) {
      setEditingTask(null)
      fetchData()
    }
  }

  async function handleCompleteTask(taskId: number) {
    const response = await fetch(`${API_URL}/api/tasks/${taskId}/complete`, {
      method: 'POST',
    })
    if (response.ok) {
      fetchData()
    }
  }

  async function handleDeleteTask(taskId: number) {
    if (!confirm('Are you sure you want to delete this task?')) return
    const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
      method: 'DELETE',
    })
    if (response.ok) {
      fetchData()
    }
  }

  async function handleSnoozeTask(durationMinutes?: number, until?: string) {
    if (!snoozeTask) return
    const body: any = {}
    if (durationMinutes) body.duration_minutes = durationMinutes
    if (until) body.until = until

    const response = await fetch(`${API_URL}/api/tasks/${snoozeTask.id}/snooze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (response.ok) {
      setSnoozeTask(null)
      fetchData()
    }
  }

  async function handleUnsnoozeTask(taskId: number) {
    const response = await fetch(`${API_URL}/api/tasks/${taskId}/unsnooze`, {
      method: 'POST',
    })
    if (response.ok) {
      fetchData()
    }
  }

  function getPriorityColor(priority: string): string {
    switch (priority) {
      case 'critical': return '#ef4444'
      case 'high': return '#f97316'
      case 'medium': return '#eab308'
      case 'low': return '#22c55e'
      default: return '#64748b'
    }
  }

  function getStatusBadge(status: string): string {
    switch (status) {
      case 'completed': return '#22c55e'
      case 'in_progress': return '#3b82f6'
      case 'snoozed': return '#8b5cf6'
      default: return '#64748b'
    }
  }

  const actionButtonStyle = {
    padding: '0.25rem 0.5rem',
    fontSize: '0.75rem',
    border: 'none',
    borderRadius: '0.25rem',
    cursor: 'pointer',
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '2rem' }}>Aegis Mesh Dashboard</h1>
          <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>
            Home Lab Maintenance & Mesh Network Management
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setShowTaskForm(true)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
            }}
          >
            + New Task
          </button>
          <button
            onClick={() => setShowRecurringForm(true)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#7c3aed',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
            }}
          >
            + Recurring
          </button>
          <a
            href="/settings"
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#334155',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            Settings
          </a>
        </div>
      </header>

      {/* Status Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <StatusCard
          title="Core Service"
          value={status?.database === 'connected' ? 'Online' : 'Offline'}
          status={status?.database === 'connected' ? 'success' : 'error'}
        />
        <StatusCard
          title="Mesh Bridge"
          value={status?.mesh_bridge === 'connected' ? 'Connected' : 'Disconnected'}
          status={status?.mesh_bridge === 'connected' ? 'success' : 'warning'}
        />
        <StatusCard
          title="Pending Tasks"
          value={tasks.filter(t => t.status === 'pending').length.toString()}
          status="info"
        />
        <StatusCard
          title="Uptime"
          value={status ? formatUptime(status.uptime_seconds) : '--'}
          status="info"
        />
      </section>

      {/* Tasks Section */}
      <section>
        <h2 style={{ marginBottom: '1rem' }}>Maintenance Tasks</h2>
        {loading ? (
          <p>Loading tasks...</p>
        ) : tasks.length === 0 ? (
          <p style={{ color: '#64748b' }}>No maintenance tasks scheduled.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {tasks.map(task => (
              <div
                key={task.id}
                style={{
                  backgroundColor: '#1e293b',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                  borderLeft: `4px solid ${getPriorityColor(task.priority)}`,
                  opacity: task.status === 'completed' ? 0.6 : 1,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ margin: 0, fontSize: '1rem', textDecoration: task.status === 'completed' ? 'line-through' : 'none' }}>
                      {task.title}
                    </h3>
                    <p style={{ margin: '0.25rem 0 0', color: '#94a3b8', fontSize: '0.875rem' }}>
                      {task.category}
                      {task.due_date && ` | Due: ${new Date(task.due_date).toLocaleDateString()}`}
                      {task.snooze_until && ` | Snoozed until: ${new Date(task.snooze_until).toLocaleString()}`}
                      {task.recurrence_rule && ` | Recurring: ${task.recurrence_rule}`}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    {task.mesh_notify && (
                      <span style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem', backgroundColor: '#1d4ed8', borderRadius: '0.25rem' }}>
                        Mesh Alert
                      </span>
                    )}
                    <span style={{
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.5rem',
                      backgroundColor: getStatusBadge(task.status),
                      borderRadius: '0.25rem',
                      textTransform: 'capitalize'
                    }}>
                      {task.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {/* Action buttons */}
                {task.status !== 'completed' && (
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                    <button
                      onClick={() => handleCompleteTask(task.id)}
                      style={{ ...actionButtonStyle, backgroundColor: '#22c55e', color: 'white' }}
                    >
                      Complete
                    </button>
                    <button
                      onClick={() => setEditingTask(task)}
                      style={{ ...actionButtonStyle, backgroundColor: '#3b82f6', color: 'white' }}
                    >
                      Edit
                    </button>
                    {task.status === 'snoozed' ? (
                      <button
                        onClick={() => handleUnsnoozeTask(task.id)}
                        style={{ ...actionButtonStyle, backgroundColor: '#8b5cf6', color: 'white' }}
                      >
                        Unsnooze
                      </button>
                    ) : (
                      <button
                        onClick={() => setSnoozeTask(task)}
                        style={{ ...actionButtonStyle, backgroundColor: '#8b5cf6', color: 'white' }}
                      >
                        Snooze
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteTask(task.id)}
                      style={{ ...actionButtonStyle, backgroundColor: '#ef4444', color: 'white' }}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Modals */}
      {showTaskForm && (
        <TaskForm
          onSubmit={handleCreateTask}
          onCancel={() => setShowTaskForm(false)}
        />
      )}

      {showRecurringForm && (
        <TaskForm
          onSubmit={handleCreateRecurringTask}
          onCancel={() => setShowRecurringForm(false)}
          isRecurring
        />
      )}

      {editingTask && (
        <TaskForm
          task={editingTask}
          onSubmit={handleUpdateTask}
          onCancel={() => setEditingTask(null)}
        />
      )}

      {snoozeTask && (
        <SnoozeDialog
          taskTitle={snoozeTask.title}
          onSnooze={handleSnoozeTask}
          onCancel={() => setSnoozeTask(null)}
        />
      )}
    </main>
  )
}

function StatusCard({ title, value, status }: { title: string; value: string; status: 'success' | 'warning' | 'error' | 'info' }) {
  const colors = {
    success: '#22c55e',
    warning: '#eab308',
    error: '#ef4444',
    info: '#3b82f6'
  }

  return (
    <div style={{
      backgroundColor: '#1e293b',
      borderRadius: '0.5rem',
      padding: '1rem',
      borderTop: `3px solid ${colors[status]}`
    }}>
      <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.875rem' }}>{title}</p>
      <p style={{ margin: '0.5rem 0 0', fontSize: '1.5rem', fontWeight: 'bold' }}>{value}</p>
    </div>
  )
}

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

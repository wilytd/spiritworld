'use client'

import { useForm } from 'react-hook-form'
import { format } from 'date-fns'

interface TaskFormData {
  title: string
  description: string
  category: string
  priority: string
  due_date: string
  mesh_notify: boolean
  recurrence_rule?: string
}

interface TaskFormProps {
  task?: TaskFormData & { id?: number }
  onSubmit: (data: TaskFormData) => Promise<void>
  onCancel: () => void
  isRecurring?: boolean
}

const categories = ['network', 'security', 'backup', 'monitoring', 'hardware', 'software', 'other']
const priorities = ['low', 'medium', 'high', 'critical']

export default function TaskForm({ task, onSubmit, onCancel, isRecurring = false }: TaskFormProps) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<TaskFormData>({
    defaultValues: task ? {
      ...task,
      due_date: task.due_date ? format(new Date(task.due_date), "yyyy-MM-dd'T'HH:mm") : '',
    } : {
      title: '',
      description: '',
      category: 'network',
      priority: 'medium',
      due_date: '',
      mesh_notify: false,
      recurrence_rule: '',
    }
  })

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

  const errorStyle = {
    color: '#ef4444',
    fontSize: '0.75rem',
    marginTop: '0.25rem',
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
        maxWidth: '500px',
        maxHeight: '90vh',
        overflow: 'auto',
      }}>
        <h2 style={{ margin: '0 0 1rem', fontSize: '1.25rem' }}>
          {task?.id ? 'Edit Task' : isRecurring ? 'Create Recurring Task' : 'Create Task'}
        </h2>

        <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={labelStyle}>Title *</label>
            <input
              {...register('title', { required: 'Title is required' })}
              style={inputStyle}
              placeholder="Task title"
            />
            {errors.title && <p style={errorStyle}>{errors.title.message}</p>}
          </div>

          <div>
            <label style={labelStyle}>Description</label>
            <textarea
              {...register('description')}
              style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }}
              placeholder="Task description (optional)"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={labelStyle}>Category *</label>
              <select
                {...register('category', { required: 'Category is required' })}
                style={inputStyle}
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={labelStyle}>Priority</label>
              <select {...register('priority')} style={inputStyle}>
                {priorities.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
          </div>

          {isRecurring ? (
            <div>
              <label style={labelStyle}>Recurrence Rule (Cron) *</label>
              <input
                {...register('recurrence_rule', {
                  required: isRecurring ? 'Cron expression is required for recurring tasks' : false,
                })}
                style={inputStyle}
                placeholder="0 9 * * 1 (every Monday at 9am)"
              />
              <p style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                Format: minute hour day month weekday
              </p>
              {errors.recurrence_rule && <p style={errorStyle}>{errors.recurrence_rule.message}</p>}
            </div>
          ) : (
            <div>
              <label style={labelStyle}>Due Date</label>
              <input
                type="datetime-local"
                {...register('due_date')}
                style={inputStyle}
              />
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              {...register('mesh_notify')}
              id="mesh_notify"
              style={{ width: '1rem', height: '1rem' }}
            />
            <label htmlFor="mesh_notify" style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
              Send mesh network notification when due
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
              {isSubmitting ? 'Saving...' : task?.id ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

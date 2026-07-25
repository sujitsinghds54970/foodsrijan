import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'

import { getApiErrorMessage, staffApi, taskApi } from './api'
import { StaffSummary, TaskItem } from './types'

const priorities = ['Low', 'Medium', 'High', 'Urgent']

export default function TaskAssignmentPanel() {
  const [staff, setStaff] = useState<StaffSummary[]>([])
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const [assignedTo, setAssignedTo] = useState<number>(0)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [priority, setPriority] = useState('Medium')

  const load = async () => {
    try {
      setLoading(true)
      const [staffRows, taskRows] = await Promise.all([
        staffApi.list(),
        taskApi.list(),
      ])
      const eligible = staffRows.filter((row) => typeof row.user_id === 'number')
      setStaff(eligible)
      setTasks(taskRows)
      if (!assignedTo && eligible.length > 0) {
        setAssignedTo(Number(eligible[0].user_id))
      } else if (assignedTo && !eligible.some((row) => Number(row.user_id) === assignedTo)) {
        setAssignedTo(eligible.length ? Number(eligible[0].user_id) : 0)
      }
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load task panel'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const activeTasks = useMemo(() => tasks.filter((task) => task.status !== 'Completed' && task.status !== 'Cancelled'), [tasks])

  const createTask = async () => {
    if (!assignedTo || !title.trim()) {
      toast.error('Please select staff and enter task title')
      return
    }

    try {
      setSubmitting(true)
      const task = await taskApi.create({
        assigned_to: assignedTo,
        title: title.trim(),
        description: description.trim() || undefined,
        due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
        priority,
      })
      setTasks((prev) => [task, ...prev])
      setTitle('')
      setDescription('')
      setDueDate('')
      setPriority('Medium')
      toast.success('Task created')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to create task'))
    } finally {
      setSubmitting(false)
    }
  }

  const cancelTask = async (taskId: number) => {
    try {
      const updated = await taskApi.updateStatus(taskId, 'Cancelled')
      setTasks((prev) => prev.map((task) => (task.id === taskId ? { ...task, ...updated } : task)))
      toast.success('Task cancelled')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to cancel task'))
    }
  }

  const reassignTask = async (task: TaskItem, nextUserId: number) => {
    try {
      const updated = await taskApi.update(task.id, { assigned_to: nextUserId })
      setTasks((prev) => prev.map((row) => (row.id === task.id ? { ...row, ...updated } : row)))
      toast.success('Task reassigned')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to reassign task'))
    }
  }

  const completionRate = useMemo(() => {
    if (!tasks.length) return 0
    const completed = tasks.filter((task) => task.status === 'Completed').length
    return Math.round((completed / tasks.length) * 100)
  }, [tasks])

  const bonusCandidates = useMemo(() => {
    const grouped = new Map<number, { total: number; completed: number }>()
    tasks.forEach((task) => {
      if (!task.assigned_to) return
      const row = grouped.get(task.assigned_to) || { total: 0, completed: 0 }
      row.total += 1
      if (task.status === 'Completed') row.completed += 1
      grouped.set(task.assigned_to, row)
    })

    return Array.from(grouped.entries())
      .filter(([, stat]) => stat.total >= 5 && stat.completed / stat.total >= 0.9)
      .map(([userId, stat]) => ({ userId, completionRate: Math.round((stat.completed / stat.total) * 100) }))
  }, [tasks])

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-lg font-bold text-slate-900">Assign Tasks</h3>
        <p className="text-sm text-slate-600">Create tasks, monitor overdue items, and collaborate with staff.</p>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <select value={assignedTo} onChange={(event) => setAssignedTo(Number(event.target.value))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            {staff.length === 0 && <option value={0}>No staff found</option>}
            {staff.map((row) => (
              <option key={row.staff_profile_id} value={Number(row.user_id)}>{row.full_name}</option>
            ))}
          </select>
          <select value={priority} onChange={(event) => setPriority(event.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            {priorities.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Task title"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2"
          />
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Task description"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2"
            rows={3}
          />
          <input type="datetime-local" value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button
            type="button"
            disabled={submitting || staff.length === 0}
            onClick={() => void createTask()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting ? 'Creating...' : 'Create Task'}
          </button>
        </div>
        {staff.length === 0 && (
          <p className="mt-2 text-xs text-rose-600">No assignable staff found for this branch. Please create staff first.</p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase text-slate-500">Active Tasks</p>
          <p className="mt-1 text-2xl font-black text-slate-900">{activeTasks.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase text-slate-500">Completion Rate</p>
          <p className="mt-1 text-2xl font-black text-slate-900">{completionRate}%</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase text-slate-500">Bonus Candidates</p>
          <p className="mt-1 text-2xl font-black text-slate-900">{bonusCandidates.length}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900">All Active Tasks</h3>
          <button type="button" onClick={() => void load()} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">Refresh</button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Loading tasks...</p>
        ) : activeTasks.length === 0 ? (
          <p className="text-sm text-slate-500">No active tasks.</p>
        ) : (
          <div className="space-y-2">
            {activeTasks.map((task) => {
              const isOverdue = task.status === 'Overdue'
              return (
                <div key={task.id} className={`rounded-lg border px-3 py-3 ${isOverdue ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-white'}`}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{task.title || task.task_name}</p>
                      <p className="text-xs text-slate-500">Due: {task.due_date ? new Date(task.due_date).toLocaleString() : '-'}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={task.assigned_to || 0}
                        onChange={(event) => void reassignTask(task, Number(event.target.value))}
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                      >
                        {staff.map((row) => (
                          <option key={row.staff_profile_id} value={Number(row.user_id)}>{row.full_name}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => void cancelTask(task.id)}
                        className="rounded bg-rose-600 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-slate-600">{task.description || 'No description'}</div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-base font-bold text-slate-900">Performance Bonus Watchlist</h3>
        {bonusCandidates.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No staff has crossed the 90% completion threshold yet.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {bonusCandidates.map((row) => {
              const member = staff.find((item) => item.user_id === row.userId)
              return (
                <div key={row.userId} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-900">{member?.full_name || `User ${row.userId}`}</p>
                  <button
                    type="button"
                    className="rounded bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-700"
                    onClick={() => toast.success('Bonus candidate tagged for payroll review')}
                  >
                    Trigger Bonus Review ({row.completionRate}%)
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

import { ChangeEvent, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'

import { getApiErrorMessage, resolveStaffMediaUrl, taskApi } from './api'
import { TaskAttachmentItem, TaskCommentItem, TaskItem } from './types'

const columns: Array<'Pending' | 'In Progress' | 'Completed' | 'Overdue'> = ['Pending', 'In Progress', 'Completed', 'Overdue']

export default function TasksAllottedTab() {
  const [loading, setLoading] = useState(true)
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [activeTask, setActiveTask] = useState<TaskItem | null>(null)
  const [comments, setComments] = useState<TaskCommentItem[]>([])
  const [attachments, setAttachments] = useState<TaskAttachmentItem[]>([])
  const [commentText, setCommentText] = useState('')
  const [commentBusy, setCommentBusy] = useState(false)
  const [uploadBusy, setUploadBusy] = useState(false)
  const [statusBusyId, setStatusBusyId] = useState<number | null>(null)
  const [previewFileUrl, setPreviewFileUrl] = useState<string>('')

  const loadTasks = async () => {
    try {
      setLoading(true)
      const rows = await taskApi.list()
      setTasks(rows)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load tasks'))
    } finally {
      setLoading(false)
    }
  }

  const openTask = async (task: TaskItem) => {
    setActiveTask(task)
    try {
      const [commentRows, attachmentRows] = await Promise.all([
        taskApi.listComments(task.id),
        taskApi.listAttachments(task.id),
      ])
      setComments(commentRows)
      setAttachments(attachmentRows)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load task details'))
    }
  }

  useEffect(() => {
    void loadTasks()
  }, [])

  const grouped = useMemo(() => {
    return {
      Pending: tasks.filter((task) => task.status === 'Pending'),
      'In Progress': tasks.filter((task) => task.status === 'In Progress'),
      Completed: tasks.filter((task) => task.status === 'Completed'),
      Overdue: tasks.filter((task) => task.status === 'Overdue'),
    }
  }, [tasks])

  const statusBadge = (status: string) => {
    const key = status.toLowerCase()
    if (key === 'completed') return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    if (key === 'in progress') return 'bg-amber-100 text-amber-700 border-amber-200'
    if (key === 'overdue') return 'bg-red-100 text-red-700 border-red-200'
    return 'bg-slate-100 text-slate-700 border-slate-200'
  }

  const priorityBadge = (priority: string) => {
    const key = priority.toLowerCase()
    if (key === 'urgent') return 'bg-red-600 text-white'
    if (key === 'high') return 'bg-red-100 text-red-700'
    if (key === 'medium') return 'bg-amber-100 text-amber-700'
    return 'bg-emerald-100 text-emerald-700'
  }

  const updateStatus = async (taskId: number, status: 'Pending' | 'In Progress' | 'Completed' | 'Overdue' | 'Cancelled') => {
    try {
      setStatusBusyId(taskId)
      const updated = await taskApi.updateStatus(taskId, status)
      setTasks((prev) => prev.map((item) => (item.id === taskId ? { ...item, ...updated } : item)))
      if (activeTask?.id === taskId) {
        setActiveTask((prev) => (prev ? { ...prev, ...updated } : prev))
      }
      toast.success('Task status updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to update status'))
    } finally {
      setStatusBusyId(null)
    }
  }

  const markCompleted = async (task: TaskItem, attachmentFile?: File | null) => {
    const shouldProceed = window.confirm('Mark this task as completed?')
    if (!shouldProceed) return

    try {
      setStatusBusyId(task.id)
      if (attachmentFile) {
        await taskApi.uploadAttachment(task.id, attachmentFile)
      }
      const updated = await taskApi.updateStatus(task.id, 'Completed')
      setTasks((prev) => prev.map((item) => (item.id === task.id ? { ...item, ...updated } : item)))
      if (activeTask?.id === task.id) {
        setActiveTask((prev) => (prev ? { ...prev, ...updated } : prev))
      }
      toast.success('Task marked completed')
      if (activeTask?.id === task.id) {
        const attachmentRows = await taskApi.listAttachments(task.id)
        setAttachments(attachmentRows)
      }
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to mark task completed'))
    } finally {
      setStatusBusyId(null)
    }
  }

  const submitComment = async () => {
    if (!activeTask || !commentText.trim()) return
    try {
      setCommentBusy(true)
      const comment = await taskApi.addComment(activeTask.id, commentText.trim())
      setComments((prev) => [...prev, comment])
      setCommentText('')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to send comment'))
    } finally {
      setCommentBusy(false)
    }
  }

  const onUploadAttachment = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !activeTask) return
    try {
      setUploadBusy(true)
      const row = await taskApi.uploadAttachment(activeTask.id, file)
      setAttachments((prev) => [row, ...prev])
      toast.success('Attachment uploaded')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to upload attachment'))
    } finally {
      setUploadBusy(false)
      event.target.value = ''
    }
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900/80">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Tasks Allotted</h2>
        <button
          type="button"
          onClick={() => void loadTasks()}
          className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <p className="text-slate-600 dark:text-slate-300">Loading tasks...</p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-4">
          {columns.map((status) => (
            <div key={status} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
              <p className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-700 dark:text-slate-200">{status}</p>
              <div className="space-y-3">
                {grouped[status].length === 0 ? (
                  <p className="text-xs text-slate-500 dark:text-slate-400">No tasks</p>
                ) : (
                  grouped[status].map((task) => (
                    <article
                      key={task.id}
                      className="cursor-pointer rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition hover:shadow-md dark:border-slate-700 dark:bg-slate-900"
                      onClick={() => void openTask(task)}
                    >
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{task.title || task.task_name}</p>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${priorityBadge(task.priority)}`}>{task.priority}</span>
                      </div>

                      <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2">{task.description || 'No description provided.'}</p>

                      <div className="mt-2 flex items-center justify-between">
                        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusBadge(task.status)}`}>{task.status}</span>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400">
                          Due {task.due_date ? new Date(task.due_date).toLocaleDateString() : '-'}
                        </span>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {(task.status === 'Pending' || task.status === 'Overdue') && (
                          <button
                            type="button"
                            disabled={statusBusyId === task.id}
                            onClick={(event) => {
                              event.stopPropagation()
                              void updateStatus(task.id, 'In Progress')
                            }}
                            className="rounded-md bg-amber-500 px-2 py-1 text-[11px] font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
                          >
                            Start
                          </button>
                        )}

                        {task.status !== 'Completed' && (
                          <label
                            className="rounded-md bg-emerald-600 px-2 py-1 text-[11px] font-semibold text-white hover:bg-emerald-700"
                            onClick={(event) => event.stopPropagation()}
                          >
                            Mark Completed
                            <input
                              type="file"
                              accept=".jpg,.jpeg,.png,.pdf,.webp"
                              className="hidden"
                              onChange={(event) => {
                                void markCompleted(task, event.target.files?.[0] || null)
                                event.target.value = ''
                              }}
                            />
                          </label>
                        )}
                      </div>
                    </article>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/40" onClick={() => setActiveTask(null)}>
          <div
            className="h-full w-full max-w-xl overflow-y-auto bg-white p-5 shadow-2xl dark:bg-slate-900"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">{activeTask.title || activeTask.task_name}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Due: {activeTask.due_date ? new Date(activeTask.due_date).toLocaleString() : '-'}</p>
              </div>
              <button className="rounded border px-3 py-1.5 text-sm" onClick={() => setActiveTask(null)}>Close</button>
            </div>

            <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <p className="text-sm text-slate-700 dark:text-slate-200">{activeTask.description || 'No description provided.'}</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400">
                <p>Assigned By: {activeTask.assigned_by || '-'}</p>
                <p>Status: {activeTask.status}</p>
                <p>Priority: {activeTask.priority}</p>
                <p>Due Date: {activeTask.due_date ? new Date(activeTask.due_date).toLocaleDateString() : '-'}</p>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <div className="mb-2 flex items-center justify-between">
                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">Attachments</h4>
                <label className="cursor-pointer rounded bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-700">
                  {uploadBusy ? 'Uploading...' : 'Upload'}
                  <input type="file" className="hidden" accept=".jpg,.jpeg,.png,.pdf,.webp" onChange={(event) => void onUploadAttachment(event)} />
                </label>
              </div>
              {attachments.length === 0 ? (
                <p className="text-xs text-slate-500">No attachments yet.</p>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  {attachments.map((row) => (
                    <button
                      key={row.id}
                      type="button"
                      onClick={() => setPreviewFileUrl(resolveStaffMediaUrl(row.file_url))}
                      className="rounded border border-slate-200 px-2 py-2 text-left text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200"
                    >
                      <p className="truncate">{row.file_url.split('/').pop()}</p>
                      <p className="mt-1 text-[10px] text-slate-500">{row.created_at ? new Date(row.created_at).toLocaleString() : ''}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <h4 className="mb-2 text-sm font-bold text-slate-900 dark:text-slate-100">Comments</h4>
              <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
                {comments.length === 0 ? (
                  <p className="text-xs text-slate-500">No comments yet.</p>
                ) : (
                  comments.map((row) => (
                    <div key={row.id} className="rounded-lg border border-slate-200 px-3 py-2 text-xs dark:border-slate-700">
                      <p className="text-slate-700 dark:text-slate-200">{row.message}</p>
                      <p className="mt-1 text-[10px] text-slate-500">{row.created_at ? new Date(row.created_at).toLocaleString() : ''}</p>
                    </div>
                  ))
                )}
              </div>
              <div className="mt-3 flex gap-2">
                <input
                  type="text"
                  value={commentText}
                  onChange={(event) => setCommentText(event.target.value)}
                  placeholder="Ask question or add update"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                />
                <button
                  type="button"
                  disabled={commentBusy || !commentText.trim()}
                  onClick={() => void submitComment()}
                  className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700 disabled:opacity-60"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {!!previewFileUrl && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4" onClick={() => setPreviewFileUrl('')}>
          {previewFileUrl.toLowerCase().endsWith('.pdf') ? (
            <div className="h-[85vh] w-[95vw] overflow-hidden rounded-xl border border-white/30 bg-white" onClick={(e) => e.stopPropagation()}>
              <iframe src={previewFileUrl} title="task-attachment-preview" className="h-full w-full" />
            </div>
          ) : (
            <img src={previewFileUrl} alt="task-attachment-preview" className="max-h-[85vh] max-w-[95vw] rounded-xl border border-white/30 object-contain" onClick={(e) => e.stopPropagation()} />
          )}
        </div>
      )}
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'

import { getApiErrorMessage, staffSelfApi } from './api'
import { StaffNotification } from './types'

export default function NotificationsTab() {
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<StaffNotification[]>([])

  const loadItems = async () => {
    try {
      setLoading(true)
      const data = await staffSelfApi.getNotifications()
      setItems(data)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load notifications'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadItems()
  }, [])

  const unreadCount = useMemo(() => items.filter((item) => !item.is_read).length, [items])

  const markRead = async (id: number) => {
    try {
      await staffSelfApi.markNotificationRead(id)
      setItems((prev) => prev.map((item) => (item.id === id ? { ...item, is_read: true, status: 'read' } : item)))
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to mark notification as read'))
    }
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900/80">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Important Notification</h2>
        {unreadCount > 0 && <span className="rounded-full bg-red-600 px-2.5 py-1 text-xs font-bold text-white">{unreadCount} unread</span>}
      </div>
      {loading ? (
        <p className="text-slate-600 dark:text-slate-300">Loading notifications...</p>
      ) : items.length === 0 ? (
        <p className="text-slate-500 dark:text-slate-400">No notifications yet.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className={`rounded-xl border p-4 ${item.is_read ? 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800' : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{item.title}</p>
                  <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{item.message}</p>
                  {item.link && <a href={item.link} className="mt-2 inline-block text-sm font-semibold text-indigo-600 hover:underline dark:text-indigo-300">Open link</a>}
                </div>
                {!item.is_read && (
                  <button onClick={() => void markRead(item.id)} className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-black dark:bg-slate-200 dark:text-slate-900">
                    Mark as Read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

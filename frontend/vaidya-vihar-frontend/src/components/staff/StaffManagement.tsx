import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { getApiErrorMessage, staffApi } from './api'
import StaffDirectory from './StaffDirectory'
import StaffProfile from './StaffProfile'
import TaskAssignmentPanel from './TaskAssignmentPanel'
import { StaffCreatePayload, StaffDetail, StaffSummary } from './types'

export default function StaffManagement() {
  const { user } = useAuth()
  const role = (user?.role || '').trim().toLowerCase()

  const [items, setItems] = useState<StaffSummary[]>([])
  const [activeSection, setActiveSection] = useState<'directory' | 'tasks'>('directory')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [selectedStaff, setSelectedStaff] = useState<StaffDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  const isAllowed = role === 'branch_admin' || role === 'branch_director'

  const loadList = async (searchText?: string) => {
    if (!isAllowed) return
    setLoading(true)
    try {
      const rows = await staffApi.list(searchText)
      // Filter out inactive staff (extra safety - should already be filtered by backend)
      const activeRows = rows.filter(row => row.status === 'active')
      setItems(activeRows)
      setSelectedIds((prev) => prev.filter((id) => activeRows.some((row) => row.staff_profile_id === id)))
      if (!selectedId && activeRows.length > 0) {
        setSelectedId(activeRows[0].staff_profile_id)
      }
      if (selectedId && !activeRows.find((x) => x.staff_profile_id === selectedId)) {
        setSelectedId(activeRows[0]?.staff_profile_id || null)
      }
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to load staff directory'))
    } finally {
      setLoading(false)
    }
  }

  const loadDetail = async (staffId: number) => {
    try {
      const detail = await staffApi.get(staffId)
      setSelectedStaff(detail)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to load staff profile'))
    }
  }

  const handleCreate = async (payload: StaffCreatePayload) => {
    try {
      const response = await staffApi.create(payload)
      if (response.temporary_password) {
        toast.success(`Created. Temporary password: ${response.temporary_password}`)
      } else {
        toast.success('Staff created successfully')
      }
      await loadList(search)
      if (response.staff?.staff_profile_id) {
        setSelectedId(response.staff.staff_profile_id)
      }
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to create staff'))
    }
  }

  const handleBulkToggleDailyOps = async (canAccess: boolean) => {
    if (selectedIds.length === 0) {
      toast.error('Select at least one staff member')
      return
    }

    try {
      const updatedCount = await staffApi.bulkToggleDailyOps(selectedIds, canAccess)
      toast.success(`Updated Daily Operations access for ${updatedCount} staff`) 
      setItems((prev) => prev.map((item) => (
        selectedIds.includes(item.staff_profile_id)
          ? { ...item, can_access_daily_ops: canAccess }
          : item
      )))
      setSelectedStaff((prev) => (
        prev && selectedIds.includes(prev.staff_profile_id)
          ? { ...prev, can_access_daily_ops: canAccess }
          : prev
      ))
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to update Daily Operations access'))
    }
  }

  const handleDeleteStaff = async (staffId: number) => {
    try {
      await staffApi.delete(staffId)
      toast.success('Staff member deactivated successfully')
      // Refresh the staff list
      await loadList(search)
      // Clear selection if deleted staff was selected
      if (selectedId === staffId) {
        setSelectedId(null)
        setSelectedStaff(null)
      }
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to deactivate staff member'))
    }
  }

  useEffect(() => {
    loadList()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAllowed])

  useEffect(() => {
    if (!selectedId) {
      setSelectedStaff(null)
      return
    }
    loadDetail(selectedId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  const headerText = useMemo(() => {
    if (role === 'branch_director') return 'Director Staff Control'
    if (role === 'branch_admin') return 'Branch Staff Control'
    return 'Staff Management'
  }, [role])

  if (!isAllowed) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-700">
        Access denied. Staff management is available only to branch director and branch admin.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-r from-emerald-100 via-cyan-100 to-sky-100 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-black text-slate-900">{headerText}</h1>
            <p className="text-sm text-slate-700">100% branch-scoped staff operations for authenticated branch users.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveSection('directory')}
              className={`rounded-lg px-3 py-2 text-sm font-semibold ${activeSection === 'directory' ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 border border-slate-300'}`}
            >
              Staff Directory
            </button>
            <button
              type="button"
              onClick={() => setActiveSection('tasks')}
              className={`rounded-lg px-3 py-2 text-sm font-semibold ${activeSection === 'tasks' ? 'bg-blue-600 text-white' : 'bg-white text-slate-700 border border-slate-300'}`}
            >
              Assign Tasks
            </button>
          </div>
        </div>
      </div>

      {activeSection === 'directory' ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
          <StaffDirectory
            items={items}
            selectedId={selectedId}
            selectedIds={selectedIds}
            loading={loading}
            onSelect={setSelectedId}
            onToggleSelect={(id) => {
              setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))
            }}
            onToggleSelectAll={(checked) => {
              setSelectedIds(checked ? items.map((item) => item.staff_profile_id) : [])
            }}
            onCreate={handleCreate}
            onBulkToggleDailyOps={handleBulkToggleDailyOps}
            onDelete={handleDeleteStaff}
            onSearch={(value) => {
             setSearch(value)
             loadList(value)
            }}
          />

          {selectedStaff ? (
            <StaffProfile
              key={selectedStaff.staff_profile_id}
              staff={selectedStaff}
              canReviewLeave={role === 'branch_director' || role === 'branch_admin'}
              onChanged={(next) => {
                setSelectedStaff(next)
                setItems((prev) => prev.map((x) => (x.staff_profile_id === next.staff_profile_id ? { ...x, ...next } : x)))
              }}
            />
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
              Select a staff member to view profile.
            </div>
          )}
        </div>
      ) : (
        <TaskAssignmentPanel />
      )}
    </div>
  )
}

import { useMemo } from 'react'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'

import { PayrollRunItem } from './types'

interface PayrollRunListProps {
  runs: PayrollRunItem[]
  onApprove: (run: PayrollRunItem) => void
}

const columnHelper = createColumnHelper<PayrollRunItem>()

const statusClass = (status: string) => {
  const s = status.toLowerCase()
  if (s === 'locked') return 'bg-slate-900 text-white'
  if (s === 'approved') return 'bg-green-600 text-white'
  if (s === 'ready') return 'bg-blue-600 text-white'
  return 'bg-amber-500 text-white'
}

export default function PayrollRunList({ runs, onApprove }: PayrollRunListProps) {
  const columns = useMemo(
    () => [
      columnHelper.accessor('month', {
        header: 'Month',
        cell: (ctx) => String(ctx.getValue()).padStart(2, '0'),
      }),
      columnHelper.accessor('year', {
        header: 'Year',
      }),
      columnHelper.accessor('total_net_pay', {
        header: 'Total Net',
        cell: (ctx) => `INR ${ctx.getValue().toLocaleString()}`,
      }),
      columnHelper.accessor('status', {
        header: 'Status',
        cell: (ctx) => (
          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(ctx.getValue())}`}>
            {ctx.getValue()}
          </span>
        ),
      }),
      columnHelper.display({
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <button
            type="button"
            onClick={() => onApprove(row.original)}
            disabled={(row.original.status || '').toLowerCase() === 'locked'}
            className="rounded bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            Approve For Payment
          </button>
        ),
      }),
    ],
    [onApprove],
  )

  const table = useReactTable({
    data: runs,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-3 py-2 text-left text-xs font-semibold uppercase text-slate-600">
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.length === 0 ? (
            <tr>
              <td className="px-3 py-4 text-center text-slate-500" colSpan={5}>No payroll runs found.</td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t border-slate-100">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2 text-slate-700">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

import { useQuery } from "@tanstack/react-query"

import { snapshotDiffOptions } from "@/api/queries"
import type { DiffRow } from "@/api/types"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

function sortDiffRows(rows: DiffRow[]) {
  return [...rows].sort((a, b) => {
    const priority = (row: DiffRow) => {
      if (row.field_type === "departed") return 3
      if (row.field_type === "added") return 2
      if (row.field_type === "direction_label") return 1
      return 0
    }
    return priority(a) - priority(b) || Math.abs(b.delta ?? 0) - Math.abs(a.delta ?? 0)
  })
}

function rowColor(row: DiffRow) {
  if (row.field_type === "direction_label") return "text-foreground"
  if (row.field_type === "departed") return "italic text-muted-foreground"
  if (row.field_type === "added") return "text-green-700 dark:text-green-300"
  if ((row.delta ?? 0) > 0) return "text-green-700 dark:text-green-300"
  if ((row.delta ?? 0) < 0) return "text-red-600 dark:text-red-400"
  return "text-muted-foreground"
}

export function SnapshotDiffView({
  leagueId,
  snapshotId,
  rosterId,
  anchorLabel,
}: {
  leagueId: string
  snapshotId: number
  rosterId: number
  anchorLabel: string
}) {
  const query = useQuery(snapshotDiffOptions(leagueId, snapshotId, rosterId))

  if (query.isLoading) {
    return (
      <div className="mt-4 space-y-2">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-6 w-full rounded" />
        ))}
      </div>
    )
  }

  if (query.isError) {
    return (
      <p className="mt-4 text-sm text-muted-foreground">
        Snapshot comparison unavailable. Check that the backend is running, then refresh.
      </p>
    )
  }

  const rows = sortDiffRows(query.data ?? [])

  return (
    <div className="mt-4 space-y-4">
      <p className="text-sm text-muted-foreground">
        What changed since {anchorLabel}
      </p>
      {rows.length ? (
        <div className="flex flex-col gap-2">
          {rows.map((row) => (
            <div
              key={`${row.field}-${row.field_type}-${row.display_string}`}
              className="flex items-center justify-between gap-4 py-1"
            >
              <span className="text-xs text-muted-foreground">{row.field}</span>
              <span className={cn("text-sm", rowColor(row))}>{row.display_string}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-center text-sm text-muted-foreground">
          No changes detected since this snapshot.
        </p>
      )}
    </div>
  )
}

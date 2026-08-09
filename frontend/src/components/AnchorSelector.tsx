import { useQuery } from "@tanstack/react-query"

import { snapshotAnchorsOptions } from "@/api/queries"
import type { SnapshotAnchor } from "@/api/types"
import { Skeleton } from "@/components/ui/skeleton"

export function AnchorSelector({
  leagueId,
  selectedAnchorId,
  onSelect,
}: {
  leagueId: string
  selectedAnchorId: number | null
  onSelect: (anchor: SnapshotAnchor | null) => void
}) {
  const query = useQuery(snapshotAnchorsOptions(leagueId))

  if (query.isLoading) {
    return <Skeleton className="h-9 w-56 rounded" />
  }

  if (query.isError) {
    return (
      <p className="text-xs text-muted-foreground">
        Snapshot anchors unavailable. Check that the backend is running, then refresh.
      </p>
    )
  }

  if (!query.data?.length) {
    return (
      <p className="text-xs text-muted-foreground">
        No snapshot anchors available. Snapshots are labeled automatically on trades and large
        roster changes.
      </p>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-muted-foreground">Compare from</span>
      <select
        value={selectedAnchorId?.toString() ?? ""}
        onChange={(event) => {
          const value = event.target.value
          const anchor = query.data.find((candidate) => candidate.snapshot_id === Number(value))
          onSelect(anchor ?? null)
        }}
        className="h-11 min-w-56 rounded-lg border border-border bg-card px-3 text-sm"
      >
        <option value="">Select a snapshot...</option>
        {query.data.map((anchor) => (
          <option key={anchor.snapshot_id} value={anchor.snapshot_id}>
            {anchor.label}
          </option>
        ))}
      </select>
    </div>
  )
}

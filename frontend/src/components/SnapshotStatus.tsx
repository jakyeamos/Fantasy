import { useMutation, useQueryClient } from "@tanstack/react-query"

import type { LeagueRefreshPipelineResponse } from "@/api/types"
import { Button } from "@/components/ui/button"

function formatSnapshot(snapshot: string | null) {
  if (!snapshot) return "No snapshot yet"
  const deltaMs = Date.now() - Date.parse(snapshot)
  const minutes = Math.floor(deltaMs / 60_000)
  if (minutes < 1) return "Last snapshot: just now"
  if (minutes < 60) return `Last snapshot: ${minutes} minutes ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Last snapshot: ${hours} hours ago`
  return `Last snapshot: ${new Date(snapshot).toLocaleDateString()}`
}

export function SnapshotStatus({
  leagueId,
  lastSnapshotAt,
}: {
  leagueId: string
  lastSnapshotAt: string | null
}) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: async (): Promise<LeagueRefreshPipelineResponse> => {
      const response = await fetch(`/api/ingest/${leagueId}/refresh-pipeline?run_type=incremental&draft_year=2026`, {
        method: "POST",
      })
      if (!response.ok) {
        throw new Error("Refresh failed")
      }
      return (await response.json()) as LeagueRefreshPipelineResponse
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["snapshots"] }),
        queryClient.invalidateQueries({ queryKey: ["snapshot-anchors", leagueId] }),
        queryClient.invalidateQueries({ queryKey: ["snapshot-diff", leagueId] }),
        queryClient.invalidateQueries({ queryKey: ["picks"] }),
        queryClient.invalidateQueries({ queryKey: ["rookie-board", leagueId] }),
        queryClient.invalidateQueries({ queryKey: ["draft-room", leagueId] }),
        queryClient.invalidateQueries({ queryKey: ["prospects", "model-outputs", leagueId] }),
        queryClient.invalidateQueries({ queryKey: ["context", "freshness", leagueId] }),
        queryClient.invalidateQueries({ queryKey: ["opportunities"] }),
        queryClient.invalidateQueries({ queryKey: ["portfolio"] }),
        queryClient.invalidateQueries({ queryKey: ["intelligence"] }),
        queryClient.invalidateQueries({ queryKey: ["startup-context", leagueId] }),
      ])
    },
  })

  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
      <span>{formatSnapshot(lastSnapshotAt)}</span>
      <Button
        size="sm"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
      >
        {mutation.isPending ? "Refreshing..." : "Refresh league data"}
      </Button>
      {mutation.isError ? (
        <span className="text-red-600 dark:text-red-400">
          Refresh failed. Full league refresh did not complete.
        </span>
      ) : null}
    </div>
  )
}

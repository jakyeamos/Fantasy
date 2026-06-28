import { useMutation, useQueryClient } from "@tanstack/react-query"

import type { LeagueRefreshPipelineResponse } from "@/api/types"
import { Button } from "@/components/ui/button"
import { textToneClasses } from "@/lib/ui-tokens"

type SnapshotStatusProps = {
  leagueId?: string
  lastSnapshotAt: string | null
}

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

function formatRefreshSummary(result: LeagueRefreshPipelineResponse) {
  return [
    `Sleeper ${result.sleeper_status}`,
    `ADP ${result.adp.matched_unique_rows}/${result.adp.source_rows} matched, ${result.adp.unmatched_rows} unmatched`,
    `Draft capital ${result.draft_capital.updated_rows} updated, ${result.draft_capital.rebuilt_boards} boards rebuilt`,
    `Artifacts ${result.artifacts.roster_count} rosters, ${result.artifacts.player_value_count} values, ${result.artifacts.manager_profile_count} profiles, ${result.artifacts.snapshot_count} snapshots`,
  ].join(" · ")
}

function formatRefreshError(error: Error) {
  return error.message || "Full league refresh did not complete."
}

export function SnapshotStatus({
  leagueId,
  lastSnapshotAt,
}: SnapshotStatusProps) {
  const queryClient = useQueryClient()
  const mutation = useMutation<LeagueRefreshPipelineResponse, Error>({
    mutationFn: async (): Promise<LeagueRefreshPipelineResponse> => {
      if (!leagueId) {
        throw new Error("Choose a league before refreshing league data.")
      }
      const response = await fetch(`/api/ingest/${leagueId}/refresh-pipeline?run_type=incremental&draft_year=2026`, {
        method: "POST",
      })
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: string | { detail?: string } }
          | null
        const detail =
          typeof payload?.detail === "string"
            ? payload.detail
            : payload?.detail?.detail
        throw new Error(detail ?? "Full league refresh did not complete.")
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
    <div className="space-y-2 text-xs text-muted-foreground">
      <div className="flex flex-wrap items-center gap-3">
        <span>{formatSnapshot(lastSnapshotAt)}</span>
        {leagueId ? (
          <Button
            size="sm"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Refreshing..." : "Refresh league data"}
          </Button>
        ) : null}
      </div>
      {mutation.isSuccess ? (
        <span className={`block max-w-3xl ${textToneClasses.success}`}>
          Refresh complete. {formatRefreshSummary(mutation.data)}
        </span>
      ) : null}
      {mutation.isError ? (
        <span className={`block max-w-3xl ${textToneClasses.destructive}`}>
          Refresh failed. {formatRefreshError(mutation.error)}
        </span>
      ) : null}
    </div>
  )
}

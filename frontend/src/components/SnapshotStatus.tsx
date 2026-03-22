import { useMutation, useQueryClient } from "@tanstack/react-query"

import type { SnapshotTriggerResponse } from "@/api/types"
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
  lastSnapshotAt,
}: {
  lastSnapshotAt: string | null
}) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/snapshots/trigger", {
        method: "POST",
      })
      if (!response.ok) {
        throw new Error("Snapshot failed")
      }
      return (await response.json()) as SnapshotTriggerResponse
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["snapshots"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
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
        {mutation.isPending ? "Saving..." : "Snapshot now"}
      </Button>
      {mutation.isError ? (
        <span className="text-red-600">Snapshot failed. Try again in a moment.</span>
      ) : null}
    </div>
  )
}

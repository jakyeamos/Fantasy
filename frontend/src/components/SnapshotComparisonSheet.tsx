import { useEffect, useState } from "react"

import type { SnapshotAnchor } from "@/api/types"
import { AnchorSelector } from "@/components/AnchorSelector"
import { SnapshotDiffView } from "@/components/SnapshotDiffView"
import { Button } from "@/components/ui/button"

export function SnapshotComparisonSheet({
  leagueId,
  rosterId,
  open,
  onOpenChange,
}: {
  leagueId: string
  rosterId: number
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [selectedAnchor, setSelectedAnchor] = useState<SnapshotAnchor | null>(null)

  useEffect(() => {
    if (!open) {
      setSelectedAnchor(null)
    }
  }, [open])

  useEffect(() => {
    if (!open) {
      return undefined
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false)
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onOpenChange, open])

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/40" onClick={() => onOpenChange(false)}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="snapshot-comparison-title"
        className="ml-auto flex h-full w-full max-w-lg flex-col overflow-y-auto border-l border-border/70 bg-background p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h2 id="snapshot-comparison-title" className="text-lg font-semibold">
              Compare to Snapshot
            </h2>
            <p className="text-sm text-muted-foreground">
              Select a snapshot anchor to see what changed.
            </p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>

        <div className="mt-4">
          <AnchorSelector
            leagueId={leagueId}
            selectedAnchorId={selectedAnchor?.snapshot_id ?? null}
            onSelect={setSelectedAnchor}
          />
          {selectedAnchor ? (
            <SnapshotDiffView
              leagueId={leagueId}
              snapshotId={selectedAnchor.snapshot_id}
              rosterId={rosterId}
              anchorLabel={selectedAnchor.label}
            />
          ) : null}
        </div>
      </div>
    </div>
  )
}

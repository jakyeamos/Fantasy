import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

interface DossierDraftPicksTabProps {
  pickPremiumScore: number | null
  pickTradeEvidence: number
  draftSelectionHistory: Array<{
    player_id: string
    pick_slot: number
    round_number: number
    season: number
    draft_type: "startup" | "rookie"
    position: string | null
    archetype_label: string | null
  }>
  archetypePattern: Record<string, number>
  isLoading?: boolean
}

export function DossierDraftPicksTab({
  pickPremiumScore,
  pickTradeEvidence,
  draftSelectionHistory,
  archetypePattern,
  isLoading = false,
}: DossierDraftPicksTabProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Draft & Picks</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          Startup and rookie draft behavior, plus pick-trade pricing patterns.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-3 mb-4 md:grid-cols-2">
          <div className="rounded-xl border border-border/40 bg-card/45 p-4">
            <p className="terminal-label mb-1">Pick Premium Score</p>
            {pickPremiumScore !== null ? (
              <p className="text-xl font-semibold">{pickPremiumScore.toFixed(2)}</p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Pick-premium score requires more pick-trade evidence to compute.
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Based on {pickTradeEvidence} pick-related trade
              {pickTradeEvidence !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-border/40">
          <div className="bg-card/45 grid grid-cols-5 px-4 py-2 text-xs font-semibold text-muted-foreground">
            <span>Season</span>
            <span>Round</span>
            <span>Pick #</span>
            <span>Position</span>
            <span>Archetype</span>
          </div>
          {draftSelectionHistory.length > 0 &&
          draftSelectionHistory.every((selection) => selection.draft_type === "startup") ? (
            <p className="text-xs text-muted-foreground px-4 py-2">
              Startup draft only - slot aggression analysis not applicable.
            </p>
          ) : null}
          {draftSelectionHistory.length === 0 ? (
            <p className="text-sm text-muted-foreground px-4 py-3">
              No draft history found for this manager.
            </p>
          ) : (
            draftSelectionHistory.map((selection) => (
              <div
                key={`${selection.player_id}-${selection.season}-${selection.pick_slot}`}
                className="grid grid-cols-5 border-t border-border/40 px-4 py-3 text-sm"
              >
                <span>{selection.season}</span>
                <span>R{selection.round_number}</span>
                <span>#{selection.pick_slot}</span>
                <span>{selection.position ?? "—"}</span>
                <span>{selection.archetype_label ?? "—"}</span>
              </div>
            ))
          )}
        </div>

        <div className="space-y-2">
          <p className="terminal-label">Archetype Patterns</p>
          {Object.keys(archetypePattern).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No archetype pattern established yet.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {Object.entries(archetypePattern).map(([label, count]) => (
                <Badge key={label}>
                  {label} · {count}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

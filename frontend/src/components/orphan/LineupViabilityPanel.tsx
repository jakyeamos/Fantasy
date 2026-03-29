import type { LineupResult } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type LineupViabilityPanelProps = {
  lineup: LineupResult | null
}

export function LineupViabilityPanel({ lineup }: LineupViabilityPanelProps) {
  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Lineup Viability</p>
        <CardTitle>Starter Pressure Points</CardTitle>
      </CardHeader>
      <CardContent>
        {lineup?.slot_scores.length ? (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {lineup.slot_scores.map((slot) => {
              const belowReplacement = slot.starter_value < slot.replacement_level
              return (
                <div
                  key={`${slot.position}-${slot.player_id}`}
                  className={cn(
                    "rounded-lg border border-border/50 bg-card/35 p-3",
                    belowReplacement ? "border-destructive/25 bg-destructive/10" : "",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{slot.position}</Badge>
                    <span className="text-sm font-semibold">{slot.player_name}</span>
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="font-mono text-sm">{slot.starter_value.toFixed(2)}</span>
                    <span className="text-xs text-muted-foreground">
                      vs repl {slot.replacement_level.toFixed(2)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">
            Lineup scores are unavailable. Re-run the lineup engine to see slot-by-slot weakness.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

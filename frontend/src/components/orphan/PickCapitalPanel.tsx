import type { OrphanIntake, PickValue } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type PickCapitalPanelProps = {
  intake: OrphanIntake
  picks: PickValue[]
}

export function PickCapitalPanel({ intake, picks }: PickCapitalPanelProps) {
  const picksByYear = picks.reduce<Record<number, PickValue[]>>(
    (groups, pick) => {
      const year = pick.pick.pick_year
      groups[year] = [...(groups[year] ?? []), pick]
      return groups
    },
    {},
  )

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Pick Capital</p>
        <CardTitle>{intake.pick_capital.label}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm font-semibold">{intake.pick_capital.summary}</p>
        {Object.keys(picksByYear).length ? (
          Object.entries(picksByYear)
            .sort(([left], [right]) => Number(left) - Number(right))
            .map(([year, yearPicks]) => (
              <div key={year} className="space-y-2">
                <p className="terminal-label text-muted-foreground">{year}</p>
                <div className="space-y-2">
                  {yearPicks.map((pick, index) => (
                    <div
                      key={`${pick.pick.pick_year}-${pick.pick.pick_round}-${pick.pick.pick_owner_roster_id}-${index}`}
                      className="flex items-center justify-between rounded-lg border border-border/50 bg-card/35 px-4 py-3"
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">
                          Round {pick.pick.pick_round}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {pick.pick.projected_slot ?? "Current slot"}
                        </span>
                      </div>
                      <span className="font-mono text-sm">
                        {pick.demand_adjusted_value.toFixed(1)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">
            No future picks are cached for this roster yet.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

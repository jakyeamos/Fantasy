import type { StartupPickValuation } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type StartupPickValuationListProps = {
  picks: StartupPickValuation[]
}

export function StartupPickValuationList({ picks }: StartupPickValuationListProps) {
  if (!picks.length) {
    return (
      <Card className="border-dashed border-border/45">
        <CardHeader>
          <p className="terminal-label text-muted-foreground">Pick Valuation</p>
          <CardTitle>Startup Data Unavailable</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            Startup context exists, but there are no pick valuations cached for this league yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Pick Valuation</p>
        <CardTitle>Board Leverage</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border/40">
          {picks.map((pick) => (
            <div key={`${pick.pick_slot}-${pick.pick_slot_number}`} className="space-y-2 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm">{pick.pick_slot}</span>
                <span className="text-sm font-semibold">
                  {pick.projected_player_name ?? "Projection pending"}
                </span>
                <Badge variant="outline">{pick.tier_label}</Badge>
                {pick.trade_up_recommended ? <Badge>Trade Up</Badge> : null}
                {pick.trade_down_recommended ? <Badge variant="outline">Trade Down</Badge> : null}
              </div>
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                <span className="font-mono">Value {pick.pick_value.toFixed(1)}</span>
                {pick.trade_reasoning ? <span>{pick.trade_reasoning}</span> : null}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

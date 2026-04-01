import { useQuery } from "@tanstack/react-query"

import { lineupScoreOptions } from "@/api/queries"
import { RecommendationCardList } from "@/components/recommendations/RecommendationCardList"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

type LineupStrengthCardProps = {
  leagueId: string
  rosterId: number
}

export function LineupStrengthCard({ leagueId, rosterId }: LineupStrengthCardProps) {
  const { data, isLoading, isError } = useQuery(lineupScoreOptions(leagueId, rosterId))

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full min-h-[40px]" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Starter scores unavailable.</p>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.slot_scores.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Lineup strength</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No lineup data yet. Run a roster ingest to see position-by-position starter strength.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lineup strength</CardTitle>
        <p className="text-sm text-muted-foreground">
          Starter score vs. league median, with contender-path pressure layered in when enough
          contender data exists.
        </p>
      </CardHeader>
      <CardContent>
        {data.upgrade_leverage_point ? (
          <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
            <p className="text-sm font-medium text-amber-700">
              Best upgrade leverage: {data.upgrade_leverage_point}
            </p>
            <p className="text-xs text-muted-foreground">
              Est. title equity improvement: +
              {(data.upgrade_title_equity_delta * 100).toFixed(1)}%
            </p>
          </div>
        ) : null}
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {data.slot_scores.map((row) => (
            <div
              key={`${row.position}-${row.player_id}`}
              className="flex min-h-[40px] flex-col gap-1 rounded-lg border border-border/50 bg-card/40 p-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{row.position}</Badge>
                {row.elite_insulation_guard ? (
                  <Badge className="border-emerald-500/25 bg-emerald-500/10 text-emerald-700">
                    Elite insulation
                  </Badge>
                ) : null}
                <span className="text-sm font-medium">{row.player_name}</span>
              </div>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-mono text-sm">{row.starter_value.toFixed(2)}</span>
                <span className="text-xs text-muted-foreground">
                  vs repl {row.replacement_level.toFixed(2)}
                </span>
                <span className="text-xs text-muted-foreground">
                  {data.contender_benchmark_used
                    ? `contender ${row.contender_benchmark.toFixed(2)}`
                    : "contender baseline unavailable"}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {row.weak_by_median ? <Badge variant="secondary">Weak by median</Badge> : null}
                {row.weak_relative_to_contender ? (
                  <Badge className="border-amber-500/25 bg-amber-500/10 text-amber-700">
                    Contender-path weak spot
                  </Badge>
                ) : null}
                {row.upgrade_leverage_score > 0 ? (
                  <Badge className="border-sky-500/25 bg-sky-500/10 text-sky-700">
                    Leverage {row.upgrade_leverage_score.toFixed(2)}
                  </Badge>
                ) : null}
                {row.position === "TE" && row.format_urgency_weight < 1 ? (
                  <Badge variant="outline">
                    TE urgency x{row.format_urgency_weight.toFixed(1)}
                  </Badge>
                ) : null}
              </div>
              {row.player_context_flags.length > 0 ? (
                <div className="flex flex-wrap gap-2 pt-1">
                  {row.player_context_flags.map((flag) => (
                    <Badge key={flag} variant="outline" className="text-[11px]">
                      {flag.replaceAll("_", " ")}
                    </Badge>
                  ))}
                </div>
              ) : null}
              {row.elite_insulation_guard ? (
                <p className="text-xs text-muted-foreground">
                  Below-contender pressure is muted here because this roster has elite insulation.
                </p>
              ) : null}
              {!row.elite_insulation_guard && row.upgrade_leverage_score > 0 ? (
                <p className="text-xs text-muted-foreground">
                  Closing this slot to the contender benchmark is the cleanest path to more weekly
                  lineup edge.
                </p>
              ) : null}
              {row.player_context_flags.length === 0 &&
              !row.elite_insulation_guard &&
              row.upgrade_leverage_score === 0 ? (
                <p className="text-xs text-muted-foreground">
                  This slot is holding baseline or better without an active context warning.
                </p>
              ) : null}
              {row.player_context_flags.length > 0 ? (
                <p className="text-xs text-muted-foreground">
                  Context notes: {row.player_context_flags.map((flag) => flag.replaceAll("_", " ")).join(", ")}.
                </p>
              ) : null}
            </div>
          ))}
        </div>
        {data.recommendation_cards && data.recommendation_cards.length > 0 ? (
          <div className="mt-6 space-y-3">
            <p className="terminal-label text-muted-foreground">Upgrade Recommendations</p>
            <RecommendationCardList cards={data.recommendation_cards} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

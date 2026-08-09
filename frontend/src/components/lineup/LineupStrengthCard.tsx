import { useQuery } from "@tanstack/react-query"

import { lineupScoreOptions } from "@/api/queries"
import type { LineupResult, LineupSlotScore } from "@/api/types"
import { RecommendationCardList } from "@/components/recommendations/RecommendationCardList"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  badgeToneClasses,
  surfaceToneClasses,
  textToneClasses,
} from "@/lib/ui-tokens"

type LineupStrengthCardProps = {
  leagueId: string
  rosterId: number
}

function benchmarkSourceLabel(source: string) {
  switch (source) {
    case "league_median_fallback":
      return "League median fallback"
    case "top_tier_fallback":
      return "Top-tier fallback"
    case "single_roster_fallback":
      return "Thin sample fallback"
    case "replacement_level":
      return "Replacement baseline"
    default:
      return null
  }
}

function roundedGap(value: number) {
  return Number(value.toFixed(2))
}

function hasVisibleGap(value: number) {
  return roundedGap(value) > 0
}

function joinClauses(parts: string[]) {
  if (parts.length === 0) {
    return ""
  }
  if (parts.length === 1) {
    return parts[0]
  }
  if (parts.length === 2) {
    return `${parts[0]} and ${parts[1]}`
  }
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`
}

function tierStatus(row: LineupSlotScore) {
  if (!row.benchmark_used) {
    return null
  }
  if (row.starter_value >= row.elite_target) {
    return {
      label: "Elite tier",
      className: badgeToneClasses.success,
    }
  }
  if (row.starter_value >= row.title_target) {
    return {
      label: "Title tier",
      className: badgeToneClasses.info,
    }
  }
  if (row.starter_value >= row.playoff_target) {
    return {
      label: "Playoff tier",
      className: badgeToneClasses.strategy,
    }
  }
  return null
}

function overallGapSummary(data: LineupResult) {
  const playoffGap = roundedGap(data.overall_gap_to_playoff_target)
  const titleGap = roundedGap(data.overall_gap_to_title_target)
  const eliteGap = roundedGap(data.overall_gap_to_elite_target)

  if (data.total_lineup_score < data.overall_playoff_target) {
    const parts = [
      playoffGap > 0 ? `the playoff bar by ${playoffGap.toFixed(2)}` : null,
      titleGap > 0 ? `the title bar by ${titleGap.toFixed(2)}` : null,
    ].filter((part): part is string => part !== null)
    return parts.length > 0
      ? `Overall lineup trails ${joinClauses(parts)}.`
      : "Overall lineup is sitting right on the contender cut lines."
  }

  if (data.total_lineup_score < data.overall_title_target) {
    return titleGap > 0
      ? `Overall lineup clears the playoff bar but still trails the title bar by ${titleGap.toFixed(2)}.`
      : "Overall lineup is sitting right on the title cut line."
  }

  if (data.total_lineup_score < data.overall_elite_target) {
    return eliteGap > 0
      ? `Overall lineup is in the title range and ${eliteGap.toFixed(2)} away from the elite end of the league.`
      : "Overall lineup is sitting right on the elite cut line."
  }

  return "Overall lineup is already tracking with the elite end of this league."
}

function slotGapSummary(row: LineupSlotScore) {
  const playoffGap = roundedGap(row.gap_to_playoff_target)
  const titleGap = roundedGap(row.gap_to_title_target)
  const eliteGap = roundedGap(row.gap_to_elite_target)

  if (row.below_playoff_target) {
    const parts = [
      playoffGap > 0
        ? `${playoffGap.toFixed(2)} to reach the playoff line`
        : null,
      titleGap > 0 ? `${titleGap.toFixed(2)} to hit the title line` : null,
      eliteGap > 0 ? `${eliteGap.toFixed(2)} to reach the elite line` : null,
    ].filter((part): part is string => part !== null)
    return parts.length > 0 ? `Needs ${joinClauses(parts)}.` : null
  }

  const trailing = [
    titleGap > 0 ? `the title line by ${titleGap.toFixed(2)}` : null,
    eliteGap > 0 ? `the elite line by ${eliteGap.toFixed(2)}` : null,
  ].filter((part): part is string => part !== null)

  if (trailing.length === 0) {
    return null
  }

  return titleGap > 0
    ? `Clears the playoff line but still trails ${joinClauses(trailing)}.`
    : `Clears the playoff and title lines but still trails ${joinClauses(trailing)}.`
}

export function LineupStrengthCard({
  leagueId,
  rosterId,
}: LineupStrengthCardProps) {
  const { data, isLoading, isError } = useQuery(
    lineupScoreOptions(leagueId, rosterId),
  )
  const hasEliteInsulation =
    data?.slot_scores.some((row) => row.elite_insulation_guard) ?? false

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
          <p className="text-sm text-muted-foreground">
            Starter scores unavailable.
          </p>
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
            No lineup data yet. Run a roster ingest to see position-by-position
            starter strength.
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
          Slot strength and overall lineup score vs. playoff, title, and elite
          roster bars for this league.
        </p>
      </CardHeader>
      <CardContent>
        <div className="mb-4 rounded-lg border border-border/50 bg-muted/25 px-3 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">
              Overall lineup score {data.total_lineup_score.toFixed(2)}
            </span>
            <Badge variant="outline">
              playoff {data.overall_playoff_target.toFixed(2)}
            </Badge>
            <Badge variant="outline">
              title {data.overall_title_target.toFixed(2)}
            </Badge>
            <Badge variant="outline">
              elite {data.overall_elite_target.toFixed(2)}
            </Badge>
            {data.overall_gap_to_title_target > 0 ? (
              <Badge className={badgeToneClasses.info}>
                Title gap {data.overall_gap_to_title_target.toFixed(2)}
              </Badge>
            ) : null}
            {benchmarkSourceLabel(data.overall_benchmark_source) ? (
              <Badge variant="outline" className="text-label-sm">
                {benchmarkSourceLabel(data.overall_benchmark_source)}
              </Badge>
            ) : null}
            {hasEliteInsulation ? (
              <Badge className={badgeToneClasses.success}>
                Elite insulation
              </Badge>
            ) : null}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {overallGapSummary(data)}
          </p>
          {hasEliteInsulation ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Elite insulation is roster-level context, not a player trait. It
              can lower urgency on marginal upgrades, but it should not hide the
              actual slot gaps.
            </p>
          ) : null}
        </div>
        {data.upgrade_leverage_point ? (
          <div
            className={`mb-4 rounded-lg border px-3 py-2 ${surfaceToneClasses.warning}`}
          >
            <p className={`text-sm font-medium ${textToneClasses.warning}`}>
              Best upgrade leverage: {data.upgrade_leverage_point}
            </p>
            <p className="text-xs text-muted-foreground">
              Est. title equity improvement: +
              {(data.upgrade_title_equity_delta * 100).toFixed(1)}%
            </p>
          </div>
        ) : null}
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {data.slot_scores.map((row) => {
            const status = tierStatus(row)
            const slotSummary = slotGapSummary(row)

            return (
              <div
                key={`${row.position}-${row.player_id}`}
                className="flex min-h-[40px] flex-col gap-1 rounded-lg border border-border/50 bg-card/40 p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">{row.position}</Badge>
                  <span className="text-sm font-medium">{row.player_name}</span>
                </div>
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-sm">
                    {row.starter_value.toFixed(2)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    vs repl {row.replacement_level.toFixed(2)}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  {data.contender_benchmark_used ? (
                    <>
                      <span>playoff {row.playoff_target.toFixed(2)}</span>
                      <span>title {row.title_target.toFixed(2)}</span>
                      <span>elite {row.elite_target.toFixed(2)}</span>
                    </>
                  ) : (
                    <span>tier targets unavailable</span>
                  )}
                  {data.contender_benchmark_used &&
                  benchmarkSourceLabel(row.benchmark_source) ? (
                    <Badge variant="outline" className="text-label-sm">
                      {benchmarkSourceLabel(row.benchmark_source)}
                    </Badge>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {status ? (
                    <Badge className={status.className}>{status.label}</Badge>
                  ) : null}
                  {row.weak_by_median ? (
                    <Badge variant="secondary">Weak by median</Badge>
                  ) : null}
                  {row.below_playoff_target ? (
                    <Badge variant="secondary">Below playoff target</Badge>
                  ) : null}
                  {row.below_title_target ? (
                    <Badge className={badgeToneClasses.warning}>
                      Below title target
                    </Badge>
                  ) : null}
                  {row.below_elite_target ? (
                    <Badge variant="outline">Below elite target</Badge>
                  ) : null}
                  {hasVisibleGap(row.gap_to_title_target) ? (
                    <Badge className={badgeToneClasses.info}>
                      Title gap {row.gap_to_title_target.toFixed(2)}
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
                      <Badge
                        key={flag}
                        variant="outline"
                        className="text-label-sm"
                      >
                        {flag.replaceAll("_", " ")}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                {data.contender_benchmark_used && slotSummary ? (
                  <p className="text-xs text-muted-foreground">{slotSummary}</p>
                ) : null}
                {row.player_context_flags.length === 0 &&
                !hasVisibleGap(row.gap_to_title_target) &&
                !hasVisibleGap(row.gap_to_elite_target) ? (
                  <p className="text-xs text-muted-foreground">
                    This slot is holding baseline or better without an active
                    context warning.
                  </p>
                ) : null}
                {row.player_context_flags.length > 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Context notes:{" "}
                    {row.player_context_flags
                      .map((flag) => flag.replaceAll("_", " "))
                      .join(", ")}
                    .
                  </p>
                ) : null}
              </div>
            )
          })}
        </div>
        {data.recommendation_cards && data.recommendation_cards.length > 0 ? (
          <div className="mt-6 space-y-3">
            <p className="terminal-label text-muted-foreground">
              Upgrade Recommendations
            </p>
            <RecommendationCardList cards={data.recommendation_cards} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

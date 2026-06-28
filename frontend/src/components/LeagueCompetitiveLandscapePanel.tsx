import type {
  CalendarState,
  LeagueCompetitiveLandscape,
  LineupResult,
  MatchupPrediction,
  PowerRankingEntry,
} from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { badgeToneClasses, surfaceToneClasses } from "@/lib/ui-tokens"
import { cn, formatModelLabel } from "@/lib/utils"

type LeagueCompetitiveLandscapePanelProps = {
  landscape: LeagueCompetitiveLandscape | null | undefined
  lineup: LineupResult | null
  calendarState?: CalendarState | null
}

type LineupPlanItem = {
  title: string
  detail: string
  tone: "urgent" | "setup" | "anchor"
}

function scoreOutOf100(score: number) {
  return Math.round(score * 100)
}

function signedScoreDelta(score: number) {
  const rounded = Math.round(score * 100)
  return `${rounded > 0 ? "+" : ""}${rounded}`
}

function compactRankings(entries: PowerRankingEntry[]) {
  if (entries.length <= 6) return entries
  const top = entries.slice(0, 6)
  const userEntry = entries.find((entry) => entry.is_user && entry.rank > 6)
  return userEntry ? [...top, userEntry] : top
}

function verdictBadge(prediction: MatchupPrediction) {
  if (prediction.verdict === "favored") {
    return badgeToneClasses.success
  }
  if (prediction.verdict === "underdog") {
    return badgeToneClasses.warning
  }
  return "border-border/60 bg-transparent text-muted-foreground"
}

function rankingContext(entry: PowerRankingEntry) {
  if (entry.record) return `Record ${entry.record}`
  if (entry.direction_label) return formatModelLabel(entry.direction_label)
  if (entry.title_window_label) return entry.title_window_label
  return "League context unavailable"
}

function buildLineupPlan(lineup: LineupResult | null): LineupPlanItem[] {
  if (!lineup || lineup.slot_scores.length === 0) {
    return []
  }

  const urgentSlot = [...lineup.slot_scores]
    .sort(
      (left, right) =>
        right.gap_to_title_target - left.gap_to_title_target ||
        right.upgrade_leverage_score - left.upgrade_leverage_score,
    )[0]

  const leverageSlot = [...lineup.slot_scores]
    .sort(
      (left, right) =>
        right.upgrade_leverage_score * right.format_urgency_weight -
          left.upgrade_leverage_score * left.format_urgency_weight ||
        right.upgrade_leverage_score - left.upgrade_leverage_score,
    )
    .find((slot) => slot.player_id !== urgentSlot?.player_id)

  const anchorSlot = [...lineup.slot_scores]
    .sort(
      (left, right) =>
        (right.score - right.title_target) - (left.score - left.title_target) ||
        right.score - left.score,
    )
    .find(
      (slot) =>
        slot.player_id !== urgentSlot?.player_id && slot.player_id !== leverageSlot?.player_id,
    )

  const plan: LineupPlanItem[] = []

  if (urgentSlot) {
    plan.push({
      title: `Press hardest on ${urgentSlot.position}`,
      detail:
        urgentSlot.gap_to_title_target > 0
          ? `${urgentSlot.player_name} sits ${urgentSlot.gap_to_title_target.toFixed(2)} behind the league title target for this slot.`
          : `${urgentSlot.player_name} is still one of the cleanest weekly pressure points to upgrade.`,
      tone: "urgent",
    })
  }

  if (leverageSlot) {
    plan.push({
      title: `Use ${leverageSlot.position} as the swing slot`,
      detail: `${leverageSlot.player_name} carries the best estimated title-equity leverage if you improve this spot.`,
      tone: "setup",
    })
  }

  if (anchorSlot) {
    const anchorContext =
      anchorSlot.score >= anchorSlot.title_target
        ? `${anchorSlot.player_name} is already holding title-level ground at ${anchorSlot.position}.`
        : `${anchorSlot.player_name} is one of the few spots not driving your weekly downside.`
    plan.push({
      title: `Protect ${anchorSlot.player_name}`,
      detail: `${anchorContext} Avoid moving it unless the return upgrades one of the red-zone slots.`,
      tone: "anchor",
    })
  }

  return plan.slice(0, 3)
}

function RankingBoard({
  title,
  subtitle,
  entries,
}: {
  title: string
  subtitle: string
  entries: PowerRankingEntry[]
}) {
  if (entries.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {compactRankings(entries).map((entry) => (
          <div
            key={entry.roster_id}
            className={cn(
              "grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-lg border border-border/50 bg-card/35 p-3",
              entry.is_user && "border-primary/25 bg-primary/7",
            )}
          >
            <div className="font-mono text-xs text-muted-foreground">#{entry.rank}</div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="truncate text-sm font-semibold">{entry.manager_name}</p>
                {entry.is_user ? <Badge>You</Badge> : null}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{rankingContext(entry)}</p>
            </div>
            <div className="text-right">
              <p className="font-mono text-sm font-semibold">{scoreOutOf100(entry.score)}</p>
              <p className="text-label-xs uppercase tracking-label-tight text-muted-foreground">
                score
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function LeagueCompetitiveLandscapePanel({
  landscape,
  lineup,
  calendarState,
}: LeagueCompetitiveLandscapePanelProps) {
  if (!landscape) return null

  const lineupPlan = buildLineupPlan(lineup)
  const showMatchupOutlook =
    calendarState === "preseason" ||
    calendarState === "early_season" ||
    calendarState === "trade_deadline" ||
    calendarState === "playoffs"
  const matchupPredictions = landscape.matchup_predictions
  const favoredCount = matchupPredictions.filter(
    (prediction) => prediction.verdict === "favored",
  ).length
  const tossUpCount = matchupPredictions.filter(
    (prediction) => prediction.verdict === "toss_up",
  ).length
  const underdogCount = matchupPredictions.filter(
    (prediction) => prediction.verdict === "underdog",
  ).length

  return (
    <section className="space-y-4">
      {landscape.metric_summaries.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-3">
          {landscape.metric_summaries.map((metric) => (
            <Card key={metric.key}>
              <CardHeader className="pb-3">
                <p className="terminal-label text-muted-foreground">{metric.label}</p>
                <div className="mt-3 flex items-end justify-between gap-4">
                  <div>
                    <p className="font-headline text-3xl font-extrabold tracking-tight">
                      #{metric.rank}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      of {metric.league_size} teams
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-2xl font-semibold">
                      {scoreOutOf100(metric.score)}
                    </p>
                    <p className="text-label-xs uppercase tracking-label-tight text-muted-foreground">
                      score
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                <p>
                  {signedScoreDelta(metric.edge_vs_median)} vs median
                  {metric.gap_to_leader > 0
                    ? ` | ${scoreOutOf100(metric.gap_to_leader)} off the lead`
                    : " | league lead"}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-3">
        <RankingBoard
          title="Win-Now Power"
          subtitle="Who is carrying the strongest weekly scoring base right now."
          entries={landscape.win_now_rankings}
        />
        <RankingBoard
          title="Future Value Power"
          subtitle="Who has the best insulated long-term value and flexibility."
          entries={landscape.future_value_rankings}
        />
        <RankingBoard
          title="Title Window Power"
          subtitle="Who currently projects with the strongest path to survive weekly pressure."
          entries={landscape.title_window_rankings}
        />
      </div>

      <div
        className={cn(
          "grid gap-4",
          showMatchupOutlook && matchupPredictions.length > 0
            ? "lg:grid-cols-[1.3fr_1fr]"
            : "lg:grid-cols-1",
        )}
      >
        {showMatchupOutlook && matchupPredictions.length > 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>Head-to-Head Outlook</CardTitle>
              <p className="mt-2 text-sm text-muted-foreground">
                Model-based matchup reads from title-window strength, ceiling, stability, and
                depth. These are opponent comparisons, not schedule assumptions.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-border/50 bg-card/35 p-3">
                  <p className="terminal-label text-muted-foreground">Favored</p>
                  <p className="mt-2 font-headline text-2xl font-extrabold">{favoredCount}</p>
                </div>
                <div className="rounded-lg border border-border/50 bg-card/35 p-3">
                  <p className="terminal-label text-muted-foreground">Toss-ups</p>
                  <p className="mt-2 font-headline text-2xl font-extrabold">{tossUpCount}</p>
                </div>
                <div className="rounded-lg border border-border/50 bg-card/35 p-3">
                  <p className="terminal-label text-muted-foreground">Underdog</p>
                  <p className="mt-2 font-headline text-2xl font-extrabold">{underdogCount}</p>
                </div>
              </div>

              <div className="space-y-3">
                {matchupPredictions.map((prediction) => (
                  <div
                    key={prediction.roster_id}
                    className="grid gap-3 rounded-lg border border-border/50 bg-card/35 p-3 md:grid-cols-[1fr_auto]"
                  >
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold">{prediction.manager_name}</p>
                        <Badge className={verdictBadge(prediction)} variant="outline">
                          {prediction.verdict.replaceAll("_", " ")}
                        </Badge>
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">{prediction.reason}</p>
                    </div>
                    <div className="text-left md:text-right">
                      <p className="font-mono text-xl font-semibold">
                        {Math.round(prediction.win_probability * 100)}%
                      </p>
                      <p className="text-label-xs uppercase tracking-label-tight text-muted-foreground">
                        win odds
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}

        {lineupPlan.length > 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>Lineup Plan</CardTitle>
              <p className="mt-2 text-sm text-muted-foreground">
                Comparative slot guidance built from your current gaps versus the league title
                targets.
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {lineupPlan.map((item) => (
                <div
                  key={item.title}
                  className={cn(
                    "rounded-lg border p-3",
                    item.tone === "urgent" && surfaceToneClasses.warning,
                    item.tone === "setup" && surfaceToneClasses.info,
                    item.tone === "anchor" && surfaceToneClasses.success,
                  )}
                >
                  <p className="text-sm font-semibold">{item.title}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{item.detail}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </section>
  )
}

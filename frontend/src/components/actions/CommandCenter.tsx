import { useEffect, useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, ArrowRight, ChevronDown, RefreshCcw } from "lucide-react"

import {
  dashboardSummaryOptions,
  leagueActionsOptions,
  postJson,
  recomputeActions,
} from "@/api/queries"
import type { CommandAction, DataRefreshAction, FreshnessTag } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { surfaceToneClasses, textToneClasses } from "@/lib/ui-tokens"

const categoryLabel: Record<CommandAction["category"], string> = {
  waiver: "Waiver",
  lineup: "Lineup",
  trade: "Trade",
  market: "Market",
  rookie_pick: "Rookie",
  portfolio: "Portfolio",
  manager: "Manager",
}

function urgencyCopy(urgency: CommandAction["urgency"]): string {
  if (urgency === "today") return "Today"
  if (urgency === "this_week") return "This week"
  if (urgency === "watch") return "Watch"
  return "Low"
}

function confidenceVariant(confidence: CommandAction["confidence"]) {
  if (confidence === "HIGH") return "default"
  if (confidence === "MEDIUM") return "secondary"
  return "outline"
}

function formatFreshnessLabel(tag: FreshnessTag): string {
  return tag.domain.replaceAll("_", " ")
}

function CommandSummary({
  dataHealth,
}: {
  dataHealth: FreshnessTag[]
}) {
  const staleDomains = dataHealth.filter((tag) => tag.is_stale)

  if (!staleDomains.length) return null

  return (
    <div className="flex flex-wrap items-center gap-2 rounded border border-border/45 bg-card/35 px-3 py-2 text-xs">
      <div className="flex items-center gap-2 pr-2 font-semibold text-foreground">
        <AlertTriangle className={`size-4 ${textToneClasses.attention}`} />
        {staleDomains.length} stale data lane{staleDomains.length === 1 ? "" : "s"}
      </div>
      {staleDomains.slice(0, 3).map((tag) => (
        <Badge key={tag.domain} variant="outline">
          {formatFreshnessLabel(tag)} stale
        </Badge>
      ))}
    </div>
  )
}

function RefreshAllButton({
  actions,
  onComplete,
}: {
  actions: DataRefreshAction[]
  onComplete: () => Promise<unknown>
}) {
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const hasRefreshActions = actions.length > 0

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        className={buttonClasses({ variant: "outline" })}
        disabled={isRunning}
        title={
          hasRefreshActions
            ? actions.map((action) => action.label).join(", ")
            : "Recompute command-center actions."
        }
        onClick={() => {
          setIsRunning(true)
          setError(null)
          const run = hasRefreshActions
            ? actions.reduce(
                (chain, action) =>
                  chain.then(() => postJson<unknown>(action.endpoint, {})),
                Promise.resolve<unknown>(undefined),
              )
            : recomputeActions()
          void run
            .then(onComplete)
            .catch(() => setError("Refresh failed. Check the local server logs."))
            .finally(() => setIsRunning(false))
        }}
      >
        <RefreshCcw className={`size-3.5 ${isRunning ? "animate-spin" : ""}`} />
        {isRunning
          ? "Refreshing..."
          : hasRefreshActions
            ? "Refresh stale data"
            : "Recompute moves"}
      </button>
      {hasRefreshActions ? (
        <span className="text-xs text-muted-foreground">
          {actions.length} queued refreshes
        </span>
      ) : null}
      {error ? <span className="text-xs text-destructive">{error}</span> : null}
    </div>
  )
}

function CommandCard({ action }: { action: CommandAction }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <Card style={{ boxShadow: "0 8px 18px -18px hsl(var(--foreground) / 0.55)" }}>
      <CardHeader className="space-y-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">#{action.priority_rank}</Badge>
              <Badge variant="secondary">{categoryLabel[action.category]}</Badge>
              <Badge variant={confidenceVariant(action.confidence)}>{action.confidence}</Badge>
              <span className="terminal-label text-muted-foreground">
                {urgencyCopy(action.urgency)}
              </span>
            </div>
            <CardTitle className="text-lg leading-6">{action.headline}</CardTitle>
          </div>
          <button
            type="button"
            aria-expanded={isExpanded}
            className={buttonClasses({ variant: "ghost", size: "sm" })}
            onClick={() => setIsExpanded((current) => !current)}
          >
            Details
            <ChevronDown
              className={`size-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`}
            />
          </button>
        </div>
        <p className="text-sm font-semibold leading-6">{action.recommended_action}</p>
      </CardHeader>
      {isExpanded ? (
        <CardContent className="flex flex-col gap-4 px-4 pb-4 pt-0">
          <div className="space-y-3">
            <div className="space-y-2 text-sm leading-6 text-muted-foreground">
              <p>
                <span className="font-semibold text-foreground">Acceptable price:</span>{" "}
                {action.acceptable_price}
              </p>
              <p>
                <span className="font-semibold text-foreground">Timing:</span>{" "}
                {action.timing}
              </p>
              <p>
                <span className="font-semibold text-foreground">Why now:</span>{" "}
                {action.why_now}
              </p>
              <p>
                <span className="font-semibold text-foreground">Wrong if:</span>{" "}
                {action.risk_if_wrong}
              </p>
            </div>
            {action.evidence.length ? (
              <div className="flex flex-wrap gap-2">
                {action.evidence.slice(0, 3).map((item) => (
                  <Badge key={item} variant="outline">
                    {item}
                  </Badge>
                ))}
              </div>
            ) : null}
            {action.stale_domains.length ? (
              <div className={`flex items-center gap-2 rounded border px-3 py-2 text-xs ${surfaceToneClasses.attention} ${textToneClasses.attention}`}>
                <AlertTriangle className="size-3.5 shrink-0" />
                Refresh {action.stale_domains.join(", ")} before locking this in.
              </div>
            ) : null}
            {action.trade_suggestion ? (
              <div className="space-y-2 rounded border border-border/45 bg-background/35 p-3 text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">Suggested package</p>
                <p>
                  <span className="font-semibold text-foreground">Send:</span>{" "}
                  {action.trade_suggestion.send_assets.join(" + ")}
                </p>
                <p>
                  <span className="font-semibold text-foreground">Receive:</span>{" "}
                  {action.trade_suggestion.receive_assets.join(" + ")}
                </p>
                <p>
                  <span className="font-semibold text-foreground">Pitch:</span>{" "}
                  {action.trade_suggestion.manager_pitch_angle}
                </p>
                {action.trade_suggestion.evaluation_summary ? (
                  <p>
                    <span className="font-semibold text-foreground">Pre-score:</span>{" "}
                    {action.trade_suggestion.evaluation_verdict.toUpperCase()}{" "}
                    {action.trade_suggestion.evaluation_score?.toFixed(1) ?? "--"} -{" "}
                    {action.trade_suggestion.evaluation_summary}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
          <a href={action.cta_destination} className={buttonClasses({ variant: "outline" })}>
            {action.cta_label}
            <ArrowRight className="size-3.5" />
          </a>
        </CardContent>
      ) : null}
    </Card>
  )
}

export function CommandCenter() {
  const leaguesQuery = useQuery(dashboardSummaryOptions)
  const leagues = leaguesQuery.data ?? []
  const [selectedLeagueId, setSelectedLeagueId] = useState("")
  const [includeStartSit, setIncludeStartSit] = useState(false)
  const activeLeagueId = selectedLeagueId || leagues[0]?.league_id || ""
  const selectedLeague = leagues.find((league) => league.league_id === activeLeagueId)
  const query = useQuery(leagueActionsOptions(activeLeagueId))

  useEffect(() => {
    if (!leagues.length) return
    if (selectedLeagueId && leagues.some((league) => league.league_id === selectedLeagueId)) {
      return
    }
    setSelectedLeagueId(leagues[0].league_id)
  }, [leagues, selectedLeagueId])

  if (leaguesQuery.isLoading || (activeLeagueId && query.isLoading)) {
    return (
      <section className="space-y-4">
        <div className="space-y-2">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-9 w-80" />
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index}>
              <CardContent className="space-y-4 p-5">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-10 w-36" />
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    )
  }

  if (!activeLeagueId) {
    return null
  }

  const actions = (query.data?.actions ?? [])
    .filter((action) => includeStartSit || action.category !== "lineup")
    .slice(0, 5)
  const dataHealth = query.data?.data_health ?? []
  const refreshActions = query.data?.refresh_actions ?? []

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-3xl space-y-2">
          <p className="terminal-label text-primary/85">Command Center</p>
          <h2 className="font-headline text-3xl font-extrabold tracking-tight">
            Top moves today
          </h2>
          <p className="text-sm leading-6 text-muted-foreground">
            The highest-priority action queue for {selectedLeague?.league_name ?? "this league"}.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-3">
          <label className="flex h-11 items-center gap-2 rounded-lg border border-border/60 bg-card/55 px-3">
            <input
              type="checkbox"
              checked={includeStartSit}
              className="size-4 accent-primary"
              onChange={(event) => setIncludeStartSit(event.target.checked)}
            />
            <span className="terminal-label text-muted-foreground">Include start/sit</span>
          </label>
          <label className="flex flex-col gap-1">
            <span className="terminal-label text-muted-foreground">League</span>
            <select
              value={activeLeagueId}
              className="h-11 min-w-48 rounded-lg border border-border/60 bg-card/75 px-3 font-label text-xs font-bold uppercase tracking-label-tight text-foreground"
              onChange={(event) => setSelectedLeagueId(event.target.value)}
            >
              {leagues.map((league) => (
                <option key={league.league_id} value={league.league_id}>
                  {league.league_name}
                </option>
              ))}
            </select>
          </label>
          <RefreshAllButton
            actions={refreshActions}
            onComplete={() => query.refetch()}
          />
        </div>
      </div>
      <CommandSummary dataHealth={dataHealth} />

      {leaguesQuery.isError || query.isError ? (
        <Card>
          <CardContent className="space-y-2 p-6">
            <p className="font-headline text-2xl font-bold tracking-tight">
              Command Center Unavailable
            </p>
            <p className="text-sm text-muted-foreground">
              The backend could not rank actions. Use league pages while checking
              the local server logs.
            </p>
          </CardContent>
        </Card>
      ) : actions.length ? (
        <div className="space-y-3">
          {actions.map((action) => (
            <CommandCard key={action.id} action={action} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="space-y-2 p-6">
            <p className="font-headline text-2xl font-bold tracking-tight">
              No Ranked Moves for {selectedLeague?.league_name ?? "This League"}
            </p>
            <p className="text-sm leading-6 text-muted-foreground">
              Run recompute after a fresh ingest, or include start/sit if you want
              lineup-only actions in this view.
            </p>
          </CardContent>
        </Card>
      )}
    </section>
  )
}

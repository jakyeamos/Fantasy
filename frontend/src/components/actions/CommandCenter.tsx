import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, ArrowRight, RefreshCcw } from "lucide-react"

import { commandCenterOptions, recomputeActions } from "@/api/queries"
import type { CommandAction } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

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

function CommandCard({ action }: { action: CommandAction }) {
  return (
    <Card className="min-h-[244px]">
      <CardHeader className="space-y-3 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">#{action.priority_rank}</Badge>
          <Badge variant="secondary">{categoryLabel[action.category]}</Badge>
          <Badge variant={confidenceVariant(action.confidence)}>{action.confidence}</Badge>
          <span className="terminal-label text-muted-foreground">
            {urgencyCopy(action.urgency)}
          </span>
        </div>
        <CardTitle className="text-xl leading-6">{action.headline}</CardTitle>
      </CardHeader>
      <CardContent className="flex h-[calc(100%-96px)] flex-col justify-between gap-4">
        <div className="space-y-3">
          <p className="text-sm font-semibold leading-6">{action.recommended_action}</p>
          <div className="space-y-2 text-sm leading-6 text-muted-foreground">
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
            <div className="flex items-center gap-2 rounded border border-orange-400/30 bg-orange-400/10 px-3 py-2 text-xs text-orange-300">
              <AlertTriangle className="size-3.5 shrink-0" />
              Refresh {action.stale_domains.join(", ")} before locking this in.
            </div>
          ) : null}
        </div>
        <a href={action.cta_destination} className={buttonClasses({ variant: "outline" })}>
          {action.cta_label}
          <ArrowRight className="size-3.5" />
        </a>
      </CardContent>
    </Card>
  )
}

export function CommandCenter() {
  const query = useQuery(commandCenterOptions)

  if (query.isLoading) {
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

  const actions = query.data?.actions.slice(0, 5) ?? []

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/45 pb-4">
        <div className="space-y-2">
          <p className="terminal-label text-primary/85">Private Edge Command Center</p>
          <h2 className="font-headline text-4xl font-extrabold tracking-tight">
            Top moves today
          </h2>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            Ranked cross-league actions with the claim, drop, price, pitch, risk,
            and next click made explicit.
          </p>
        </div>
        <button
          type="button"
          className={buttonClasses({ variant: "outline" })}
          onClick={() => {
            void recomputeActions().then(() => query.refetch())
          }}
        >
          <RefreshCcw className="size-3.5" />
          Recompute
        </button>
      </div>

      {query.isError ? (
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
        <div className="grid gap-4 xl:grid-cols-5 lg:grid-cols-3 md:grid-cols-2">
          {actions.map((action) => (
            <CommandCard key={action.id} action={action} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="space-y-2 p-6">
            <p className="font-headline text-2xl font-bold tracking-tight">
              No Ranked Moves Yet
            </p>
            <p className="text-sm leading-6 text-muted-foreground">
              Run recompute after a fresh ingest to warm waiver, market, manager,
              and portfolio artifacts for command ranking.
            </p>
          </CardContent>
        </Card>
      )}
    </section>
  )
}


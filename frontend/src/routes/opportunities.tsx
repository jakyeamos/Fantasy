import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useMemo, useState } from "react"

import { opportunityFeedOptions } from "@/api/queries"
import type { OpportunityFeedItem } from "@/api/types"
import { OpportunityCardList } from "@/components/opportunities/OpportunityCardList"
import { buttonClasses } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { filterOpportunityItems } from "@/lib/opportunityFilters"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/opportunities")({
  component: OpportunityFeedPage,
})

function OpportunityFeedPage() {
  const query = useQuery(opportunityFeedOptions)
  const items = query.data?.items ?? []
  const [scopeFilter, setScopeFilter] = useState<
    "all" | "my_roster" | "available" | "opponent_roster"
  >("all")
  const [actionFilter, setActionFilter] = useState<
    "all" | OpportunityFeedItem["suggested_action"]
  >("all")
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false)
  const [leagueFilter, setLeagueFilter] = useState("all")
  const [includeSpeculative, setIncludeSpeculative] = useState(false)
  const [lineupFitOnly, setLineupFitOnly] = useState(false)
  const leagueOptions = useMemo(
    () =>
      Array.from(
        new Set(
          items.flatMap((item) => [
            ...item.owned_in_leagues,
            item.cta?.league_id ?? "",
          ]),
        ),
      )
        .filter(Boolean)
        .sort(),
    [items],
  )
  const filteredItems = filterOpportunityItems(items, {
    scopeFilter,
    actionFilter,
    highConfidenceOnly,
    leagueFilter,
    includeSpeculative,
    lineupFitOnly,
  })
  const topSignal = items[0] ?? null
  const isTimeout = query.error?.name === "TimeoutError"
  const isUnavailable = query.isError && !query.data
  const updatedAt = (() => {
    if (query.data?.computed_at) {
      return new Intl.DateTimeFormat("en", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(query.data.computed_at))
    }
    if (isTimeout) {
      return "Timed out"
    }
    if (query.isError) {
      return "Unavailable"
    }
    return "Pending"
  })()

  return (
    <div className="space-y-8">
      <section className="grid gap-5 border-b border-border/45 pb-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-3">
          <p className="terminal-label text-primary/85">
            Ranked by impact - gap magnitude x projection confidence
          </p>
          <h2 className="font-headline text-4xl font-extrabold">
            Opportunity Feed
          </h2>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            Scan one ordered list of dynasty buy, sell, and hold signals across
            every league you track, with trend confidence, market gaps, and
            similar-player context attached to each call.
          </p>
        </div>

        <div className="grid grid-cols-3 overflow-hidden rounded-xl border border-border/60 bg-card/60">
          <div className="border-r border-border/45 p-4">
            <p className="terminal-label text-muted-foreground">Signals</p>
            {query.isLoading ? (
              <Skeleton className="mt-3 h-7 w-12" />
            ) : isUnavailable ? (
              <p className="mt-2 font-headline text-2xl font-extrabold">-</p>
            ) : (
              <p className="mt-2 font-headline text-2xl font-extrabold">
                {query.data?.total ?? items.length}
              </p>
            )}
          </div>
          <div className="border-r border-border/45 p-4">
            <p className="terminal-label text-muted-foreground">Top impact</p>
            {query.isLoading ? (
              <Skeleton className="mt-3 h-7 w-14" />
            ) : isUnavailable ? (
              <p className="mt-2 font-headline text-2xl font-extrabold">-</p>
            ) : (
              <p className="mt-2 font-headline text-2xl font-extrabold">
                {topSignal ? Math.round(topSignal.impact_score) : "-"}
              </p>
            )}
          </div>
          <div className="p-4">
            <p className="terminal-label text-muted-foreground">Updated</p>
            {query.isLoading ? (
              <Skeleton className="mt-3 h-5 w-20" />
            ) : (
              <p className="mt-2 text-sm font-bold text-foreground">{updatedAt}</p>
            )}
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          {[
            ["all", "All"],
            ["my_roster", "My roster"],
            ["available", "Available"],
            ["opponent_roster", "Opponent-owned"],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={cn(
                buttonClasses({
                  variant: scopeFilter === value ? "default" : "outline",
                  size: "sm",
                }),
                "min-w-0",
              )}
              onClick={() =>
                setScopeFilter(value as "all" | "my_roster" | "available" | "opponent_roster")
              }
            >
              {label}
            </button>
          ))}
          {[
            ["all", "All actions"],
            ["buy", "Buy"],
            ["sell", "Sell"],
            ["hold", "Hold"],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={buttonClasses({
                variant: actionFilter === value ? "default" : "outline",
                size: "sm",
              })}
              onClick={() =>
                setActionFilter(value as "all" | OpportunityFeedItem["suggested_action"])
              }
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            className={buttonClasses({
              variant: highConfidenceOnly ? "default" : "outline",
              size: "sm",
            })}
            onClick={() => setHighConfidenceOnly((value) => !value)}
          >
            High confidence
          </button>
          <button
            type="button"
            className={buttonClasses({
              variant: lineupFitOnly ? "default" : "outline",
              size: "sm",
            })}
            onClick={() => setLineupFitOnly((value) => !value)}
          >
            Solves lineup gap
          </button>
          <label className="inline-flex min-h-9 items-center gap-2 rounded-md border border-border/60 px-3 text-xs font-medium text-muted-foreground">
            <input
              type="checkbox"
              className="size-3.5"
              checked={includeSpeculative}
              onChange={(event) => setIncludeSpeculative(event.target.checked)}
            />
            Speculative
          </label>
          <select
            className="min-h-9 rounded-md border border-border/60 bg-background px-3 text-xs font-medium text-foreground"
            value={leagueFilter}
            onChange={(event) => setLeagueFilter(event.target.value)}
          >
            <option value="all">By league: all</option>
            {leagueOptions.map((leagueId) => (
              <option key={leagueId} value={leagueId}>
                {leagueId}
              </option>
            ))}
          </select>
        </div>
        <p className="text-xs text-muted-foreground">
          Showing {filteredItems.length} of {items.length} ranked signals.
        </p>
      </section>

      <OpportunityCardList
        items={filteredItems}
        isLoading={query.isLoading}
        isError={query.isError}
        isTimeout={isTimeout}
        isDegraded={query.data?.status === "degraded"}
        degradedReason={query.data?.degraded_reason ?? null}
      />
    </div>
  )
}

import { ArrowRight, ChevronDown, Clock3, ShieldAlert } from "lucide-react"

import type {
  DecisionCard as DecisionCardModel,
  FreshnessState,
} from "@/v2/contracts/decision-card"

const bandClasses = {
  high: "border-success/30 bg-success-surface text-success",
  medium: "border-warning/30 bg-warning-surface text-warning",
  low: "border-destructive/30 bg-destructive-surface text-destructive",
} as const

const freshnessCopy: Record<FreshnessState, string> = {
  fresh: "Fresh evidence",
  stale: "Refresh before acting",
  degraded: "Degraded evidence",
  unknown: "Freshness unknown",
}

export function DecisionCard({ card }: { card: DecisionCardModel }) {
  return (
    <article className="rounded-xl border border-border/60 bg-card/70 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
              {card.lane.replaceAll("_", " ")}
            </span>
            {card.scope.leagueId ? (
              <span className="rounded-md border border-border/50 px-2 py-1 text-xs text-muted-foreground">
                {card.scope.leagueId}
              </span>
            ) : null}
          </div>
          <h3 className="mt-3 font-headline text-xl font-extrabold leading-tight">
            {card.outcome}
          </h3>
        </div>
        <span
          className={`rounded-md border px-2.5 py-1 text-label-xs font-bold uppercase tracking-label-tight ${bandClasses[card.confidence.band]}`}
        >
          {card.confidence.band} confidence
        </span>
      </div>

      <p className="mt-4 text-sm leading-6 text-muted-foreground">
        {card.action}
      </p>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
          <p className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
            Why now
          </p>
          <p className="mt-1 leading-5">{card.confidence.explanation}</p>
        </div>
        <div className="rounded-lg border border-border/50 bg-background/35 p-3">
          <p className="flex items-center gap-2 font-label text-label-xs font-bold uppercase tracking-label text-muted-foreground">
            <Clock3 className="size-3.5" /> Timing
          </p>
          <p className="mt-1 leading-5">{card.timing}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="rounded-md border border-border/50 px-2 py-1">
          {freshnessCopy[card.freshness.state]}
        </span>
        {card.acceptablePrice ? (
          <span className="rounded-md border border-border/50 px-2 py-1">
            Price: {card.acceptablePrice}
          </span>
        ) : null}
        {card.freshness.domains.map((domain) => (
          <span
            key={domain}
            className="rounded-md border border-warning/25 bg-warning-surface px-2 py-1 text-warning"
          >
            {domain}
          </span>
        ))}
      </div>

      <details className="group mt-4 border-t border-border/40 pt-3">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs font-semibold text-muted-foreground">
          Evidence, downside, and invalidation
          <ChevronDown className="size-4 transition-transform group-open:rotate-180" />
        </summary>
        <div className="mt-3 space-y-2 text-sm leading-5 text-muted-foreground">
          <ul className="list-disc space-y-1 pl-5">
            {card.evidence.map((evidence) => (
              <li key={evidence}>{evidence}</li>
            ))}
          </ul>
          <p className="flex gap-2">
            <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning" />
            <span>Risk: {card.risk}</span>
          </p>
          <p>Invalidated by: {card.invalidation}</p>
        </div>
      </details>

      <a
        href={card.cta.destination}
        className="mt-4 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-md border border-primary/35 bg-primary px-4 py-2 font-label text-label-sm font-bold uppercase tracking-label text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 sm:w-auto"
      >
        {card.cta.label}
        <ArrowRight className="size-4" />
      </a>
    </article>
  )
}

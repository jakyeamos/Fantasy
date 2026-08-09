import { AlertTriangle, CheckCircle2, LoaderCircle } from "lucide-react"

type State = "loading" | "empty" | "stale" | "degraded" | "blocked" | "error" | "ready"

const copy: Record<State, { title: string; body: string }> = {
  loading: {
    title: "Preparing the read model",
    body: "Loading verified local evidence.",
  },
  empty: {
    title: "No decision yet",
    body: "Connect or refresh a league before relying on this surface.",
  },
  stale: {
    title: "Evidence needs refresh",
    body: "The last confirmed result is retained and marked stale.",
  },
  degraded: {
    title: "Partial evidence",
    body: "Some sources failed. Existing confirmed values remain visible.",
  },
  blocked: {
    title: "Action blocked",
    body: "The required identity, roster rule, or source evidence is missing.",
  },
  error: {
    title: "Could not load this surface",
    body: "Check local backend readiness and try again.",
  },
  ready: { title: "Ready", body: "Evidence is available for review." },
}

export function StatePanel({
  state,
  title,
  body,
}: {
  state: State
  title?: string
  body?: string
}) {
  const Icon =
    state === "loading"
      ? LoaderCircle
      : state === "error" || state === "degraded"
        ? AlertTriangle
        : CheckCircle2
  return (
    <div
      className="rounded-xl border border-border/60 bg-card/55 p-5"
      role={state === "error" ? "alert" : undefined}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={`mt-0.5 size-5 shrink-0 ${state === "loading" ? "animate-spin text-primary" : state === "error" || state === "degraded" ? "text-warning" : "text-accent"}`}
        />
        <div>
          <h3 className="font-headline text-lg font-bold">{title ?? copy[state].title}</h3>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{body ?? copy[state].body}</p>
        </div>
      </div>
    </div>
  )
}

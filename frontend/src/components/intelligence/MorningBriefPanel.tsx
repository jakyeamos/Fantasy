import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react"
import { useState } from "react"

import {
  analyzeIntelligenceUrl,
  intelligenceReviewOptions,
  recordBriefFeedback,
  refreshIntelligence,
  reviewIntelligenceEvent,
  todayBriefOptions,
} from "@/api/queries"
import type { BriefItem, FootballEvent } from "@/api/intelligence.generated"
import { Badge } from "@/components/ui/badge"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const laneCopy = {
  changed: "What changed",
  best_move: "Best moves",
  watch: "Watch",
} as const

function BriefCard({ item, briefId }: { item: BriefItem; briefId: string }) {
  const [saved, setSaved] = useState<string | null>(null)
  const feedback = useMutation({
    mutationFn: (verdict: "acted" | "useful" | "not_relevant" | "dismissed") =>
      recordBriefFeedback(briefId, item.item_id, verdict),
    onSuccess: (_, verdict) => setSaved(verdict),
  })
  const confidence = Math.round(item.confidence * 100)
  const deltaEntries = Object.entries(item.impact_summary?.deltas ?? {})

  return (
    <article className="rounded-lg border border-border/60 bg-background/35 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {item.league_id ? (
              <Badge variant="outline">{item.league_id}</Badge>
            ) : null}
            <Badge variant={item.lane === "watch" ? "outline" : "secondary"}>
              {confidence}% confidence
            </Badge>
          </div>
          <h4 className="font-headline text-lg font-bold leading-tight">
            {item.headline}
          </h4>
        </div>
        {item.cta_destination && item.cta_label ? (
          <a
            href={item.cta_destination}
            className={buttonClasses({ variant: "outline", size: "sm" })}
          >
            {item.cta_label}
            <ExternalLink className="size-3.5" />
          </a>
        ) : null}
      </div>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        {item.why_it_matters}
      </p>
      {item.recommended_action ? (
        <p className="mt-3 rounded-md border border-primary/20 bg-primary/5 p-3 text-sm">
          <span className="font-semibold">Next move:</span>{" "}
          {item.recommended_action}
        </p>
      ) : null}
      {deltaEntries.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
          {deltaEntries.map(([label, value]) => (
            <span key={label} className="rounded bg-muted/60 px-2 py-1">
              {label.replaceAll("_", " ")} {value > 0 ? "+" : ""}
              {value.toFixed(2)}
            </span>
          ))}
        </div>
      ) : null}
      <details className="mt-3 text-xs text-muted-foreground">
        <summary className="cursor-pointer">Evidence and invalidation</summary>
        <p className="mt-2">{item.source_summary}</p>
        <p className="mt-1">Invalidated by: {item.invalidation}</p>
      </details>
      <div className="mt-3 flex flex-wrap gap-2 border-t border-border/40 pt-3">
        {(["acted", "useful", "not_relevant", "dismissed"] as const).map(
          (verdict) => (
            <Button
              key={verdict}
              size="sm"
              variant={saved === verdict ? "secondary" : "ghost"}
              disabled={feedback.isPending}
              onClick={() => feedback.mutate(verdict)}
            >
              {verdict.replaceAll("_", " ")}
            </Button>
          ),
        )}
      </div>
    </article>
  )
}

function ReviewClaim({ event }: { event: FootballEvent }) {
  const client = useQueryClient()
  const review = useMutation({
    mutationFn: (decision: "confirm" | "reject") =>
      reviewIntelligenceEvent(event.event_id, decision),
    onSuccess: async () => {
      client.setQueryData<FootballEvent[]>(
        ["v2", "intelligence", "review"],
        (current) =>
          current?.filter((candidate) => candidate.event_id !== event.event_id),
      )
      await client.invalidateQueries({ queryKey: ["v2"] })
    },
  })
  return (
    <article className="rounded-md border border-border/60 p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-semibold">{event.summary}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {event.verification_state.replaceAll("_", " ")} ·{" "}
            {Math.round(event.confidence * 100)}% confidence
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={review.isPending}
            onClick={() => review.mutate("reject")}
          >
            Reject
          </Button>
          <Button
            size="sm"
            disabled={review.isPending || !event.player_id}
            onClick={() => review.mutate("confirm")}
          >
            Confirm
          </Button>
        </div>
      </div>
      {!event.player_id ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Identity is unresolved; confirmation stays disabled until the player
          can be resolved.
        </p>
      ) : null}
    </article>
  )
}

export function MorningBriefPanel() {
  const client = useQueryClient()
  const brief = useQuery(todayBriefOptions)
  const review = useQuery(intelligenceReviewOptions)
  const [url, setUrl] = useState("")
  const [analysisNote, setAnalysisNote] = useState<string | null>(null)
  const refresh = useMutation({
    mutationFn: refreshIntelligence,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["v2"] })
    },
  })
  const analyze = useMutation({
    mutationFn: analyzeIntelligenceUrl,
    onSuccess: async (result) => {
      setAnalysisNote(
        (result.events ?? []).length
          ? `${(result.events ?? []).length} event claim${(result.events ?? []).length === 1 ? "" : "s"} analyzed with ${(result.impacts ?? []).length} league consequences.`
          : "The page was captured, but it contained no schema-valid event claim. No values changed.",
      )
      setUrl("")
      await client.invalidateQueries({ queryKey: ["v2"] })
    },
    onError: (error) => setAnalysisNote(error.message),
  })

  const grouped = Object.fromEntries(
    (["changed", "best_move", "watch"] as const).map((lane) => [
      lane,
      (brief.data?.items ?? []).filter((item) => item.lane === lane),
    ]),
  ) as Record<"changed" | "best_move" | "watch", BriefItem[]>

  return (
    <section className="space-y-4" aria-labelledby="morning-brief-title">
      <Card className="overflow-hidden border-primary/25">
        <CardHeader className="gap-4 bg-gradient-to-br from-primary/10 via-card to-card">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 space-y-2">
              <div className="flex items-center gap-2 text-primary">
                <Sparkles className="size-4" />
                <p className="terminal-label">Prepared intelligence</p>
              </div>
              <CardTitle
                id="morning-brief-title"
                className="font-headline text-3xl"
              >
                Today
              </CardTitle>
              <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                Fresh football events translated into league-specific moves.
                Nothing here submits a waiver, trade, or lineup change.
              </p>
            </div>
            <Button
              className="w-full sm:w-auto"
              onClick={() => refresh.mutate()}
              disabled={refresh.isPending}
            >
              <RefreshCw
                className={`size-4 ${refresh.isPending ? "animate-spin" : ""}`}
              />
              {brief.data ? "Refresh briefing" : "Run morning brief"}
            </Button>
          </div>
          <div className="flex flex-wrap items-start gap-3 text-xs text-muted-foreground">
            {brief.data ? (
              <>
                {brief.data.status === "ready" ? (
                  <CheckCircle2 className="size-4 text-accent" />
                ) : (
                  <AlertTriangle className="size-4 text-destructive" />
                )}
                <span className="min-w-0 break-words">
                  {brief.data.status} · run {brief.data.run_id.slice(0, 8)} ·{" "}
                  {new Date(brief.data.created_at).toLocaleString()}
                </span>
              </>
            ) : (
              <span>
                No verified briefing exists for today. Run it before relying on
                this page.
              </span>
            )}
          </div>
          {refresh.isError ? (
            <p className="text-sm text-destructive">{refresh.error.message}</p>
          ) : null}
        </CardHeader>
      </Card>

      {brief.data ? (
        <div className="grid gap-4 xl:grid-cols-3">
          {(["changed", "best_move", "watch"] as const).map((lane) => (
            <Card key={lane}>
              <CardHeader>
                <CardTitle className="text-xl">{laneCopy[lane]}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {grouped[lane].length ? (
                  grouped[lane].map((item) => (
                    <BriefCard
                      key={item.item_id}
                      item={item}
                      briefId={brief.data.brief_id}
                    />
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No {laneCopy[lane].toLowerCase()} items.
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Search className="size-4" />
              Analyze a public link
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-col gap-3 sm:flex-row"
              onSubmit={(event) => {
                event.preventDefault()
                if (url.trim()) analyze.mutate(url.trim())
              }}
            >
              <input
                type="url"
                required
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://public-source.example/story"
                className="h-11 min-w-0 flex-1 rounded-md border border-border bg-background px-3 text-sm"
              />
              <Button type="submit" disabled={analyze.isPending}>
                Analyze
              </Button>
            </form>
            {analysisNote ? (
              <p className="mt-3 text-sm text-muted-foreground">
                {analysisNote}
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Source health and review</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {(brief.data?.source_health ?? []).map((source) => (
              <div
                key={source.source_id}
                className="border-b border-border/40 pb-2"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate">{source.source_id}</span>
                  <Badge
                    variant={
                      source.status === "complete" ? "secondary" : "outline"
                    }
                  >
                    {source.status}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {source.coverage_through
                    ? `Coverage ${new Date(source.coverage_through).toLocaleString()}`
                    : "Coverage unavailable"}
                  {source.message ? ` · ${source.message}` : ""}
                </p>
              </div>
            ))}
            <p className="text-muted-foreground">
              {review.data?.length ?? 0} unresolved event claim
              {review.data?.length === 1 ? "" : "s"} in the review queue.
            </p>
            {(review.data ?? []).map((event) => (
              <ReviewClaim key={event.event_id} event={event} />
            ))}
          </CardContent>
        </Card>
      </div>
    </section>
  )
}

import { useState } from "react"

import type {
  TradeFollowUpEventRequest,
  TradeFollowUpRow,
  TradeFollowUpsResponse,
} from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function eventLabel(event: string): string {
  return event.replaceAll("_", " ")
}

function followUpDate(value: string | null | undefined): string {
  if (!value) return "No date set"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString()
}

function stateLabel(row: TradeFollowUpRow): string {
  if (row.resolution_state === "awaiting_outcome") return "Awaiting outcome"
  if (row.latest_event === "held") return "Held"
  return "Awaiting action"
}

export function TradeFollowUpPanel({
  data,
  isLoading,
  pendingDecisionId,
  onEvent,
}: {
  data?: TradeFollowUpsResponse
  isLoading: boolean
  pendingDecisionId: string | null
  onEvent: (decisionId: string, request: TradeFollowUpEventRequest) => Promise<void>
}) {
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [holdDates, setHoldDates] = useState<Record<string, string>>({})

  if (isLoading && !data) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Loading Trade Lab follow-ups…
        </CardContent>
      </Card>
    )
  }

  if (!data) return null

  const calibration = data.calibration
  const scopeName = data.league_name ?? data.league_id
  const available = calibration.win_probability_status === "available"

  const submit = async (
    row: TradeFollowUpRow,
    eventType: TradeFollowUpEventRequest["event_type"],
    outcome?: TradeFollowUpEventRequest["outcome"],
  ) => {
    await onEvent(row.decision_id, {
      event_type: eventType,
      outcome: outcome ?? null,
      follow_up_at:
        eventType === "held" && holdDates[row.decision_id]
          ? new Date(`${holdDates[row.decision_id]}T12:00:00`).toISOString()
          : null,
      notes: notes[row.decision_id]?.trim() || null,
    })
  }

  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="terminal-label text-primary/85">Decision lifecycle · append-only</p>
            <CardTitle className="mt-1 text-2xl">Trade Lab follow-ups</CardTitle>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Record what happened after a Trade Lab recommendation. Each check-in adds a lifecycle
              event; it never rewrites the original analysis.
            </p>
          </div>
          <Badge
            variant="outline"
            className={
              available
                ? "border-success/25 bg-success/10 text-success"
                : "border-warning/25 bg-warning-surface text-warning"
            }
          >
            {available ? "Win probability available" : "Win probability unavailable"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="rounded-xl border border-border/40 bg-card/45 p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="terminal-label text-muted-foreground">Calibration progress</p>
              <p className="mt-1 text-lg font-semibold text-foreground">
                {calibration.sample_size} / {calibration.minimum_sample_size} labeled {scopeName}{" "}
                trade outcomes
              </p>
            </div>
            <p className="font-mono text-sm text-muted-foreground">
              {calibration.captured_decisions} trade decisions captured
            </p>
          </div>
          <div
            className="mt-3 h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label={`${scopeName} trade calibration progress`}
            aria-valuemin={0}
            aria-valuemax={calibration.minimum_sample_size}
            aria-valuenow={calibration.sample_size}
          >
            <div
              className={`h-full rounded-full ${available ? "bg-success" : "bg-warning"}`}
              style={{ width: `${calibration.progress_percent}%` }}
            />
          </div>
          <p className={`mt-3 text-sm ${available ? "text-success" : "text-warning"}`}>
            {calibration.message}
          </p>
        </div>

        {data.follow_ups.length ? (
          <div className="space-y-3">
            <div className="flex items-end justify-between gap-3">
              <div>
                <p className="terminal-label text-muted-foreground">Open check-ins</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {data.follow_ups.length} unresolved Trade Lab decision
                  {data.follow_ups.length === 1 ? "" : "s"}
                </p>
              </div>
              <p className="terminal-label text-muted-foreground">Due dates are advisory</p>
            </div>
            {data.follow_ups.map((row) => {
              const pending = pendingDecisionId === row.decision_id
              const awaitingOutcome = row.resolution_state === "awaiting_outcome"
              return (
                <div
                  key={row.decision_id}
                  className="rounded-xl border border-border/40 bg-background/35 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">
                        {row.question ?? `Trade decision ${row.decision_id}`}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Recommendation:{" "}
                        <span className="font-mono">{eventLabel(row.recommendation_action)}</span> ·{" "}
                        {Math.round(row.confidence * 100)} score confidence · follow up{" "}
                        {followUpDate(row.follow_up_at)}
                      </p>
                    </div>
                    <Badge variant="outline">{stateLabel(row)}</Badge>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    {row.history.map((event) => (
                      <span
                        key={event.id}
                        className="rounded-full border border-border/45 px-2 py-1"
                      >
                        {eventLabel(event.event_type)} · {followUpDate(event.created_at)}
                      </span>
                    ))}
                  </div>

                  <label className="mt-4 block">
                    <span className="terminal-label text-muted-foreground">Optional note</span>
                    <input
                      value={notes[row.decision_id] ?? ""}
                      onChange={(event) =>
                        setNotes((current) => ({
                          ...current,
                          [row.decision_id]: event.target.value,
                        }))
                      }
                      placeholder="What did you learn?"
                      className="mt-2 h-10 w-full rounded-lg border border-border bg-card px-3 text-sm"
                      disabled={pending}
                    />
                  </label>

                  {awaitingOutcome ? (
                    <div className="mt-4 space-y-2">
                      <p className="terminal-label text-muted-foreground">Outcome check-in</p>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          disabled={pending}
                          onClick={() => submit(row, "outcome", "recommendation_correct")}
                        >
                          Outcome: correct
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={pending}
                          onClick={() => submit(row, "outcome", "recommendation_incorrect")}
                        >
                          Outcome: incorrect
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 space-y-2">
                      <p className="terminal-label text-muted-foreground">Action check-in</p>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          disabled={pending}
                          onClick={() => submit(row, "accepted")}
                        >
                          Mark accepted
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={pending}
                          onClick={() => submit(row, "rejected")}
                        >
                          Mark rejected
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={pending}
                          onClick={() => submit(row, "held")}
                        >
                          Hold for later
                        </Button>
                      </div>
                      <label className="block max-w-xs">
                        <span className="text-xs text-muted-foreground">Optional hold date</span>
                        <input
                          type="date"
                          value={holdDates[row.decision_id] ?? ""}
                          onChange={(event) =>
                            setHoldDates((current) => ({
                              ...current,
                              [row.decision_id]: event.target.value,
                            }))
                          }
                          className="mt-1 h-9 w-full rounded-lg border border-border bg-card px-3 text-sm"
                          disabled={pending}
                        />
                      </label>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border/50 p-4 text-sm text-muted-foreground">
            No unresolved Trade Lab decisions for {scopeName}. Evaluate an offer to start a new
            follow-up cycle.
          </div>
        )}
      </CardContent>
    </Card>
  )
}

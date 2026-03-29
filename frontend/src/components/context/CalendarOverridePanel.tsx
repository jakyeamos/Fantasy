import { useState } from "react"

import { useQueryClient } from "@tanstack/react-query"

import { deleteJson, postJson } from "@/api/queries"
import type { CalendarContext, CalendarState } from "@/api/types"
import { CalendarStateBadge } from "@/components/context/CalendarStateBadge"

const OVERRIDE_STATES: CalendarState[] = [
  "startup",
  "preseason",
  "early_season",
  "trade_deadline",
  "playoffs",
  "rookie_fever",
  "post_combine",
  "post_nfl_draft",
]

export function CalendarOverridePanel({
  leagueId,
  context,
}: {
  leagueId: string
  context: CalendarContext
}) {
  const queryClient = useQueryClient()
  const [selectedState, setSelectedState] = useState<CalendarState>(
    context.active_state,
  )
  const [loading, setLoading] = useState(false)

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["context", "calendar", leagueId] })
    await queryClient.invalidateQueries({ queryKey: ["dashboard", "league", leagueId] })
    await queryClient.invalidateQueries({ queryKey: ["picks", "list", leagueId] })
  }

  const handleSetOverride = async () => {
    setLoading(true)
    try {
      await postJson(`/context/${leagueId}/calendar/override`, {
        state: selectedState,
      })
      await invalidate()
    } finally {
      setLoading(false)
    }
  }

  const handleClearOverride = async () => {
    setLoading(true)
    try {
      await deleteJson(`/context/${leagueId}/calendar/override`)
      await invalidate()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-border/45 bg-card/45 p-4 text-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="terminal-label text-muted-foreground">Calendar state</span>
        <CalendarStateBadge
          state={context.active_state}
          isOverride={context.is_override}
        />
      </div>
      <div className="flex items-center gap-2">
        <select
          className="flex-1 rounded border border-border bg-background px-2 py-1 text-xs"
          value={selectedState}
          onChange={(event) =>
            setSelectedState(event.target.value as CalendarState)
          }
          disabled={loading}
        >
          {OVERRIDE_STATES.map((state) => (
            <option key={state} value={state}>
              {state.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <button
          className="rounded bg-primary px-2 py-1 text-xs text-primary-foreground disabled:opacity-50"
          onClick={() => void handleSetOverride()}
          disabled={loading}
        >
          Set
        </button>
        {context.is_override ? (
          <button
            className="rounded border border-border px-2 py-1 text-xs text-muted-foreground disabled:opacity-50"
            onClick={() => void handleClearOverride()}
            disabled={loading}
          >
            Clear
          </button>
        ) : null}
      </div>
      {context.is_override ? (
        <p className="mt-2 text-xs text-amber-600 dark:text-amber-300">
          Manual override active - auto-detection is suppressed.
        </p>
      ) : null}
    </div>
  )
}

import { useMemo } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { PickSearchResult, PickValue } from "@/api/types"
import { pickInventoryOptions, pickListOptions } from "@/api/queries"
import { CalendarStateBadge } from "@/components/context/CalendarStateBadge"
import { FreshnessWarningBar } from "@/components/context/FreshnessWarningBar"
import { RuleCitation } from "@/components/picks/RuleCitation"
import { TimingBadge } from "@/components/picks/TimingBadge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

function pickKey(value: {
  pick_owner_roster_id: number
  pick_year: number
  pick_round: number
}) {
  return `${value.pick_owner_roster_id}:${value.pick_year}:${value.pick_round}`
}

function inventoryKey(value: PickSearchResult) {
  return `${value.original_owner_id}:${value.pick_year}:${value.round}`
}

function formatValue(value: number) {
  return value.toFixed(1)
}

function ordinal(value: number) {
  if (value % 100 >= 10 && value % 100 <= 20) return `${value}th`
  if (value % 10 === 1) return `${value}st`
  if (value % 10 === 2) return `${value}nd`
  if (value % 10 === 3) return `${value}rd`
  return `${value}th`
}

function formatPickLabel(pickValue: PickValue) {
  return `${pickValue.pick.pick_year} ${ordinal(pickValue.pick.pick_round)}`
}

function slotLabel(round: number, slot: number) {
  return `${round}.${String(slot).padStart(2, "0")}`
}

function roundedSlot(pickValue: PickValue) {
  return Math.max(1, Math.round(pickValue.expected_draft_slot))
}

function formatProjectedSlot(pickValue: PickValue) {
  return slotLabel(pickValue.pick.pick_round, roundedSlot(pickValue))
}

function formatProjectedRange(pickValue: PickValue) {
  const start = Math.max(1, Math.floor(pickValue.expected_draft_slot))
  const end = Math.max(start, Math.ceil(pickValue.expected_draft_slot))
  if (start === end) {
    return `~${slotLabel(pickValue.pick.pick_round, start)}`
  }
  return `~${slotLabel(pickValue.pick.pick_round, start)}-${String(end).padStart(2, "0")}`
}

function ownerSummary(inventory: PickSearchResult | undefined) {
  if (!inventory) return null
  if (inventory.current_owner_name === inventory.original_owner_name) {
    return `From ${inventory.original_owner_name}`
  }
  return `From ${inventory.original_owner_name} | Held by ${inventory.current_owner_name}`
}

function relativeTime(value: string | undefined) {
  if (!value) return "just now"
  const date = new Date(value)
  const minutes = Math.max(1, Math.round((Date.now() - date.getTime()) / 60000))
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export function LeaguePickList({
  leagueId,
  rosterId,
}: {
  leagueId: string
  rosterId?: number | null
}) {
  const queryClient = useQueryClient()
  const pickListQuery = useQuery(pickListOptions(leagueId, rosterId))
  const inventoryQuery = useQuery(pickInventoryOptions(leagueId, rosterId))
  const recomputeMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`/api/picks/${leagueId}/recompute`, {
        method: "POST",
      })
      if (!response.ok) {
        throw new Error("Failed to recompute picks")
      }
      return response.json() as Promise<{ recomputed: number }>
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["picks", leagueId] })
      await queryClient.invalidateQueries({
        queryKey: ["picks", "list", leagueId],
      })
    },
  })

  const inventoryByKey = useMemo(
    () =>
      new Map(
        (inventoryQuery.data ?? []).map((row) => [inventoryKey(row), row]),
      ),
    [inventoryQuery.data],
  )
  const lastComputedAt = useMemo(
    () =>
      [...(pickListQuery.data?.picks ?? [])]
        .sort(
          (a, b) =>
            new Date(b.computed_at).getTime() -
            new Date(a.computed_at).getTime(),
        )
        .at(0)?.computed_at,
    [pickListQuery.data?.picks],
  )

  if (pickListQuery.isLoading || inventoryQuery.isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pick Capital</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-11 w-full" />
          ))}
        </CardContent>
      </Card>
    )
  }

  if (pickListQuery.isError || inventoryQuery.isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pick Capital</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Pick values unavailable. Try recomputing or check the backend.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!pickListQuery.data || pickListQuery.data.picks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pick Capital</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {rosterId
              ? "No future picks currently belong to your roster."
              : "No future picks tracked for this league."}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <CardTitle>Pick Capital</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            Timed value, projected slot range, and market posture for every
            future pick.
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Last computed: {relativeTime(lastComputedAt)}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => recomputeMutation.mutate()}
          disabled={recomputeMutation.isPending}
        >
          {recomputeMutation.isPending ? "Recomputing..." : "Recompute Picks"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <CalendarStateBadge
            state={pickListQuery.data.recommendation_context.calendar_state}
          />
          {pickListQuery.data.recommendation_context.calendar_note ? (
            <p className="text-xs text-muted-foreground">
              {pickListQuery.data.recommendation_context.calendar_note}
            </p>
          ) : null}
          <FreshnessWarningBar
            tags={pickListQuery.data.recommendation_context.freshness_tags}
          />
        </div>
        {pickListQuery.data.picks.map((pickValue) => {
          const key = pickKey({
            pick_owner_roster_id: pickValue.pick.pick_owner_roster_id,
            pick_year: pickValue.pick.pick_year,
            pick_round: pickValue.pick.pick_round,
          })
          const isBlocked = pickValue.rule_citation === null
          const inventory = inventoryByKey.get(key)
          const ownerText = ownerSummary(inventory)
          return (
            <div
              key={key}
              className="rounded-xl border border-border/45 bg-card/45 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold">
                    {formatPickLabel(pickValue)}
                  </p>
                  {ownerText ? (
                    <span className="text-xs text-muted-foreground">
                      {ownerText}
                    </span>
                  ) : null}
                  {!isBlocked ? (
                    <span className="text-xs text-muted-foreground">
                      {formatProjectedRange(pickValue)}
                    </span>
                  ) : null}
                </div>
                {!isBlocked ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <TimingBadge
                      label={pickValue.timing_label}
                      reasoning={pickValue.timing_reasoning}
                      showReasoning={false}
                    />
                    <span className="text-sm font-semibold">
                      {formatValue(pickValue.league_adjusted_value)}
                    </span>
                  </div>
                ) : null}
              </div>
              {!isBlocked ? (
                <>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Projected position: {formatProjectedSlot(pickValue)}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {pickValue.timing_reasoning}
                  </p>
                </>
              ) : null}
              <RuleCitation
                citation={pickValue.rule_citation}
                leagueId={leagueId}
              />
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

import { useEffect, useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import type { LeagueDraftOrderRule } from "@/api/types"
import { draftOrderRuleOptions, saveDraftOrderRule } from "@/api/queries"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"

const basisLabels: Record<LeagueDraftOrderRule["non_playoff_basis"], string> = {
  inverse_standings: "Inverse standings",
  max_points_for: "Max points for",
}

const playoffOrderingLabels: Record<
  LeagueDraftOrderRule["playoff_ordering"],
  string
> = {
  by_finish: "By playoff finish",
  by_record: "By regular-season record",
  by_points_for: "By regular-season points for",
}

const tiebreakerLabels: Record<LeagueDraftOrderRule["tiebreaker"], string> = {
  points_against: "Points against",
  points_for: "Points for",
  commissioner: "Commissioner discretion",
}

export function DraftOrderRuleForm({ leagueId }: { leagueId: string }) {
  const queryClient = useQueryClient()
  const ruleQuery = useQuery(draftOrderRuleOptions(leagueId))
  const rule = ruleQuery.data?.rule ?? null
  const [editing, setEditing] = useState(false)
  const [basis, setBasis] = useState<
    LeagueDraftOrderRule["non_playoff_basis"] | ""
  >("")
  const [playoffOrdering, setPlayoffOrdering] = useState<
    LeagueDraftOrderRule["playoff_ordering"] | ""
  >("")
  const [tiebreaker, setTiebreaker] = useState<
    LeagueDraftOrderRule["tiebreaker"] | ""
  >("")

  useEffect(() => {
    if (editing) return
    if (rule) {
      setBasis(rule.non_playoff_basis)
      setPlayoffOrdering(rule.playoff_ordering)
      setTiebreaker(rule.tiebreaker)
      return
    }
    setBasis("")
    setPlayoffOrdering("")
    setTiebreaker("")
  }, [editing, rule])

  const saveMutation = useMutation({
    mutationFn: (nextRule: LeagueDraftOrderRule) =>
      saveDraftOrderRule(leagueId, nextRule),
    onSuccess: async (data) => {
      queryClient.setQueryData(["picks", leagueId, "draft-order-rule"], data)
      await queryClient.invalidateQueries({ queryKey: ["picks", leagueId] })
      setEditing(false)
    },
  })

  const allFieldsFilled =
    basis !== "" && playoffOrdering !== "" && tiebreaker !== ""
  const showSummary = rule !== null && !editing

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!allFieldsFilled) return
    saveMutation.mutate({
      non_playoff_basis: basis,
      playoff_ordering: playoffOrdering,
      tiebreaker,
    })
  }

  if (ruleQuery.isLoading && rule === null) {
    return (
      <Card id="draft-order-rule">
        <CardHeader>
          <CardTitle>Draft Order Rule</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Loading league draft-order settings...
          </p>
        </CardContent>
      </Card>
    )
  }

  if (showSummary) {
    return (
      <Card id="draft-order-rule">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Draft Order Rule</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              This league&apos;s pick projection rule is configured and active.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
            Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            <span className="text-muted-foreground">Non-playoff ordering:</span>{" "}
            {basisLabels[rule.non_playoff_basis]}
          </p>
          <p>
            <span className="text-muted-foreground">
              Playoff team ordering:
            </span>{" "}
            {playoffOrderingLabels[rule.playoff_ordering]}
          </p>
          <p>
            <span className="text-muted-foreground">Tiebreaker:</span>{" "}
            {tiebreakerLabels[rule.tiebreaker]}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card id="draft-order-rule">
      <CardHeader>
        <CardTitle>Draft Order Rule</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          Pick values stay blocked until this league&apos;s draft-order rule is
          fully configured.
        </p>
      </CardHeader>
      <CardContent>
        <form className="space-y-6" onSubmit={handleSubmit}>
          {ruleQuery.isError ? (
            <p className="rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              The current rule could not be loaded. You can still save a new
              one.
            </p>
          ) : null}

          <div className="space-y-3">
            <Label>Non-playoff order basis</Label>
            <RadioGroup className="gap-3">
              <label className="flex items-start gap-3 rounded-lg border border-border/60 bg-card/60 p-3">
                <RadioGroupItem
                  name="non-playoff-basis"
                  value="inverse_standings"
                  checked={basis === "inverse_standings"}
                  onChange={() => setBasis("inverse_standings")}
                />
                <div className="space-y-1">
                  <span className="text-sm font-semibold">
                    Inverse standings
                  </span>
                  <p className="text-xs text-muted-foreground">
                    Worst record gets the earliest draft slot.
                  </p>
                </div>
              </label>
              <label className="flex items-start gap-3 rounded-lg border border-border/60 bg-card/60 p-3">
                <RadioGroupItem
                  name="non-playoff-basis"
                  value="max_points_for"
                  checked={basis === "max_points_for"}
                  onChange={() => setBasis("max_points_for")}
                />
                <div className="space-y-1">
                  <span className="text-sm font-semibold">Max points for</span>
                  <p className="text-xs text-muted-foreground">
                    Lower season-long points for gets the earlier non-playoff
                    slot.
                  </p>
                </div>
              </label>
            </RadioGroup>
          </div>

          <div className="block space-y-2">
            <Label htmlFor="playoff-ordering">Playoff team ordering</Label>
            <select
              id="playoff-ordering"
              value={playoffOrdering}
              onChange={(event) =>
                setPlayoffOrdering(
                  event.target.value as
                    | LeagueDraftOrderRule["playoff_ordering"]
                    | "",
                )
              }
              className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
            >
              <option value="">Select playoff ordering</option>
              <option value="by_finish">By playoff finish</option>
              <option value="by_record">By regular-season record</option>
              <option value="by_points_for">
                By regular-season points for
              </option>
            </select>
          </div>

          <div className="block space-y-2">
            <Label htmlFor="tiebreaker">Tiebreaker</Label>
            <select
              id="tiebreaker"
              value={tiebreaker}
              onChange={(event) =>
                setTiebreaker(
                  event.target.value as LeagueDraftOrderRule["tiebreaker"] | "",
                )
              }
              className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm"
            >
              <option value="">Select tiebreaker</option>
              <option value="points_against">Points against</option>
              <option value="points_for">Points for</option>
              <option value="commissioner">Commissioner discretion</option>
            </select>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="submit"
              disabled={!allFieldsFilled || saveMutation.isPending}
            >
              {saveMutation.isPending
                ? "Saving..."
                : rule
                  ? "Save Changes"
                  : "Save Rule"}
            </Button>
            {rule ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditing(false)
                  saveMutation.reset()
                }}
              >
                Cancel
              </Button>
            ) : null}
            {saveMutation.isError ? (
              <p className="text-sm text-destructive">
                Failed to save the draft-order rule.
              </p>
            ) : null}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

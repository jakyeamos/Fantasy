import type { PickValue } from "@/api/types"
import { RuleCitation } from "@/components/picks/RuleCitation"
import { TimingBadge } from "@/components/picks/TimingBadge"
import { Badge } from "@/components/ui/badge"

function formatPickLabel(pickValue: PickValue) {
  const year = pickValue.pick.pick_year
  const round = pickValue.pick.pick_round
  return `${year} R${round}`
}

function formatExpectedSlot(pickValue: PickValue) {
  const round = pickValue.pick.pick_round
  const slot = Math.max(1, Math.round(pickValue.expected_draft_slot))
  return `~${round}.${String(slot).padStart(2, "0")}`
}

function formatValue(value: number) {
  return value.toFixed(1)
}

export function PickValueSummaryRow({
  pickValue,
  leagueId,
  managerName,
}: {
  pickValue: PickValue
  leagueId: string
  managerName?: string | null
}) {
  const isBlocked = pickValue.rule_citation === null
  const showDemand =
    !isBlocked &&
    Math.abs(pickValue.demand_adjusted_value - pickValue.league_adjusted_value) >= 0.05

  return (
    <div className="rounded-xl border border-border/70 bg-background/70 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold">{formatPickLabel(pickValue)}</p>
        {!isBlocked ? <Badge variant="outline">{formatExpectedSlot(pickValue)}</Badge> : null}
        {!isBlocked ? (
          <TimingBadge
            label={pickValue.timing_label}
            reasoning={pickValue.timing_reasoning}
            showReasoning={false}
          />
        ) : null}
      </div>
      {!isBlocked ? (
        <>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
            <span className="text-muted-foreground">League value:</span>
            <span>{formatValue(pickValue.league_adjusted_value)}</span>
            {showDemand ? (
              <>
                <span className="text-muted-foreground">
                  To {managerName?.trim() ? managerName : "counterparty"}:
                </span>
                <span className="text-primary">{formatValue(pickValue.demand_adjusted_value)}</span>
              </>
            ) : null}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{pickValue.timing_reasoning}</p>
        </>
      ) : null}
      <RuleCitation citation={pickValue.rule_citation} leagueId={leagueId} />
    </div>
  )
}

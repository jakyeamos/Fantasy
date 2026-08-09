import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, XOctagon } from "lucide-react"

import {
  acknowledgeLeagueFormat,
  leagueAcknowledgedOptions,
  leagueFormatScanOptions,
} from "@/api/queries"
import type { RuleScanEntry } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

const RULE_LABELS: Record<string, string> = {
  median_wins: "Median wins",
  best_ball: "Best ball",
  idp: "IDP",
  salary_cap: "Salary cap",
  first_down_scoring: "First-down scoring",
  return_scoring: "Return scoring",
  wr_bonus: "WR bonus",
  non_dynasty: "Non-dynasty",
}

function formatRuleLabel(rule: string): string {
  return RULE_LABELS[rule] ?? rule.replaceAll("_", " ")
}

function RuleList({
  entries,
  badgeClassName,
}: {
  entries: RuleScanEntry[]
  badgeClassName: string
}) {
  return (
    <div className="space-y-2">
      {entries.map((entry) => (
        <div
          key={entry.rule}
          className="flex flex-wrap items-center gap-2 rounded-lg border border-border/35 bg-card/45 px-3 py-2 text-sm"
        >
          <Badge className={badgeClassName}>
            {formatRuleLabel(entry.rule)}
          </Badge>
          <span className="text-muted-foreground">{entry.reason}</span>
        </div>
      ))}
    </div>
  )
}

export function FormatWarningBanner({ leagueId }: { leagueId: string }) {
  const queryClient = useQueryClient()
  const scanQuery = useQuery(leagueFormatScanOptions(leagueId))
  const acknowledgedQuery = useQuery(leagueAcknowledgedOptions(leagueId))

  const acknowledgeMutation = useMutation({
    mutationFn: () => acknowledgeLeagueFormat(leagueId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["trust", leagueId] })
    },
  })

  if (scanQuery.isLoading || scanQuery.isError || !scanQuery.data) {
    return null
  }

  const unsupportedEntries = scanQuery.data.entries.filter(
    (entry) => entry.support_level === "unsupported",
  )
  const partialEntries = scanQuery.data.entries.filter(
    (entry) =>
      entry.support_level === "partially_supported" &&
      entry.distorts_recommendations,
  )

  if (unsupportedEntries.length > 0) {
    return (
      <div className="glass-panel rounded-xl border border-destructive/25 bg-destructive/10 p-5">
        <div className="flex items-start gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg border border-destructive/25 bg-destructive/15 text-destructive">
            <XOctagon className="size-4" />
          </div>
          <div className="min-w-0 flex-1 space-y-3">
            <div className="space-y-1">
              <p className="terminal-label text-destructive/85">
                Unsupported league rules
              </p>
              <p className="text-sm text-muted-foreground">
                This league uses rules the app does not model cleanly.
                Recommendations remain visible, but confidence should be treated
                as degraded.
              </p>
            </div>
            <RuleList
              entries={unsupportedEntries}
              badgeClassName="border border-destructive/25 bg-destructive/15 text-destructive"
            />
          </div>
        </div>
      </div>
    )
  }

  if (partialEntries.length === 0) {
    return null
  }

  if (
    acknowledgedQuery.isLoading ||
    acknowledgedQuery.isError ||
    !acknowledgedQuery.data
  ) {
    return null
  }

  if (acknowledgedQuery.data.acknowledged) {
    return null
  }

  return (
    <div className="glass-panel rounded-xl border border-primary/25 bg-card/65 p-5">
      <div className="flex items-start gap-3">
        <div className="flex size-10 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
          <AlertTriangle className="size-4" />
        </div>
        <div className="min-w-0 flex-1 space-y-3">
          <div className="space-y-1">
            <p className="terminal-label text-primary/85">
              Partially supported league rules
            </p>
            <p className="text-sm text-muted-foreground">
              This league uses format settings that can distort confidence.
              Review the flagged rules before relying on lineup, trade, or
              roster recommendations.
            </p>
          </div>
          <RuleList
            entries={partialEntries}
            badgeClassName="border border-primary/25 bg-primary/10 text-primary"
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              size="sm"
              onClick={() => acknowledgeMutation.mutate()}
              disabled={acknowledgeMutation.isPending}
            >
              {acknowledgeMutation.isPending
                ? "Saving..."
                : "I understand, continue"}
            </Button>
            {acknowledgeMutation.isError ? (
              <p className="text-sm text-destructive">
                Failed to persist the acknowledgment.
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

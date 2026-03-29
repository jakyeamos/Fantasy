import { useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"

import { managerProfileOptions } from "@/api/queries"
import { DossierDraftPicksTab } from "@/components/DossierDraftPicksTab"
import { DossierOverviewTab } from "@/components/DossierOverviewTab"
import { DossierPitchAnglesTab } from "@/components/DossierPitchAnglesTab"
import { DossierTradeHistoryTab } from "@/components/DossierTradeHistoryTab"
import { Badge } from "@/components/ui/badge"
import { Button, buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatModelLabel } from "@/lib/utils"

export const Route = createFileRoute("/league/$leagueId/managers/$managerId")({
  component: ManagerDossierPlaceholderPage,
})

function ManagerDossierPlaceholderPage() {
  const { leagueId, managerId } = Route.useParams()
  const [tab, setTab] = useState<
    "overview" | "trade-history" | "pitch-angles" | "draft-picks"
  >("overview")
  const profileQuery = useQuery(managerProfileOptions(leagueId, managerId))

  if (profileQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (profileQuery.isError || !profileQuery.data) {
    return (
      <p className="text-sm text-muted-foreground">
        Manager dossier unavailable. Try refreshing.
      </p>
    )
  }

  const profile = profileQuery.data

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <p className="terminal-label text-muted-foreground">Manager dossier</p>
                <CardTitle className="mt-2 text-3xl">
                  {profile.manager_name ?? `Roster ${profile.roster_id}`}
                </CardTitle>
              </div>
              {profile.direction_label ? (
                <Badge variant="secondary">
                  {formatModelLabel(profile.direction_label)}
                </Badge>
              ) : null}
            </div>
            <div
              className={`rounded-xl border px-4 py-3 text-sm ${
                profile.low_confidence ? "opacity-75 text-muted-foreground" : "text-muted-foreground"
              }`}
            >
              <span className="terminal-label">Exploitability</span>{" "}
              <span
                className={
                  profile.low_confidence
                    ? "font-semibold text-muted-foreground"
                    : "font-semibold text-primary"
                }
              >
                {profile.exploitability_score.toFixed(0)}
              </span>{" "}
              | {profile.evidence_count} trades
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/league/$leagueId/managers"
              params={{ leagueId }}
              className={buttonClasses({ variant: "outline" })}
            >
              Back to Managers
            </Link>
            <Link
              to="/trades"
              search={{ leagueId }}
              className={buttonClasses({})}
            >
              Evaluate Trade
            </Link>
          </div>
        </CardHeader>
      </Card>

      <div className="flex flex-wrap gap-2 rounded-xl border border-border/40 bg-card/45 p-2">
        {[
          { key: "overview", label: "Overview" },
          { key: "trade-history", label: "Trade History" },
          { key: "pitch-angles", label: "Pitch Angles" },
          ...(profile.show_draft_picks_tab
            ? [{ key: "draft-picks", label: "Draft & Picks" }]
            : []),
        ].map((item) => (
          <Button
            key={item.key}
            variant={tab === item.key ? "default" : "ghost"}
            onClick={() =>
              setTab(
                item.key as
                  | "overview"
                  | "trade-history"
                  | "pitch-angles"
                  | "draft-picks",
              )
            }
          >
            {item.label}
          </Button>
        ))}
      </div>

      {tab === "overview" ? <DossierOverviewTab profile={profile} /> : null}
      {tab === "trade-history" ? (
        <DossierTradeHistoryTab trades={profile.trade_history} />
      ) : null}
      {tab === "pitch-angles" ? (
        <DossierPitchAnglesTab pitchAngles={profile.pitch_angles} />
      ) : null}
      {tab === "draft-picks" && profile.show_draft_picks_tab ? (
        <DossierDraftPicksTab
          pickPremiumScore={profile.pick_premium_score ?? null}
          pickTradeEvidence={profile.pick_trade_evidence ?? 0}
          draftSelectionHistory={profile.draft_selection_history ?? []}
          archetypePattern={profile.archetype_pattern ?? {}}
        />
      ) : null}
    </div>
  )
}

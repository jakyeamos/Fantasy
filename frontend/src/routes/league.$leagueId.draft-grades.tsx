import { useMemo, useState } from "react"

import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { ChevronDown, ChevronUp } from "lucide-react"

import { draftGradesOptions } from "@/api/queries"
import type { DraftGradeSelection, DraftGradeTeamSummary } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/league/$leagueId/draft-grades")({
  component: LeagueDraftGradesPage,
})

type DraftTypeFilter = "all" | "rookie" | "startup"

function deltaText(value: number): string {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`
}

function gradeTone(score: number): string {
  if (score >= 85) return "text-success"
  if (score >= 58) return "text-primary"
  if (score >= 45) return "text-warning"
  return "text-destructive"
}

function SummaryCard({
  label,
  title,
  detail,
}: {
  label: string
  title: string
  detail: string
}) {
  return (
    <div className="rounded-xl border border-border/40 bg-card/45 p-4">
      <p className="terminal-label text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold">{title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
    </div>
  )
}

function SelectionRow({
  selection,
  expanded,
  onToggle,
}: {
  selection: DraftGradeSelection
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div className="rounded-xl border border-border/45 bg-card/45">
      <button
        type="button"
        onClick={onToggle}
        aria-label={`Toggle draft grade for ${selection.player_name} at pick ${selection.pick_slot}`}
        className="grid w-full gap-3 p-4 text-left md:grid-cols-[90px_1fr_auto_auto_auto] md:items-center"
      >
        <div>
          <p className="terminal-label text-muted-foreground">Pick</p>
          <p className="mt-1 font-mono text-sm">{selection.pick_slot}</p>
        </div>
        <div>
          <p className="font-semibold">{selection.player_name}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {selection.roster_name} · {selection.position ?? "UNK"} ·{" "}
            {selection.season} {selection.draft_type}
          </p>
        </div>
        <Badge variant="outline">Round {selection.round_number}</Badge>
        <div>
          <p className="terminal-label text-muted-foreground">Grade</p>
          <p
            className={`mt-1 font-mono text-sm ${gradeTone(selection.grade_score)}`}
          >
            {selection.grade_label} {selection.grade_score.toFixed(0)}
          </p>
        </div>
        <div className="flex items-center gap-2 md:justify-end">
          <Badge variant={selection.value_delta >= 0 ? "secondary" : "outline"}>
            {deltaText(selection.value_delta)}
          </Badge>
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </div>
      </button>
      {expanded ? (
        <div className="grid gap-4 border-t border-border/40 p-4 md:grid-cols-[1.2fr_1fr]">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {selection.rationale}
            </p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">
                Current {selection.current_value.toFixed(2)}
              </Badge>
              <Badge variant="outline">
                Slot baseline {selection.expected_value.toFixed(2)}
              </Badge>
              <Badge variant="outline">Rank delta {selection.rank_delta}</Badge>
            </div>
          </div>
          <div className="rounded-lg border border-border/35 bg-background/35 p-3">
            <p className="terminal-label text-muted-foreground">At-Time Lane</p>
            <p className="mt-2 text-sm">
              {selection.at_time.status === "available"
                ? `Snapshot value ${selection.at_time.value?.toFixed(2) ?? "--"}`
                : "Unavailable"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {selection.at_time.note}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function teamCardDetail(
  team: DraftGradeTeamSummary | null | undefined,
): string {
  if (!team) return "No draft selections available."
  return `${team.pick_count} picks · ${deltaText(team.total_value_delta)} value delta`
}

function LeagueDraftGradesPage() {
  const { leagueId } = Route.useParams()
  const query = useQuery(draftGradesOptions(leagueId))
  const [draftType, setDraftType] = useState<DraftTypeFilter>("all")
  const [season, setSeason] = useState("all")
  const [manager, setManager] = useState("all")
  const [expandedKey, setExpandedKey] = useState<string | null>(null)

  const seasons = useMemo(() => {
    const values = new Set<number>()
    for (const selection of query.data?.selections ?? []) {
      values.add(selection.season)
    }
    return [...values].sort((a, b) => b - a)
  }, [query.data?.selections])

  const managers = useMemo(() => {
    const map = new Map<number, string>()
    for (const selection of query.data?.selections ?? []) {
      map.set(selection.roster_id, selection.roster_name)
    }
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [query.data?.selections])

  const selections = useMemo(() => {
    return (query.data?.selections ?? []).filter((selection) => {
      const typeMatch =
        draftType === "all" || selection.draft_type === draftType
      const seasonMatch =
        season === "all" || selection.season === Number(season)
      const managerMatch =
        manager === "all" || selection.roster_id === Number(manager)
      return typeMatch && seasonMatch && managerMatch
    })
  }, [draftType, manager, query.data?.selections, season])

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <p className="text-sm text-muted-foreground">Draft grades unavailable.</p>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <p className="terminal-label text-primary/85">
            League Draft Gradebook
          </p>
          <CardTitle className="mt-2 text-3xl">Draft Grades</CardTitle>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Rookie and startup selections graded by current replay value, slot
            baseline, roster fit, and historical snapshot coverage where
            available.
          </p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 md:grid-cols-4">
            <SummaryCard
              label="Best Value"
              title={query.data.best_value?.player_name ?? "--"}
              detail={
                query.data.best_value
                  ? `${query.data.best_value.roster_name} · ${deltaText(query.data.best_value.value_delta)}`
                  : "No selections"
              }
            />
            <SummaryCard
              label="Biggest Reach"
              title={query.data.biggest_reach?.player_name ?? "--"}
              detail={
                query.data.biggest_reach
                  ? `${query.data.biggest_reach.roster_name} · ${deltaText(query.data.biggest_reach.value_delta)}`
                  : "No selections"
              }
            />
            <SummaryCard
              label="Best Team Draft"
              title={query.data.best_team?.roster_name ?? "--"}
              detail={teamCardDetail(query.data.best_team)}
            />
            <SummaryCard
              label="Weakest Team Draft"
              title={query.data.weakest_team?.roster_name ?? "--"}
              detail={teamCardDetail(query.data.weakest_team)}
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="space-y-2">
              <span className="terminal-label text-muted-foreground">
                Draft Type
              </span>
              <select
                value={draftType}
                onChange={(event) =>
                  setDraftType(event.target.value as DraftTypeFilter)
                }
                className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm"
              >
                <option value="all">All drafts</option>
                <option value="rookie">Rookie</option>
                <option value="startup">Startup</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="terminal-label text-muted-foreground">
                Season
              </span>
              <select
                value={season}
                onChange={(event) => setSeason(event.target.value)}
                className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm"
              >
                <option value="all">All seasons</option>
                {seasons.map((seasonValue) => (
                  <option key={seasonValue} value={seasonValue}>
                    {seasonValue}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="terminal-label text-muted-foreground">
                Manager
              </span>
              <select
                value={manager}
                onChange={(event) => setManager(event.target.value)}
                className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm"
              >
                <option value="all">All managers</option>
                {managers.map(([rosterId, name]) => (
                  <option key={rosterId} value={rosterId}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </CardContent>
      </Card>

      {selections.length ? (
        <div className="space-y-3">
          {selections.map((selection) => {
            const key = `${selection.draft_id}:${selection.player_id}:${selection.pick_slot}`
            return (
              <SelectionRow
                key={key}
                selection={selection}
                expanded={expandedKey === key}
                onToggle={() =>
                  setExpandedKey(expandedKey === key ? null : key)
                }
              />
            )
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="py-10">
            <p className="text-sm text-muted-foreground">
              No stored draft selections match these filters.
            </p>
            <Button
              className="mt-4"
              variant="outline"
              onClick={() => {
                setDraftType("all")
                setSeason("all")
                setManager("all")
              }}
            >
              Clear filters
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

import { useQuery } from "@tanstack/react-query"

import { hygieneOptions } from "@/api/queries"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

import { HygieneSuggestionRow } from "./HygieneSuggestionRow"

type RosterHygienePanelProps = {
  leagueId: string
  rosterId: number
}

export function RosterHygienePanel({ leagueId, rosterId }: RosterHygienePanelProps) {
  const { data, isLoading, isError } = useQuery(hygieneOptions(leagueId, rosterId))

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Roster hygiene suggestions could not be generated. Ingest data may be incomplete.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!data) {
    return null
  }

  const consolidate = data.suggestions.filter((s) => s.action_type === "consolidate")
  const cut = data.suggestions.filter((s) => s.action_type === "cut")
  const stash = data.suggestions.filter((s) => s.action_type === "stash")
  const taxi = data.suggestions.filter((s) => s.action_type === "taxi")

  const hasAny =
    consolidate.length + cut.length + stash.length + taxi.length > 0

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Roster Hygiene</p>
        <CardTitle>Roster Moves</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasAny ? (
          <>
            <p className="text-sm font-medium">Roster Looks Clean</p>
            <p className="mt-1 text-sm text-muted-foreground">
              No consolidation, cut, or stash suggestions at this time. Check back after the next
              ingest.
            </p>
          </>
        ) : (
          <div className="space-y-0 divide-y divide-border/40">
            {consolidate.length > 0 ? (
              <div>
                <p className="terminal-label text-muted-foreground py-2">Consolidate</p>
                {consolidate.map((s, i) => (
                  <HygieneSuggestionRow key={`c-${i}`} suggestion={s} leagueId={leagueId} />
                ))}
              </div>
            ) : null}
            {cut.length > 0 ? (
              <div>
                <p className="terminal-label text-muted-foreground py-2">Cut</p>
                {cut.map((s, i) => (
                  <HygieneSuggestionRow key={`k-${i}`} suggestion={s} leagueId={leagueId} />
                ))}
              </div>
            ) : null}
            {stash.length > 0 ? (
              <div>
                <p className="terminal-label text-muted-foreground py-2">Stash</p>
                {stash.map((s, i) => (
                  <HygieneSuggestionRow key={`s-${i}`} suggestion={s} leagueId={leagueId} />
                ))}
              </div>
            ) : null}
            {taxi.length > 0 ? (
              <div>
                <p className="terminal-label text-muted-foreground py-2">Move to Taxi</p>
                {taxi.map((s, i) => (
                  <HygieneSuggestionRow key={`t-${i}`} suggestion={s} leagueId={leagueId} />
                ))}
              </div>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

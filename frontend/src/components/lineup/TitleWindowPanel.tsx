import { useQuery } from "@tanstack/react-query"

import { lineupScoreOptions } from "@/api/queries"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

type TitleWindowPanelProps = {
  leagueId: string
  rosterId: number
}

export function TitleWindowPanel({ leagueId, rosterId }: TitleWindowPanelProps) {
  const { data, isLoading, isError } = useQuery(lineupScoreOptions(leagueId, rosterId))

  if (isLoading) {
    return <Skeleton className="h-24 w-full" />
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Lineup scores could not be loaded. Try refreshing or check the backend connection.
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.slot_scores.length === 0) {
    return (
      <Card>
        <CardHeader>
          <p className="terminal-label text-muted-foreground">Title Window</p>
          <CardTitle className="text-lg">Window Analysis Unavailable</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Ingest roster data to generate your lineup&apos;s title-window score.
          </p>
        </CardContent>
      </Card>
    )
  }

  const label = data.title_window_label
  const badgeClass =
    label === "Peak Window"
      ? "border-accent/20 bg-accent/10 text-accent-foreground"
      : label === "Fading Window"
        ? "border-primary/25 bg-primary/12 text-primary"
        : "border-border/60 bg-transparent text-muted-foreground"

  const ceiling = data.ceiling_score
  const ceilingWord =
    ceiling >= 0.6 ? "elite" : ceiling >= 0.3 ? "competitive" : "below the field"

  return (
    <Card>
      <CardHeader className="space-y-2">
        <p className="terminal-label text-muted-foreground">Title Window</p>
        <Badge className={`w-fit text-2xl font-headline font-extrabold ${badgeClass}`}>
          {label}
        </Badge>
        <p className="text-sm text-muted-foreground">
          Starter ceiling is {ceilingWord} for this league.
        </p>
      </CardHeader>
    </Card>
  )
}

import { useQuery } from "@tanstack/react-query"

import { hygieneOptions } from "@/api/queries"
import { RecommendationCardList } from "@/components/recommendations/RecommendationCardList"
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

  const sections = [
    {
      title: "Upgrade packages",
      actionTypes: ["consolidate", "package", "throw_in_now"] as const,
    },
    {
      title: "Market actions",
      actionTypes: ["shop", "hold"] as const,
    },
    {
      title: "Bench triage",
      actionTypes: ["cut", "reroll_into_pick"] as const,
    },
    {
      title: "Developmental holds",
      actionTypes: ["stash", "handcuff_speculative"] as const,
    },
    {
      title: "Taxi moves",
      actionTypes: ["taxi"] as const,
    },
  ]
  const populatedSections = sections
    .map((section) => ({
      ...section,
      suggestions: data.suggestions.filter((suggestion) =>
        section.actionTypes.includes(suggestion.action_type),
      ),
    }))
    .filter((section) => section.suggestions.length > 0)

  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Roster Hygiene</p>
        <CardTitle>Roster Moves</CardTitle>
      </CardHeader>
      <CardContent>
        {data.recommendation_cards && data.recommendation_cards.length > 0 ? (
          <div className="mb-6 space-y-3">
            <p className="terminal-label text-muted-foreground">Recommendations</p>
            <RecommendationCardList cards={data.recommendation_cards} />
          </div>
        ) : null}
        {populatedSections.length === 0 ? (
          <>
            <p className="text-sm font-medium">Roster Looks Clean</p>
            <p className="mt-1 text-sm text-muted-foreground">
              No roster triage, package, or taxi suggestions are active right now. Check back
              after the next ingest.
            </p>
          </>
        ) : (
          <div className="space-y-0 divide-y divide-border/40">
            {populatedSections.map((section) => (
              <div key={section.title}>
                <p className="terminal-label py-2 text-muted-foreground">{section.title}</p>
                {section.suggestions.map((suggestion, index) => (
                  <HygieneSuggestionRow
                    key={`${section.title}-${index}`}
                    suggestion={suggestion}
                    leagueId={leagueId}
                  />
                ))}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

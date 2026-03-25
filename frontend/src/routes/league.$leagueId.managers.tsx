import { useEffect } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Outlet, createFileRoute, useLocation } from "@tanstack/react-router"

import { managerSummariesOptions } from "@/api/queries"
import { ManagerListRow } from "@/components/ManagerListRow"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/league/$leagueId/managers")({
  component: ManagersPlaceholderPage,
})

function ManagersPlaceholderPage() {
  const { leagueId } = Route.useParams()
  const location = useLocation()
  const queryClient = useQueryClient()
  const isManagerListRoute = location.pathname === `/league/${leagueId}/managers`
  const summariesQuery = useQuery({
    ...managerSummariesOptions(leagueId),
    enabled: isManagerListRoute,
  })
  const computeMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`/api/profiling/leagues/${leagueId}/managers/compute`, {
        method: "POST",
      })
      if (!response.ok) {
        throw new Error("Failed to compute manager profiles")
      }
      return response.json()
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profiling", "managers", leagueId] })
      await queryClient.invalidateQueries({ queryKey: ["profiling", "manager", leagueId] })
    },
  })

  useEffect(() => {
    if (!isManagerListRoute) {
      return
    }

    if (
      summariesQuery.data &&
      summariesQuery.data.length > 0 &&
      summariesQuery.data.every((summary) => summary.evidence_count === 0) &&
      !computeMutation.isPending &&
      !computeMutation.isSuccess
    ) {
      computeMutation.mutate()
    }
  }, [computeMutation, isManagerListRoute, summariesQuery.data])

  if (!isManagerListRoute) {
    return <Outlet />
  }

  if (summariesQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }

  if (summariesQuery.isError || !summariesQuery.data) {
    return (
      <p className="text-sm text-muted-foreground">
        Manager data unavailable. Try refreshing or recomputing profiles.
      </p>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="terminal-label text-muted-foreground">League {leagueId}</p>
          <h2 className="font-headline text-3xl font-extrabold tracking-tight">Managers</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Behavioral profiles, exploitability, and top trade angles for every roster.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => computeMutation.mutate()}
          disabled={computeMutation.isPending}
        >
          {computeMutation.isPending ? "Refreshing..." : "Refresh Profiles"}
        </Button>
      </div>

      <div className="space-y-3">
        {summariesQuery.data.map((summary) => (
          <ManagerListRow
            key={summary.roster_id}
            leagueId={leagueId}
            summary={summary}
          />
        ))}
      </div>

      <Card className="border-dashed border-border/45">
        <CardHeader>
          <CardTitle>Signal Notes</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Scores below the evidence threshold stay visible but are intentionally dimmed.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

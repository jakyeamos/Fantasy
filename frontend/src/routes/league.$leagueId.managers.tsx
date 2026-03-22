import { createFileRoute } from "@tanstack/react-router"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/league/$leagueId/managers")({
  component: ManagersPlaceholderPage,
})

function ManagersPlaceholderPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Managers</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Manager dossiers will load here once the profiling UI slice is applied.
        </p>
      </CardContent>
    </Card>
  )
}

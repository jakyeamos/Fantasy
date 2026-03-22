import { createFileRoute } from "@tanstack/react-router"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/league/$leagueId/managers/$managerId")({
  component: ManagerDossierPlaceholderPage,
})

function ManagerDossierPlaceholderPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Manager Dossier</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          The dossier UI is scaffolded and linked. Full manager tabs arrive in the next slice.
        </p>
      </CardContent>
    </Card>
  )
}

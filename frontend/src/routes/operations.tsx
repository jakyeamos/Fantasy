import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Activity, Database, RefreshCw } from "lucide-react"

import { readyOptions, healthOptions } from "@/api/queries"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StatePanel } from "@/v2/components/StatePanel"

export const Route = createFileRoute("/operations")({
  component: OperationsPage,
})

function OperationsPage() {
  const health = useQuery(healthOptions)
  const ready = useQuery(readyOptions)

  return (
    <div className="space-y-8">
      <section className="space-y-3 border-b border-border/45 pb-8">
        <p className="font-label text-label-xs font-bold uppercase tracking-label text-primary">
          Operations and trust
        </p>
        <h2 className="font-headline text-4xl font-extrabold tracking-tight">
          Know what is healthy before relying on a move.
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
          Process health, schema readiness, source freshness, and per-league data health are
          separate facts. A green process probe never substitutes for fresh league evidence.
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Activity className="size-4" /> Process health
            </CardTitle>
          </CardHeader>
          <CardContent>
            {health.isLoading ? (
              <StatePanel state="loading" />
            ) : health.isError ? (
              <StatePanel state="error" />
            ) : (
              <StatePanel
                state="ready"
                title="Backend process is reachable"
                body={`${health.data?.service ?? "fantasy-backend"} responded to /healthz.`}
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Database className="size-4" /> Schema readiness
            </CardTitle>
          </CardHeader>
          <CardContent>
            {ready.isLoading ? (
              <StatePanel state="loading" />
            ) : ready.isError ? (
              <StatePanel
                state="blocked"
                title="Database is not ready"
                body="The process may be reachable, but the required local schema is not verified."
              />
            ) : (
              <StatePanel
                state="ready"
                title="Database is ready"
                body={`${ready.data?.database ?? "database"} and required tables are available.`}
              />
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <RefreshCw className="size-4" /> Refresh and rollback boundary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-6 text-muted-foreground">
          <p>
            Refreshes write only to the configured local DuckDB. Migration rehearsal uses a copied
            database and a restore manifest. External league actions remain manual and outside this
            app boundary.
          </p>
          <p>
            For a blocked migration, preserve the legacy database and restart on the legacy branch;
            do not silently repair or drop tables at startup.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

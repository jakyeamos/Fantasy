import type { RiserFallerEntry } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function Column({
  title,
  items,
  positive,
}: {
  title: string
  items: RiserFallerEntry[]
  positive: boolean
}) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle>{title}</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          {positive
            ? "Players gaining momentum since the latest ingest."
            : "Players losing market ground since the latest ingest."}
        </p>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No actionable movers since last ingest.
          </p>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={`${title}-${item.player_name}`}
                className="rounded-lg border border-border/35 bg-card/45 p-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">{item.player_name}</p>
                  <span
                    className={`font-mono text-xs ${
                      positive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {item.delta > 0 ? "+" : ""}
                    {item.delta.toFixed(1)}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.reason}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function RisersFallersList({
  risers,
  fallers,
}: {
  risers: RiserFallerEntry[]
  fallers: RiserFallerEntry[]
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Column title="Value Risers" items={risers} positive />
      <Column title="Value Fallers" items={fallers} positive={false} />
    </div>
  )
}

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
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No actionable movers since last ingest.
          </p>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={`${title}-${item.player_name}`} className="space-y-1">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs text-muted-foreground">{item.player_name}</p>
                  <span
                    className={`text-xs ${positive ? "text-green-600" : "text-red-600"}`}
                  >
                    {item.delta > 0 ? "+" : ""}
                    {item.delta.toFixed(1)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{item.reason}</p>
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

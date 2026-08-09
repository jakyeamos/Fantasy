import type { ActionPlan } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type ThirtyDayActionPlanCardProps = {
  plan: ActionPlan | null
}

function dotClass(index: number) {
  if (index === 0) return "bg-accent/80"
  if (index < 3) return "bg-primary/30"
  return "bg-border/60"
}

export function ThirtyDayActionPlanCard({
  plan,
}: ThirtyDayActionPlanCardProps) {
  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">
          30-Day Action Plan
        </p>
        <CardTitle>Your First Month</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {plan?.summary ? (
          <p className="text-sm leading-6 text-muted-foreground">
            {plan.summary}
          </p>
        ) : null}
        {plan?.items.length ? (
          <div className="space-y-4">
            {plan.items.map((item, index) => (
              <div
                key={`${item.headline}-${item.priority_rank}`}
                className="flex gap-3"
              >
                <div
                  className={cn("mt-2 size-2 rounded-full", dotClass(index))}
                />
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold">
                      {item.priority_rank}. {item.headline}
                    </span>
                    {item.confidence_label === "LOW" ? (
                      <Badge variant="outline" className="text-xs">
                        LOW
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {item.rationale}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">
            Action-plan output is unavailable for this roster right now.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

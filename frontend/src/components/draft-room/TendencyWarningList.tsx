import type { TendencyWarning } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function TendencyWarningList({
  warnings,
}: {
  warnings: TendencyWarning[]
}) {
  if (!warnings.length) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>League Tendencies</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No major tendency warnings for this slot.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>League Tendencies</CardTitle>
        <p className="mt-2 text-sm text-muted-foreground">
          Structural signals that may distort value at this pick slot.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {warnings.map((warning, index) => (
          <div
            key={`${warning.warning_type}-${index}`}
            className="rounded-xl border border-border/45 bg-card/45 p-4"
          >
            <p className="text-sm font-semibold">{warning.title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{warning.description}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

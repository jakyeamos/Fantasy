import type { PitchAngle } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatModelLabel } from "@/lib/utils"

export function DossierPitchAnglesTab({
  pitchAngles,
}: {
  pitchAngles: PitchAngle[]
}) {
  if (pitchAngles.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pitch Angles</CardTitle>
          <p className="mt-2 text-sm text-muted-foreground">
            No pitch angles available yet. More trade history is needed to compute angles.
          </p>
        </CardHeader>
        <CardContent />
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {pitchAngles.map((angle) => (
        <Card key={angle.rank}>
          <CardHeader>
            <CardTitle className="text-primary">
              {formatModelLabel(angle.deal_archetype)}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="rounded-lg border border-border/35 bg-card/45 px-3 py-3 text-sm">
              <span className="terminal-label text-muted-foreground">Send</span>{" "}
              {angle.send_description}
            </p>
            <p className="rounded-lg border border-border/35 bg-card/45 px-3 py-3 text-sm">
              <span className="terminal-label text-muted-foreground">Avoid</span>{" "}
              {angle.avoid_description}
            </p>
            <p className="border-t border-border/60 pt-3 text-sm italic text-muted-foreground">
              {angle.reasoning}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

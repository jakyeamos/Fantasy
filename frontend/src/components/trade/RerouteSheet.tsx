import type { RerouteResult } from "@/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

export function RerouteSheet({
  open,
  reroutes,
  onClose,
}: {
  open: boolean
  reroutes: RerouteResult[] | null | undefined
  onClose: () => void
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/25 backdrop-blur-sm">
      <div className="glass-panel h-full w-[360px] max-w-full border-l border-border bg-background/95 p-6 shadow-2xl sm:w-[420px]">
        <div className="mb-6 flex items-start justify-between gap-3">
          <div>
            <p className="terminal-label text-primary/85">Alternative Paths</p>
            <p className="mt-2 font-headline text-2xl font-bold">Better Options</p>
            <p className="text-xs text-muted-foreground">Participant-scoped reroute paths</p>
          </div>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
        {!reroutes || reroutes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No reroutes available for this trade.
          </p>
        ) : (
          <div className="space-y-3">
            {reroutes.map((reroute, index) => (
              <Card key={`${reroute.headline}-${index}`}>
                <CardContent className="space-y-2 p-4">
                  {reroute.target_label ? (
                    <p className="terminal-label text-muted-foreground">
                      {reroute.target_label}
                    </p>
                  ) : null}
                  <p className="text-sm font-semibold">{reroute.headline}</p>
                  <p className="text-sm italic text-muted-foreground">{reroute.reasoning}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

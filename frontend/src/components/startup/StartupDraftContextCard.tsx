import type { StartupContext } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatModelLabel } from "@/lib/utils"

type StartupDraftContextCardProps = {
  leagueName: string
  context: StartupContext
}

export function StartupDraftContextCard({
  leagueName,
  context,
}: StartupDraftContextCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="terminal-label text-primary/85">Startup Draft</p>
          <CardTitle className="mt-2 text-3xl">{leagueName}</CardTitle>
        </div>
        <Badge variant="outline">{context.draft_status}</Badge>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="font-headline text-2xl font-extrabold tracking-tight">
          {formatModelLabel(context.direction_label)}
        </p>
        <p className="text-sm leading-6 text-muted-foreground">{context.build_template_hint}</p>
      </CardContent>
    </Card>
  )
}

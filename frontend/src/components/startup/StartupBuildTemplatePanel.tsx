import type { StartupContext } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type StartupBuildTemplatePanelProps = {
  buildTemplate: StartupContext["build_template"]
}

const templateSections = [
  {
    key: "win_now",
    title: "Win-Now Stack",
    bullets: [
      "Prioritize proven starters over fragile depth swings.",
      "Move secondary picks when they buy usable weekly scoring.",
      "Avoid long-horizon rookie bets once the room starts chasing upside.",
    ],
  },
  {
    key: "balanced",
    title: "Balanced Build",
    bullets: [
      "Keep first-round startup equity intact unless the tier break is clear.",
      "Use middle rounds on ascending core players in the 24-27 range.",
      "Trade down when several comparable names are still on the board.",
    ],
  },
  {
    key: "rebuild",
    title: "Rebuild Mode",
    bullets: [
      "Collect every future-value asset the room will give you.",
      "Bias toward young insulation instead of patching this season.",
      "Let veterans slide unless the market leaves them far below cost.",
    ],
  },
] as const

export function StartupBuildTemplatePanel({
  buildTemplate,
}: StartupBuildTemplatePanelProps) {
  return (
    <Card>
      <CardHeader>
        <p className="terminal-label text-muted-foreground">Direction Build Templates</p>
        <CardTitle>Build Guide</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {templateSections.map((section) => (
          <details
            key={section.key}
            className={cn(
              "rounded-lg border border-border/50 bg-card/35 p-4",
              buildTemplate === section.key ? "border-l-2 border-accent pl-3" : "",
            )}
            open={buildTemplate === section.key}
          >
            <summary className="cursor-pointer text-base font-semibold">{section.title}</summary>
            <div className="mt-3 space-y-2">
              {section.bullets.map((bullet) => (
                <p key={bullet} className="text-sm leading-6 text-muted-foreground">
                  {bullet}
                </p>
              ))}
            </div>
          </details>
        ))}
      </CardContent>
    </Card>
  )
}

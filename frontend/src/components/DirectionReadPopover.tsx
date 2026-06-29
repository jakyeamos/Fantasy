import type { DirectionFitFlag, DirectionReadBand } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { cn, directionReadBadgeVariant, formatModelLabel } from "@/lib/utils"

function strengthVariant(strength: DirectionFitFlag["strength"]) {
  if (strength === "Strong Fit") return "default"
  if (strength === "Supporting") return "secondary"
  return "outline"
}

const directionLabelContext: Record<string, string> = {
  true_contender:
    "High weekly output with enough depth and insulation to press a real title window.",
  fragile_contender:
    "Strong current scoring, but the roster depends on a thinner, shakier weekly path.",
  fringe_playoff:
    "Competitive enough to matter now, but not strong enough to justify a blind all-in push.",
  transition_contender:
    "A roster with enough weekly strength to compete, but one that still needs to preserve flexibility instead of shoving fully in.",
  productive_struggle:
    "A roster that can still score while redirecting value toward the future.",
  one_year_punt:
    "A short-term step back built to bank future leverage instead of this season's points.",
  retool:
    "A workable core that stays active while stripping out age risk and fragile value.",
  value_retool:
    "A retool that leans even harder into liquidity, optionality, and patient value collection without fully bottoming out.",
  elite_value_accumulation:
    "A value-first build focused on optionality, liquidity, and long-term leverage.",
  soft_rebuild:
    "A future-first build that still holds enough usable production that a full tear-down would be too aggressive.",
  hard_rebuild:
    "A full reset that sacrifices current points to maximize youth and pick capital.",
}

function formatDirectionName(value: string) {
  const formatted = formatModelLabel(value) ?? value
  return formatted.replace(/\b([a-z])/g, (match) => match.toUpperCase())
}

function directionContext(value: string) {
  return (
    directionLabelContext[value] ??
    `${formatDirectionName(value)} is a nearby roster path for this team.`
  )
}

function formatDirectionReasoning({
  directionRead,
  directionLabel,
  directionAlternates,
  directionReasoning,
}: {
  directionRead: DirectionReadBand
  directionLabel: string
  directionAlternates: string[]
  directionReasoning: string | null
}) {
  if (!directionReasoning) return null
  if (!directionReasoning.startsWith("Low confidence — ")) {
    return directionReasoning
  }

  const strippedReasoning = directionReasoning.replace("Low confidence — ", "")
  const nearbyPaths =
    directionRead === "Hybrid"
      ? [directionLabel, ...directionAlternates.slice(0, 2)]
      : [directionLabel, ...directionAlternates.slice(0, 1)]
  const formattedPaths = nearbyPaths.map((label) => formatDirectionName(label)).join(", ")

  return (
    `This roster checks enough boxes across ${formattedPaths} that the model does not see one clean lane separating from the others. ` +
    "That points to keeping more optionality open rather than forcing a rigid direction too early. " +
    strippedReasoning
  )
}

export function Popout({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="pointer-events-none absolute left-0 top-full z-30 hidden w-[min(24rem,calc(100vw-2rem))] pt-3 opacity-0 transition duration-150 group-hover:block group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:block group-focus-within:pointer-events-auto group-focus-within:opacity-100">
      <div className="translate-y-2 rounded-2xl border border-border/70 bg-background/95 p-4 backdrop-blur transition duration-150 group-hover:translate-y-0 group-focus-within:translate-y-0">
        <p className="terminal-label text-muted-foreground">{title}</p>
        <div className="mt-3 space-y-3 text-sm leading-6 text-muted-foreground">
          {children}
        </div>
      </div>
    </div>
  )
}

export function HoverTrigger({
  children,
  className,
  popout,
}: {
  children: React.ReactNode
  className?: string
  popout: React.ReactNode
}) {
  return (
    <div className="group relative">
      <button
        type="button"
        className={cn("cursor-help text-left", className)}
      >
        {children}
      </button>
      {popout}
    </div>
  )
}

export function DirectionReadPopover({
  directionRead,
  directionLabel,
  directionAlternates,
  directionNote,
  directionReasoning,
  directionFitFlags,
}: {
  directionRead: DirectionReadBand
  directionLabel: string
  directionAlternates: string[]
  directionNote: string | null
  directionReasoning: string | null
  directionFitFlags: DirectionFitFlag[]
}) {
  const hasReadPopover = Boolean(directionNote) || Boolean(directionReasoning)
  const hybridAlternates =
    directionRead === "Hybrid" && directionAlternates.length > 0
      ? directionAlternates.slice(0, 2)
      : null
  const readReasoning = formatDirectionReasoning({
    directionRead,
    directionLabel,
    directionAlternates,
    directionReasoning,
  })

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {hasReadPopover ? (
          <HoverTrigger
            popout={
              <Popout title="Read Breakdown">
                {directionNote ? (
                  <p className="text-foreground">{directionNote}</p>
                ) : null}
                {readReasoning ? <p>{readReasoning}</p> : null}
              </Popout>
            }
            className="inline-flex"
          >
            <Badge
              variant={directionReadBadgeVariant(directionRead)}
              className="px-3 py-1.5 text-sm font-extrabold tracking-label-wide"
            >
              {directionRead} Read
            </Badge>
          </HoverTrigger>
        ) : (
          <Badge
            variant={directionReadBadgeVariant(directionRead)}
            className="px-3 py-1.5 text-sm font-extrabold tracking-label-wide"
          >
            {directionRead} Read
          </Badge>
        )}

        <HoverTrigger
          className="inline-flex"
          popout={
            <Popout title={formatDirectionName(directionLabel)}>
              <p>{directionContext(directionLabel)}</p>
              {directionNote ? (
                <p className="text-foreground">{directionNote}</p>
              ) : null}
              {readReasoning ? <p>{readReasoning}</p> : null}
            </Popout>
          }
        >
          <p className="font-headline text-2xl font-extrabold underline decoration-primary/35 decoration-dotted underline-offset-4">
            {formatDirectionName(directionLabel)}
          </p>
        </HoverTrigger>

        {hybridAlternates ? (
          <div className="flex flex-wrap items-center gap-2 text-sm leading-6 text-muted-foreground">
            <span className="font-semibold text-foreground">Hybrid Read:</span>
            {hybridAlternates.map((alternate, index) => (
              <div key={alternate} className="flex items-center gap-2">
                <HoverTrigger
                  className="inline-flex"
                  popout={
                    <Popout title={formatDirectionName(alternate)}>
                      <p>{directionContext(alternate)}</p>
                      <p>
                        This roster is close enough to this path that a modest shift
                        in the scorecard could move the read here.
                      </p>
                    </Popout>
                  }
                >
                  <span className="underline decoration-primary/35 decoration-dotted underline-offset-4 text-foreground">
                    {formatDirectionName(alternate)}
                  </span>
                </HoverTrigger>
                {index < hybridAlternates.length - 1 ? (
                  <span className="text-muted-foreground">,</span>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        {hasReadPopover ? (
          <p className="text-xs text-muted-foreground">
            Hover the read or title for the full explanation.
          </p>
        ) : null}
      </div>

      {directionFitFlags.length > 0 ? (
        <div className="space-y-2">
          <p className="terminal-label text-muted-foreground">Profile Flags</p>
          <div className="flex flex-wrap gap-2 xl:flex-nowrap">
            {directionFitFlags.map((flag) => (
              <HoverTrigger
                key={flag.dimension}
                popout={
                  <Popout title={flag.label}>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={strengthVariant(flag.strength)}>
                        {flag.strength}
                      </Badge>
                    </div>
                    <p>{flag.detail}</p>
                  </Popout>
                }
                className="inline-flex"
              >
                <div className="shrink-0 rounded-xl border border-border/55 bg-card/70 px-3 py-2 transition-colors hover:border-primary/35 hover:bg-card">
                  <div className="flex items-center gap-2 whitespace-nowrap">
                    <span className="text-sm font-semibold text-foreground">
                      {flag.label}
                    </span>
                    <Badge variant={strengthVariant(flag.strength)}>
                      {flag.strength}
                    </Badge>
                  </div>
                </div>
              </HoverTrigger>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

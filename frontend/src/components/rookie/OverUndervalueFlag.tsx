import { useId, useState } from "react"

import { ChevronDown, ChevronUp } from "lucide-react"

import type { SubFlag } from "@/api/types"
import { SubFlagsPanel } from "@/components/rookie/SubFlagsPanel"
import { textToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

export function OverUndervalueFlag({
  direction,
  magnitude,
  lowConfidence,
  subFlags,
}: {
  direction: "overvalued" | "undervalued" | null
  magnitude: number | null
  lowConfidence: boolean
  subFlags: SubFlag[]
}) {
  const [isOpen, setIsOpen] = useState(false)
  const panelId = useId()
  const label =
    lowConfidence || !direction || magnitude == null
      ? "Insufficient comps - low confidence"
      : `${magnitude} spots ${direction}`

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between gap-3">
        <p
          className={cn(
            "text-sm",
            direction === "overvalued" && textToneClasses.destructive,
            direction === "undervalued" && textToneClasses.success,
            (lowConfidence || !direction || magnitude == null) &&
              "text-muted-foreground",
          )}
        >
          {label}
        </p>
        {subFlags.length ? (
          <button
            type="button"
            onClick={() => setIsOpen((open) => !open)}
            aria-controls={panelId}
            aria-expanded={isOpen}
            aria-label={
              isOpen ? "Hide signal breakdown" : "Show signal breakdown"
            }
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {isOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        ) : null}
      </div>
      <SubFlagsPanel id={panelId} subFlags={subFlags} isOpen={isOpen} />
    </div>
  )
}

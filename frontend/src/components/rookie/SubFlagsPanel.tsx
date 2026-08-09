import type { SubFlag } from "@/api/types"
import { textToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

export function SubFlagsPanel({
  subFlags,
  isOpen,
  id,
}: {
  subFlags: SubFlag[]
  isOpen: boolean
  id: string
}) {
  if (!isOpen || !subFlags.length) {
    return null
  }

  return (
    <div
      id={id}
      className="mt-2 flex flex-col gap-2 rounded-md bg-muted/50 p-3 transition-all duration-150"
    >
      {subFlags.map((flag) => (
        <div
          key={`${flag.signal_name}-${flag.magnitude_str}`}
          className="flex items-center justify-between gap-3"
        >
          <span className="terminal-label text-muted-foreground">{flag.signal_name}</span>
          <span
            className={cn(
              "text-sm",
              flag.direction === "positive" && textToneClasses.success,
              flag.direction === "negative" && textToneClasses.destructive,
              flag.direction === "neutral" && textToneClasses.neutral,
            )}
          >
            {flag.magnitude_str}
          </span>
        </div>
      ))}
    </div>
  )
}

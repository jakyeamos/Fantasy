import { Minus, TrendingDown, TrendingUp } from "lucide-react"

import type { SupportingFactor } from "@/api/types"
import { textToneClasses } from "@/lib/ui-tokens"
import { cn } from "@/lib/utils"

const iconByDirection = {
  positive: TrendingUp,
  negative: TrendingDown,
  neutral: Minus,
}

const directionClass = {
  positive: textToneClasses.success,
  negative: textToneClasses.warning,
  neutral: textToneClasses.neutral,
}

export function SupportingFactorRow({ factor }: { factor: SupportingFactor }) {
  const Icon = iconByDirection[factor.direction]

  return (
    <div className="rounded-lg border border-border/40 bg-card/45 px-3 py-2">
      <div className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4", directionClass[factor.direction])} />
        <span className="text-sm font-medium">{factor.factor_name}</span>
        <span className="font-mono text-label-sm uppercase text-muted-foreground">
          {factor.magnitude}
        </span>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
        {factor.explanation}
      </p>
    </div>
  )
}

import type { FreshnessTag } from "@/api/types"
import { surfaceToneClasses, textToneClasses } from "@/lib/ui-tokens"

export function FreshnessWarningBar({ tags }: { tags: FreshnessTag[] }) {
  const staleTags = tags.filter((tag) => tag.is_stale && tag.warning)
  if (staleTags.length === 0) {
    return null
  }

  return (
    <div className="flex flex-col gap-1">
      {staleTags.map((tag) => (
        <div
          key={tag.domain}
          className={`rounded border px-3 py-2 text-xs ${surfaceToneClasses.warning} ${textToneClasses.warning}`}
        >
          <span className="font-medium">Data freshness: </span>
          {tag.warning}
        </div>
      ))}
    </div>
  )
}

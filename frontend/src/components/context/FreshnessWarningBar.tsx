import type { FreshnessTag } from "@/api/types"

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
          className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800/40 dark:bg-amber-950/20 dark:text-amber-200"
        >
          <span className="font-medium">Data freshness: </span>
          {tag.warning}
        </div>
      ))}
    </div>
  )
}

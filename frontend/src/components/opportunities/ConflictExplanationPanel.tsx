import { surfaceToneClasses, textToneClasses } from "@/lib/ui-tokens"

export function ConflictExplanationPanel({
  explanation,
}: {
  explanation: string | null
}) {
  if (!explanation) {
    return null
  }

  return (
    <div className={`mt-3 rounded-xl border p-4 ${surfaceToneClasses.warning}`}>
      <p className={`terminal-label mb-2 ${textToneClasses.warning}`}>
        SIGNAL CONFLICT
      </p>
      <p className="text-sm text-foreground">{explanation}</p>
    </div>
  )
}

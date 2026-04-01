export function ConflictExplanationPanel({
  explanation,
}: {
  explanation: string | null
}) {
  if (!explanation) {
    return null
  }

  return (
    <div className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/8 p-4">
      <p className="terminal-label mb-2 text-amber-600 dark:text-amber-300">
        SIGNAL CONFLICT
      </p>
      <p className="text-sm text-foreground">{explanation}</p>
    </div>
  )
}

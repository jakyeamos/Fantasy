import { CalendarClock } from "lucide-react"

export function CalendarEscalationLabel({ label }: { label: string | null }) {
  if (!label) {
    return null
  }

  return (
    <div className="mb-1 flex items-center gap-1.5">
      <CalendarClock className="size-3 text-primary" />
      <span className="terminal-label text-primary">{label}</span>
    </div>
  )
}

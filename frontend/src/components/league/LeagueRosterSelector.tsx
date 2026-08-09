import type { LeagueRosterOption } from "@/api/types"

function optionLabel(option: LeagueRosterOption) {
  const managerLabel =
    option.owner_display_name ?? option.owner_id ?? `Roster ${option.roster_id}`
  const record =
    option.ties > 0
      ? `${option.wins}-${option.losses}-${option.ties}`
      : `${option.wins}-${option.losses}`

  return `${managerLabel} (Roster ${option.roster_id} • ${record})`
}

export function LeagueRosterSelector({
  options,
  value,
  onChange,
  disabled,
}: {
  options: LeagueRosterOption[]
  value: number | null
  onChange: (rosterId: number | null) => void
  disabled?: boolean
}) {
  const hasOptions = options.length > 0

  return (
    <label className="min-w-[280px] space-y-2">
      <span className="terminal-label text-muted-foreground">
        Team Perspective
      </span>
      <select
        value={value ?? ""}
        onChange={(event) => onChange(Number(event.target.value) || null)}
        disabled={disabled || !hasOptions}
        className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
      >
        <option value="">
          {hasOptions ? "Select a roster" : "No rosters loaded"}
        </option>
        {options.map((option) => (
          <option key={option.roster_id} value={option.roster_id}>
            {optionLabel(option)}
          </option>
        ))}
      </select>
    </label>
  )
}

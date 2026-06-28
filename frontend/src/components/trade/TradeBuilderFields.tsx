import type {
  DashboardLeagueSummary,
  PickValue,
  TradeAsset,
  TradeRosterResult,
} from "@/api/types"
import { Button } from "@/components/ui/button"
import { AssetChip } from "@/components/trade/AssetChip"
import {
  assetDetail,
  assetKey,
  pickValueKeyFromAsset,
} from "@/lib/tradeRouteHelpers"

export function AssetBucketPanel({
  title,
  subtitle,
  buttonLabel,
  isActive,
  assets,
  leagueId,
  pickValuesByKey,
  onSelect,
  onRemove,
}: {
  title: string
  subtitle: string
  buttonLabel: string
  isActive: boolean
  assets: TradeAsset[]
  leagueId: string
  pickValuesByKey: Map<string, PickValue>
  onSelect: () => void
  onRemove: (index: number) => void
}) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        isActive
          ? "border-primary/30 bg-primary/10 shadow-[0_0_24px_-16px_rgba(123,208,255,0.8)]"
          : "border-border/45 bg-card/45"
      }`}
    >
      <div className="space-y-1">
        <p className="terminal-label text-muted-foreground">Asset bucket</p>
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      <div className="mt-4 min-h-11">
        {assets.length ? (
          <div className="flex flex-wrap gap-2">
            {assets.map((asset, index) => (
              <AssetChip
                key={`${assetKey(asset)}-${index}`}
                asset={asset}
                detail={assetDetail(asset)}
                leagueId={leagueId}
                pickValue={
                  asset.asset_type === "pick"
                    ? pickValuesByKey.get(pickValueKeyFromAsset(asset))
                    : undefined
                }
                onRemove={() => onRemove(index)}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No assets added yet.</p>
        )}
      </div>
      <Button
        className="mt-4"
        variant={isActive ? "default" : "outline"}
        onClick={onSelect}
      >
        {buttonLabel}
      </Button>
    </div>
  )
}

export function LeagueField({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (value: string) => void
  options: DashboardLeagueSummary[]
}) {
  const hasOptions = options.length > 0

  return (
    <label className="space-y-2">
      <span className="terminal-label text-muted-foreground">League</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={!hasOptions}
        className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
      >
        <option value="">
          {hasOptions ? "Select a league" : "No leagues available"}
        </option>
        {options.map((option) => (
          <option key={option.league_id} value={option.league_id}>
            {option.league_name} ({option.league_id})
          </option>
        ))}
      </select>
    </label>
  )
}

export function RosterField({
  label,
  value,
  onChange,
  options,
  placeholder,
  emptyLabel,
}: {
  label: string
  value: number
  onChange: (value: number) => void
  options: TradeRosterResult[]
  placeholder: string
  emptyLabel: string
}) {
  const hasOptions = options.length > 0

  return (
    <label className="space-y-2">
      <span className="terminal-label text-muted-foreground">{label}</span>
      <select
        value={value || ""}
        onChange={(event) => onChange(Number(event.target.value) || 0)}
        disabled={!hasOptions}
        className="h-11 w-full rounded-lg border border-border bg-card px-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
      >
        <option value="">{hasOptions ? placeholder : emptyLabel}</option>
        {options.map((option) => (
          <option key={option.roster_id} value={option.roster_id}>
            {option.roster_name} (Roster {option.roster_id})
          </option>
        ))}
      </select>
    </label>
  )
}

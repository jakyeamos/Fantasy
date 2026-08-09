import type { TradeAnalysis, TradeAnalysisOffer, TradeAsset } from "@/api/types"
import { Badge } from "@/components/ui/badge"

function assetLabel(asset: TradeAsset): string {
  if (asset.label) return asset.label
  if (asset.asset_type === "player") return asset.player_id ?? "Unknown player"
  return `${asset.pick_year ?? "?"} Round ${asset.pick_round ?? "?"}`
}

function renderAssets(assets: TradeAsset[]): string {
  return assets.length > 0 ? assets.map(assetLabel).join(", ") : "No assets"
}

function recordText(record: Record<string, unknown>, key: string): string | null {
  const value = record[key]
  if (typeof value === "string" || typeof value === "number") return String(value)
  return null
}

function statusLabel(status: TradeAnalysis["quality"]["status"]): string {
  if (status === "complete_with_degraded_evidence") return "Complete · degraded evidence"
  if (status === "blocked") return "Blocked · details required"
  return "Complete"
}

function statusClass(status: "available" | "degraded" | "unavailable"): string {
  if (status === "available") return "border-success/25 bg-success/10 text-success"
  if (status === "degraded") return "border-warning/25 bg-warning-surface text-warning"
  return "border-destructive/25 bg-destructive/10 text-destructive"
}

function offerBlock(offer: TradeAnalysisOffer) {
  return (
    <div key={offer.purpose} className="rounded-lg border border-border/35 bg-background/35 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">{offer.label}</p>
          <p className="terminal-label text-muted-foreground">{offer.purpose.replace("_", " ")}</p>
        </div>
        <Badge variant="outline">{offer.purpose.replace("_", " ")}</Badge>
      </div>
      <div className="mt-3 space-y-2 text-sm">
        <p>
          <span className="terminal-label text-muted-foreground">Send</span>{" "}
          {renderAssets(offer.send_assets)}
        </p>
        <p>
          <span className="terminal-label text-muted-foreground">Receive</span>{" "}
          {renderAssets(offer.receive_assets)}
        </p>
      </div>
      <p className="mt-3 border-t border-border/50 pt-3 text-sm text-muted-foreground">
        {offer.rationale}
      </p>
    </div>
  )
}

export function TradeAnalysisPanel({ analysis }: { analysis: TradeAnalysis | null | undefined }) {
  if (!analysis) return null

  const failedGates = Object.entries(analysis.quality.gates).filter(([, passed]) => !passed)
  const freshnessStatus = recordText(analysis.quality.freshness, "status") ?? "unknown"
  const statsHealth = analysis.quality.freshness.stats_health
  const statsStatus =
    typeof statsHealth === "object" && statsHealth !== null
      ? recordText(statsHealth as Record<string, unknown>, "status")
      : null
  const calibrationStatus = recordText(analysis.quality.calibration, "status") ?? "unavailable"
  const calibrationSample = recordText(analysis.quality.calibration, "sample_size")
  const scenarioRows = analysis.scenarios.filter(
    (scenario) => scenario.scenario_type !== "walk_away",
  )
  const ladderOffers = [
    analysis.negotiation.aggressive_open,
    analysis.negotiation.preferred_close,
    analysis.negotiation.fallback,
    analysis.negotiation.walk_away,
  ]

  return (
    <div className="space-y-4 rounded-xl border border-primary/25 bg-primary/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="terminal-label text-primary/80">Trade-analysis/1.0</p>
          <h3 className="mt-1 font-headline text-2xl font-bold">{analysis.headline}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{analysis.score_interpretation}</p>
        </div>
        <Badge
          variant="outline"
          className={
            analysis.quality.status === "blocked"
              ? "border-destructive/25 bg-destructive/10 text-destructive"
              : analysis.quality.status === "complete"
                ? "border-success/25 bg-success/10 text-success"
                : "border-warning/25 bg-warning-surface text-warning"
          }
        >
          {statusLabel(analysis.quality.status)}
        </Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-[1.3fr_1fr_1fr]">
        <div className="rounded-lg border border-border/35 bg-background/45 p-4">
          <p className="terminal-label text-muted-foreground">Model score</p>
          <div className="mt-1 flex items-end gap-2">
            <span className="font-mono text-4xl font-semibold text-foreground">
              {analysis.model_score_point.toFixed(0)}
            </span>
            <span className="pb-1 font-mono text-sm text-muted-foreground">
              {analysis.model_score_low.toFixed(0)}–{analysis.model_score_high.toFixed(0)}
            </span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-gradient-to-r from-warning/70 to-primary"
              style={{ width: `${analysis.model_score_point}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Decision score, not a claimed win percentage.
          </p>
        </div>
        <div className="rounded-lg border border-border/35 bg-background/45 p-4">
          <p className="terminal-label text-muted-foreground">Completeness</p>
          <p className="mt-1 font-mono text-2xl text-foreground">
            {analysis.quality.completeness_score.toFixed(0)}/100
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Format, assets, lineup, scenarios, and negotiation layers.
          </p>
        </div>
        <div className="rounded-lg border border-border/35 bg-background/45 p-4">
          <p className="terminal-label text-muted-foreground">Evidence reliability</p>
          <p className="mt-1 font-mono text-2xl text-foreground">
            {analysis.quality.evidence_reliability_score.toFixed(0)}/100
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Freshness, stats integrity, valuation, and calibration truth.
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-border/35 bg-background/35 p-4">
          <p className="terminal-label text-muted-foreground">Why the model leans this way</p>
          <ul className="mt-3 space-y-2 text-sm text-foreground">
            {analysis.key_reasons.map((reason) => (
              <li key={reason} className="border-l-2 border-primary/35 pl-3">
                {reason}
              </li>
            ))}
          </ul>
          <p className="mt-4 border-t border-border/50 pt-3 text-sm text-muted-foreground">
            <span className="terminal-label">Contrary case</span> {analysis.contrary_case}
          </p>
        </div>
        <div className="rounded-lg border border-border/35 bg-background/35 p-4">
          <p className="terminal-label text-muted-foreground">What changes the answer</p>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            {analysis.what_changes_the_answer.map((change) => (
              <li key={change} className="border-l-2 border-warning/35 pl-3">
                {change}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div>
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="terminal-label text-muted-foreground">Scenario range</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Each package is rescored against the same local league context.
            </p>
          </div>
          <p className="terminal-label text-muted-foreground">Current → close → floor</p>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {scenarioRows.map((scenario) => (
            <div
              key={scenario.scenario_type}
              className="rounded-lg border border-border/35 bg-background/35 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">{scenario.label}</p>
                <Badge variant="outline">{scenario.verdict.replace("_", " ")}</Badge>
              </div>
              <p className="mt-3 font-mono text-xl text-foreground">
                {scenario.score_point === null
                  ? "Not scored"
                  : `${scenario.score_low?.toFixed(0)}–${scenario.score_high?.toFixed(0)}`}
              </p>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">{scenario.rationale}</p>
              <p className="mt-2 text-xs text-muted-foreground">{scenario.assumptions.join(" ")}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="terminal-label text-muted-foreground">Before / after lineup impact</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {analysis.lineup_impacts.map((impact) => (
            <div
              key={impact.roster_id}
              className="rounded-lg border border-border/35 bg-background/35 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">{impact.roster_name}</p>
                <Badge variant="outline" className={statusClass(impact.status)}>
                  {impact.status}
                </Badge>
              </div>
              <p className="mt-3 text-sm text-foreground">
                {impact.before_title_window ?? "Unavailable"} →{" "}
                {impact.after_title_window ?? "Unavailable"}
              </p>
              <p className="mt-1 font-mono text-sm text-muted-foreground">
                {impact.before_score === null || impact.after_score === null
                  ? "No score"
                  : `${impact.before_score.toFixed(2)} → ${impact.after_score.toFixed(2)} (${impact.score_delta && impact.score_delta > 0 ? "+" : ""}${impact.score_delta?.toFixed(2)})`}
              </p>
              <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                {impact.starter_changes.map((change) => (
                  <p key={change}>{change}</p>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="terminal-label text-muted-foreground">Negotiation ladder</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {ladderOffers.map(offerBlock)}
        </div>
        <p className="mt-3 rounded-lg border border-warning/25 bg-warning-surface px-3 py-3 text-sm text-warning">
          {analysis.negotiation.walk_away_rule}
        </p>
      </div>

      <details className="rounded-lg border border-border/35 bg-background/30 p-3">
        <summary className="cursor-pointer text-sm font-semibold text-foreground">
          Evidence ledger ({analysis.assets.length} asset records)
        </summary>
        <div className="mt-3 space-y-2">
          {analysis.assets.map((asset, index) => (
            <div
              key={`${asset.side}-${asset.label}-${index}`}
              className="rounded-md border border-border/35 p-3 text-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-foreground">{asset.label}</span>
                <span className="flex items-center gap-2">
                  <span className="terminal-label text-muted-foreground">
                    {asset.side.replace("_", " ")}
                  </span>
                  <Badge variant="outline" className={statusClass(asset.evidence_status)}>
                    {asset.evidence_status}
                  </Badge>
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {asset.position ?? "Unknown position"}
                {asset.age === null ? "" : ` · age ${asset.age}`}
                {asset.current_owner_name ? ` · current owner ${asset.current_owner_name}` : ""}
                {` · ${asset.valuation_source}`}
              </p>
              {asset.evidence_notes.length ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  {asset.evidence_notes.join(" ")}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </details>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-border/35 bg-background/35 p-4 text-sm">
          <p className="terminal-label text-muted-foreground">Freshness and calibration</p>
          <p className="mt-3 text-foreground">
            Ingest: <span className="font-mono">{freshnessStatus}</span>
            {analysis.quality.freshness.age_hours !== null &&
            analysis.quality.freshness.age_hours !== undefined
              ? ` · ${String(analysis.quality.freshness.age_hours)}h old`
              : ""}
          </p>
          <p className="mt-1 text-muted-foreground">
            Stats: {statsStatus ?? "unknown"} · Calibration: {calibrationStatus}
            {calibrationSample ? ` (${calibrationSample} labeled outcomes)` : ""}
          </p>
        </div>
        <div className="rounded-lg border border-border/35 bg-background/35 p-4 text-sm">
          <p className="terminal-label text-muted-foreground">Quality gates</p>
          {failedGates.length ? (
            <p className="mt-3 text-warning">
              Needs attention: {failedGates.map(([gate]) => gate.replaceAll("_", " ")).join(", ")}
            </p>
          ) : (
            <p className="mt-3 text-success">All structural gates passed.</p>
          )}
          {analysis.quality.limitations.length ? (
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              {analysis.quality.limitations.join(" ")}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  )
}

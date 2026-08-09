import type { BriefItem } from "@/api/intelligence.generated"
import type { CommandAction, OpportunityFeedItem } from "@/api/types"

export type DecisionLane =
  | "today"
  | "lineup"
  | "waiver"
  | "trade"
  | "market"
  | "draft"
  | "portfolio"
  | "manager"
  | "watch"

export type DecisionUrgency = "today" | "this_week" | "watch" | "low"
export type DecisionConfidence = "high" | "medium" | "low"
export type FreshnessState = "fresh" | "stale" | "degraded" | "unknown"

export interface DecisionCard {
  id: string
  lane: DecisionLane
  scope: {
    leagueId?: string | null
    rosterId?: number | null
    assetIds: string[]
    managerId?: string | null
  }
  action: string
  outcome: string
  timing: string
  urgency: DecisionUrgency
  confidence: {
    band: DecisionConfidence
    score?: number
    explanation: string
  }
  acceptablePrice?: string | null
  risk: string
  invalidation: string
  evidence: string[]
  freshness: {
    state: FreshnessState
    domains: string[]
  }
  cta: {
    label: string
    destination: string
  }
}

export interface DecisionCardWire {
  id: string
  lane: Exclude<DecisionLane, "today" | "watch">
  scope: {
    league_id?: string | null
    roster_id?: number | null
    asset_ids: string[]
    manager_id?: string | null
  }
  action: string
  outcome: string
  timing: string
  urgency: DecisionUrgency
  confidence: {
    band: DecisionConfidence
    score?: number | null
    explanation: string
  }
  acceptable_price?: string | null
  risk: string
  invalidation: string
  evidence: string[]
  freshness: {
    state: FreshnessState
    domains: string[]
  }
  cta: {
    label: string
    destination: string
  }
}

function confidenceBand(value: string): DecisionConfidence {
  const normalized = value.toLowerCase()
  if (normalized === "high") return "high"
  if (normalized === "medium") return "medium"
  return "low"
}

function freshnessFromDomains(domains: string[]): DecisionCard["freshness"] {
  return {
    state: domains.length ? "stale" : "fresh",
    domains,
  }
}

export function decisionCardFromAction(action: CommandAction): DecisionCard {
  return {
    id: action.id,
    lane: action.category === "rookie_pick" ? "draft" : action.category,
    scope: {
      leagueId: action.league_id,
      rosterId: action.roster_id,
      assetIds: action.trade_suggestion
        ? [
            ...action.trade_suggestion.send_player_ids,
            ...action.trade_suggestion.receive_player_ids,
          ]
        : [],
      managerId: action.trade_suggestion?.target_manager_roster_id
        ? String(action.trade_suggestion.target_manager_roster_id)
        : null,
    },
    action: action.recommended_action,
    outcome: action.headline,
    timing: action.timing,
    urgency: action.urgency,
    confidence: {
      band: confidenceBand(action.confidence),
      explanation: action.why_now,
    },
    acceptablePrice: action.acceptable_price,
    risk: action.risk_if_wrong,
    invalidation: action.stale_domains.length
      ? `Refresh ${action.stale_domains.join(", ")} before acting.`
      : "Recheck the attached evidence before execution.",
    evidence: action.evidence,
    freshness: freshnessFromDomains(action.stale_domains),
    cta: {
      label: action.cta_label,
      destination: action.cta_destination,
    },
  }
}

export function decisionCardsFromActions(actions: CommandAction[]) {
  return actions.map(decisionCardFromAction)
}

export function decisionCardFromWire(card: DecisionCardWire): DecisionCard {
  return {
    id: card.id,
    lane: card.lane,
    scope: {
      leagueId: card.scope.league_id,
      rosterId: card.scope.roster_id,
      assetIds: card.scope.asset_ids,
      managerId: card.scope.manager_id,
    },
    action: card.action,
    outcome: card.outcome,
    timing: card.timing,
    urgency: card.urgency,
    confidence: {
      band: card.confidence.band,
      score: card.confidence.score ?? undefined,
      explanation: card.confidence.explanation,
    },
    acceptablePrice: card.acceptable_price,
    risk: card.risk,
    invalidation: card.invalidation,
    evidence: card.evidence,
    freshness: card.freshness,
    cta: card.cta,
  }
}

export function decisionCardFromBriefItem(item: BriefItem): DecisionCard {
  const isWatch = item.lane === "watch"
  return {
    id: item.item_id,
    lane: isWatch ? "watch" : "today",
    scope: {
      leagueId: item.league_id,
      rosterId: item.roster_id,
      assetIds: item.impact_summary?.affected_asset_ids ?? [],
    },
    action: item.recommended_action ?? "Review the evidence before choosing a move.",
    outcome: item.headline,
    timing: isWatch ? "Monitor until verification changes." : "Review today.",
    urgency: isWatch ? "watch" : "today",
    confidence: {
      band: item.confidence >= 0.75 ? "high" : item.confidence >= 0.5 ? "medium" : "low",
      score: item.confidence,
      explanation: item.why_it_matters,
    },
    acceptablePrice: null,
    risk: "Do not act on a watch or conflicted claim as if it were confirmed.",
    invalidation: item.invalidation,
    evidence: [item.source_summary, item.why_it_matters],
    freshness: {
      state: isWatch ? "degraded" : "fresh",
      domains: [],
    },
    cta: {
      label: item.cta_label ?? "Open evidence",
      destination: item.cta_destination ?? `/v2/events/${item.event_id}`,
    },
  }
}

export function decisionCardFromOpportunity(item: OpportunityFeedItem): DecisionCard {
  const lane = item.suggested_action === "hold" ? "watch" : "market"
  const domains = item.evidence_freshness.stale_domains
  return {
    id: `opportunity:${item.player_id}:${item.suggested_action}`,
    lane,
    scope: {
      leagueId: item.cta?.league_id,
      assetIds: [item.player_id],
    },
    action: `${item.suggested_action[0].toUpperCase()}${item.suggested_action.slice(1)} ${item.player_name}.`,
    outcome: `${item.player_name} is a ${item.suggested_action} signal`,
    timing: item.calendar_escalation_label ?? "Review before the next market window.",
    urgency: item.suggested_action === "hold" ? "watch" : "this_week",
    confidence: {
      band: confidenceBand(item.trend_confidence),
      score: item.impact_score / 100,
      explanation: item.why_summary,
    },
    acceptablePrice: `Market gap ${item.adp_gap.toFixed(1)}`,
    risk: item.conflict_explanation ?? "The market may close before the thesis is confirmed.",
    invalidation: domains.length
      ? `Refresh ${domains.join(", ")} before relying on this signal.`
      : "Recheck market and roster fit before execution.",
    evidence: [item.why_summary, `Trend confidence: ${item.trend_confidence}`],
    freshness: {
      state: domains.length ? "stale" : "fresh",
      domains,
    },
    cta: {
      label: item.cta?.label ?? "Open trade preparation",
      destination: item.cta?.href ?? "/trades",
    },
  }
}

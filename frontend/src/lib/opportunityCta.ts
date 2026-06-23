import type { OpportunityFeedItem } from "@/api/types"

export interface TradeEvaluatorOpportunityTarget {
  kind: "trade_evaluator"
  label: string
  search: {
    leagueId: string
    userRosterId?: number
    counterpartyRosterId?: number
    targetPlayerId: string
    targetPlayerName: string
    targetPlayerPosition: string
    targetPlayerRosterId?: number
  }
}

export interface ManagerDossierOpportunityTarget {
  kind: "manager_dossier"
  label: string
  params: {
    leagueId: string
    managerId: string
  }
}

export interface PlayerRankingsOpportunityTarget {
  kind: "player_rankings"
  label: string
  params: {
    leagueId: string
  }
}

export type OpportunityCtaTarget =
  | TradeEvaluatorOpportunityTarget
  | ManagerDossierOpportunityTarget
  | PlayerRankingsOpportunityTarget

export function buildOpportunityCtaTarget(
  item: OpportunityFeedItem,
): OpportunityCtaTarget | null {
  const cta = item.cta
  if (!cta?.league_id) {
    return null
  }

  if (cta.destination === "trade_evaluator") {
    return {
      kind: "trade_evaluator",
      label: cta.label,
      search: {
        leagueId: cta.league_id,
        userRosterId: cta.user_roster_id ?? undefined,
        counterpartyRosterId: cta.manager_roster_id ?? undefined,
        targetPlayerId: item.player_id,
        targetPlayerName: item.player_name,
        targetPlayerPosition: item.position,
        targetPlayerRosterId: cta.target_player_roster_id ?? undefined,
      },
    }
  }

  if (cta.destination === "manager_dossier" && cta.manager_roster_id) {
    return {
      kind: "manager_dossier",
      label: cta.label,
      params: {
        leagueId: cta.league_id,
        managerId: String(cta.manager_roster_id),
      },
    }
  }

  return {
    kind: "player_rankings",
    label: cta.label,
    params: {
      leagueId: cta.league_id,
    },
  }
}

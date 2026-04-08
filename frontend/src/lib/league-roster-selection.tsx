import { createContext, useContext, type ReactNode } from "react"

import type { LeagueDetailResponse, LeagueRosterOption } from "@/api/types"

const STORAGE_PREFIX = "fantasy:selected-roster:"

function storageKey(leagueId: string) {
  return `${STORAGE_PREFIX}${leagueId}`
}

export function readStoredLeagueRosterId(leagueId: string): number | null {
  if (typeof window === "undefined") {
    return null
  }

  const raw = window.localStorage.getItem(storageKey(leagueId))
  if (!raw) {
    return null
  }

  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export function persistStoredLeagueRosterId(leagueId: string, rosterId: number | null) {
  if (typeof window === "undefined") {
    return
  }

  if (rosterId && rosterId > 0) {
    window.localStorage.setItem(storageKey(leagueId), String(rosterId))
    return
  }

  window.localStorage.removeItem(storageKey(leagueId))
}

export interface LeagueRosterSelectionContextValue {
  leagueId: string
  requestedRosterId: number | null
  setRequestedRosterId: (rosterId: number | null) => void
  rosterOptions: LeagueRosterOption[]
  league: LeagueDetailResponse
}

const LeagueRosterSelectionContext =
  createContext<LeagueRosterSelectionContextValue | null>(null)

export function LeagueRosterSelectionProvider({
  value,
  children,
}: {
  value: LeagueRosterSelectionContextValue
  children: ReactNode
}) {
  return (
    <LeagueRosterSelectionContext.Provider value={value}>
      {children}
    </LeagueRosterSelectionContext.Provider>
  )
}

export function useLeagueRosterSelection() {
  const value = useContext(LeagueRosterSelectionContext)
  if (!value) {
    throw new Error("useLeagueRosterSelection must be used within a LeagueRosterSelectionProvider")
  }
  return value
}

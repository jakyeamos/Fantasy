import { Link } from "@tanstack/react-router"

import type { LeagueDetailResponse } from "@/api/types"
import { ConcentrationAlertBanner } from "@/components/ConcentrationAlertBanner"
import { RisersFallersList } from "@/components/RisersFallersList"
import { buttonClasses } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function LeagueOverviewPanels({
  league,
  leagueId,
}: {
  league: LeagueDetailResponse
  leagueId: string
}) {
  return (
    <>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <p className="terminal-label text-muted-foreground">
              Exploit windows
            </p>
          </CardHeader>
          <CardContent>
            <p className="font-headline text-3xl font-extrabold tracking-tight">
              {league.exploit_windows.length}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Managers currently showing live behavioral triggers.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <p className="terminal-label text-muted-foreground">
              Market movement
            </p>
          </CardHeader>
          <CardContent>
            <p className="font-headline text-3xl font-extrabold tracking-tight">
              {league.risers.length + league.fallers.length}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Player valuation changes surfaced in the latest ingest.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <p className="terminal-label text-muted-foreground">
              Active Roster
            </p>
          </CardHeader>
          <CardContent>
            <p className="font-headline text-3xl font-extrabold tracking-tight">
              {league.user_roster_name ?? "No roster selected"}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Switching the selector updates every league tab from this team&apos;s
              perspective.
            </p>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle>Section Guide</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              Keep overview high-level, then use the dedicated tabs for league
              comparison, roster actions, and league operations.
            </p>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Link
            to="/league/$leagueId/comparison"
            params={{ leagueId }}
            className={buttonClasses({ variant: "outline" })}
          >
            Open Comparison
          </Link>
          <Link
            to="/league/$leagueId/roster-moves"
            params={{ leagueId }}
            className={buttonClasses({ variant: "outline" })}
          >
            Open Roster Moves
          </Link>
          <Link
            to="/league/$leagueId/league-ops"
            params={{ leagueId }}
            className={buttonClasses({ variant: "outline" })}
          >
            Open League Ops
          </Link>
          <Link
            to="/league/$leagueId/managers"
            params={{ leagueId }}
            className={buttonClasses({ variant: "outline" })}
          >
            Review Dossiers
          </Link>
          <Link
            to="/trades"
            search={{
              leagueId,
              userRosterId: league.user_roster_id ?? undefined,
            }}
            className={buttonClasses({ variant: "outline" })}
          >
            Open Trade Lab
          </Link>
        </CardContent>
      </Card>

      <ConcentrationAlertBanner
        leagueId={leagueId}
        ownerId={league.user_owner_id}
        userRosterPlayerIds={league.user_roster_player_ids}
      />
      <RisersFallersList risers={league.risers} fallers={league.fallers} />
    </>
  )
}

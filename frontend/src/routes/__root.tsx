import { useEffect, useMemo, useState } from "react"
import {
  Activity,
  ArrowLeftRight,
  BarChart3,
  Bell,
  Briefcase,
  ChevronRight,
  History,
  LayoutDashboard,
  Menu,
  Moon,
  Search,
  Star,
  Sun,
  Terminal,
  Users,
} from "lucide-react"
import {
  Outlet,
  createRootRouteWithContext,
  useLocation,
  useNavigate,
} from "@tanstack/react-router"
import type { QueryClient } from "@tanstack/react-query"
import { useQuery } from "@tanstack/react-query"

import { dashboardSummaryOptions } from "@/api/queries"
import { Button } from "@/components/ui/button"
import {
  SYSTEM_THEME_MEDIA_QUERY,
  THEME_STORAGE_KEY,
  applyTheme,
  getPreferredTheme,
  getStoredTheme,
  persistTheme,
  type Theme,
} from "@/lib/theme"

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient
}>()({
  component: RootLayout,
})

function RootLayout() {
  const [theme, setTheme] = useState<Theme>(() => getPreferredTheme())
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const dashboardQuery = useQuery(dashboardSummaryOptions)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    const mediaQuery = window.matchMedia(SYSTEM_THEME_MEDIA_QUERY)

    const handleSystemThemeChange = (event: MediaQueryListEvent) => {
      if (!getStoredTheme()) {
        setTheme(event.matches ? "dark" : "light")
      }
    }

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY) {
        setTheme(getPreferredTheme())
      }
    }

    mediaQuery.addEventListener("change", handleSystemThemeChange)
    window.addEventListener("storage", handleStorageChange)

    return () => {
      mediaQuery.removeEventListener("change", handleSystemThemeChange)
      window.removeEventListener("storage", handleStorageChange)
    }
  }, [])

  useEffect(() => {
    setMobileNavOpen(false)
  }, [location.pathname])

  const isDark = theme === "dark"
  const primaryLeagueId = dashboardQuery.data?.[0]?.league_id ?? null

  const routeMeta = useMemo(() => {
    const pathname = location.pathname

    if (pathname === "/") {
      return {
        title: "Dashboard",
        subtitle: "League overview",
      }
    }

    if (pathname === "/portfolio") {
      return {
        title: "Portfolio",
        subtitle: "Cross-league risk",
      }
    }

    if (pathname === "/opportunities") {
      return {
        title: "Opportunity Feed",
        subtitle: "Market inefficiencies",
      }
    }

    if (pathname === "/trades") {
      return {
        title: "Trade Evaluator",
        subtitle: "Deal intelligence",
      }
    }

    if (pathname === "/draft-room") {
      return {
        title: "Draft Room",
        subtitle: "Live pick guidance",
      }
    }

    if (pathname.includes("/rookie-board")) {
      return {
        title: "Rookie Board",
        subtitle: "Tiered class view",
      }
    }

    if (pathname.includes("/managers/")) {
      return {
        title: "Manager Dossier",
        subtitle: "Behavioral profile",
      }
    }

    if (pathname.includes("/roster-moves")) {
      return {
        title: "Roster Moves",
        subtitle: "Actionable roster hygiene",
      }
    }

    if (pathname.includes("/comparison")) {
      return {
        title: "Comparison",
        subtitle: "League standing context",
      }
    }

    if (pathname.includes("/league-ops")) {
      return {
        title: "League Ops",
        subtitle: "Picks, rules, and taxi setup",
      }
    }

    if (pathname.endsWith("/managers")) {
      return {
        title: "Managers",
        subtitle: "League trade profiles",
      }
    }

    if (pathname.startsWith("/league/")) {
      return {
        title: "League Briefing",
        subtitle: "Direction and market notes",
      }
    }

    return {
      title: "Dynasty Intelligence",
      subtitle: "Front-office cockpit",
    }
  }, [location.pathname])

  const latestSnapshot = useMemo(() => {
    const snapshot = dashboardQuery.data
      ?.map((league) => league.last_snapshot_at)
      .filter(Boolean)
      .sort()
      .at(-1)

    if (!snapshot) {
      return "No snapshot"
    }

    const minutes = Math.max(1, Math.round((Date.now() - Date.parse(snapshot)) / 60_000))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.round(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    return new Date(snapshot).toLocaleDateString()
  }, [dashboardQuery.data])

  const toggleTheme = () => {
    setTheme((currentTheme) => {
      const nextTheme = currentTheme === "dark" ? "light" : "dark"
      persistTheme(nextTheme)
      return nextTheme
    })
  }

  const navItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
      active: location.pathname === "/",
      action: () => void navigate({ to: "/" }),
      disabled: false,
    },
    {
      id: "managers",
      label: "Managers",
      icon: Users,
      active: location.pathname.includes("/managers"),
      action: () => {
        if (!primaryLeagueId) return
        void navigate({
          to: "/league/$leagueId/managers",
          params: { leagueId: primaryLeagueId },
        })
      },
      disabled: !primaryLeagueId,
    },
    {
      id: "portfolio",
      label: "Portfolio",
      icon: Briefcase,
      active: location.pathname === "/portfolio",
      action: () => void navigate({ to: "/portfolio" }),
      disabled: false,
    },
    {
      id: "trade",
      label: "Trade Lab",
      icon: ArrowLeftRight,
      active: location.pathname === "/trades",
      action: () => void navigate({ to: "/trades" }),
      disabled: false,
    },
    {
      id: "rookie",
      label: "Rookie Board",
      icon: Star,
      active: location.pathname.includes("/rookie-board"),
      action: () => {
        if (!primaryLeagueId) return
        void navigate({
          to: "/league/$leagueId/rookie-board",
          params: { leagueId: primaryLeagueId },
        })
      },
      disabled: !primaryLeagueId,
    },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="glass-panel hidden w-72 shrink-0 border-r border-border/40 xl:flex xl:flex-col">
          <div className="border-b border-border/30 px-6 py-6">
            <button
              type="button"
              className="flex items-center gap-3 text-left"
              onClick={() => void navigate({ to: "/" })}
            >
              <div className="flex size-10 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary">
                <Terminal className="size-5" />
              </div>
              <div>
                <p className="font-headline text-lg font-extrabold tracking-tight">
                  Dynasty Intelligence
                </p>
                <p className="terminal-label text-primary/80">
                  Front-Office Cockpit
                </p>
              </div>
            </button>
          </div>

          <nav className="flex-1 space-y-1 px-4 py-5">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                disabled={item.disabled}
                onClick={item.action}
                className={`flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left ${
                  item.active
                    ? "border-primary/30 bg-primary/10 text-primary shadow-[0_0_24px_-16px_rgba(123,208,255,0.85)]"
                    : "border-transparent text-muted-foreground hover:border-border/60 hover:bg-card/55 hover:text-foreground"
                } ${item.disabled ? "cursor-not-allowed opacity-45" : ""}`}
              >
                <item.icon className="size-4" />
                <span className="font-label text-[11px] uppercase tracking-[0.16em]">
                  {item.label}
                </span>
              </button>
            ))}
          </nav>

          <div className="space-y-4 border-t border-border/30 px-4 py-5">
            <div className="rounded-xl border border-border/40 bg-card/50 p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="terminal-label text-muted-foreground">
                  System Status
                </span>
                <span className="terminal-label text-accent">Synced</span>
              </div>
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span>Tracked leagues</span>
                  <span className="font-mono text-foreground">
                    {dashboardQuery.data?.length ?? 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Last snapshot</span>
                  <span className="font-mono text-foreground">{latestSnapshot}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-border/40 bg-card/50 p-4">
              <div className="flex size-10 items-center justify-center rounded-md border border-primary/25 bg-primary/10 font-headline text-sm font-bold text-primary">
                JY
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">Analyst Desk</p>
                <p className="terminal-label text-muted-foreground">Proven</p>
              </div>
            </div>
          </div>
        </aside>

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="glass-panel sticky top-0 z-40 border-b border-border/40">
            <div className="flex flex-col gap-4 px-5 py-4 lg:px-8">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 xl:hidden">
                  <button
                    type="button"
                    className="flex size-10 items-center justify-center rounded-md border border-border/60 bg-card/50 text-muted-foreground"
                    onClick={() => setMobileNavOpen((open) => !open)}
                    aria-label="Toggle navigation"
                  >
                    <Menu className="size-4" />
                  </button>
                  <div>
                    <p className="font-headline text-base font-bold tracking-tight">
                      Dynasty Intelligence
                    </p>
                    <p className="terminal-label text-primary/75">Front-Office Cockpit</p>
                  </div>
                </div>

                <div className="hidden min-w-0 flex-1 xl:block">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <span className="terminal-label">Terminal</span>
                    <ChevronRight className="size-3" />
                    <span className="terminal-label text-primary">{routeMeta.title}</span>
                    <ChevronRight className="size-3" />
                    <span className="terminal-label">{routeMeta.subtitle}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="relative hidden md:block">
                    <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search assets..."
                      className="h-10 w-56 pl-10 pr-3 text-[11px] uppercase tracking-[0.14em] lg:w-72"
                    />
                  </div>

                  <div className="hidden items-center gap-2 lg:flex">
                    <button
                      type="button"
                      className="flex size-10 items-center justify-center rounded-md border border-border/60 bg-card/50 text-muted-foreground hover:text-primary"
                      aria-label="Alerts"
                    >
                      <Bell className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="flex size-10 items-center justify-center rounded-md border border-border/60 bg-card/50 text-muted-foreground hover:text-primary"
                      aria-label="History"
                    >
                      <History className="size-4" />
                    </button>
                    <button
                      type="button"
                      className="flex size-10 items-center justify-center rounded-md border border-border/60 bg-card/50 text-muted-foreground hover:text-primary"
                      aria-label="Metrics"
                    >
                      <BarChart3 className="size-4" />
                    </button>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="w-10 px-0"
                    onClick={toggleTheme}
                    aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
                    title={isDark ? "Switch to light mode" : "Switch to dark mode"}
                  >
                    {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
                  </Button>
                </div>
              </div>

              <div className="hidden items-center justify-between xl:flex">
                <div>
                  <h1 className="font-headline text-3xl font-extrabold tracking-tight">
                    {routeMeta.title}
                  </h1>
                  <p className="mt-1 text-sm text-muted-foreground">{routeMeta.subtitle}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg border border-border/40 bg-card/50 px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Activity className="size-3.5 text-accent" />
                      <span className="terminal-label text-muted-foreground">
                        Active Sync
                      </span>
                    </div>
                    <p className="mt-1 font-mono text-sm text-foreground">
                      {dashboardQuery.data?.length ?? 0} leagues tracked
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-card/50 px-3 py-2">
                    <span className="terminal-label text-muted-foreground">
                      Last Snapshot
                    </span>
                    <p className="mt-1 font-mono text-sm text-foreground">{latestSnapshot}</p>
                  </div>
                </div>
              </div>

              {mobileNavOpen ? (
                <div className="grid gap-2 border-t border-border/30 pt-4 xl:hidden">
                  {navItems.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      disabled={item.disabled}
                      onClick={item.action}
                      className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left ${
                        item.active
                          ? "border-primary/30 bg-primary/10 text-primary"
                          : "border-border/40 bg-card/50 text-muted-foreground"
                      } ${item.disabled ? "cursor-not-allowed opacity-45" : ""}`}
                    >
                      <item.icon className="size-4" />
                      <span className="font-label text-[11px] uppercase tracking-[0.16em]">
                        {item.label}
                      </span>
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </header>

          <main className="flex-1 px-5 py-6 lg:px-8 lg:py-8">
            <div className="mx-auto w-full max-w-[1600px]">
              <Outlet />
            </div>
          </main>

          <footer className="glass-panel border-t border-border/40 px-5 py-3 text-[10px] uppercase tracking-[0.18em] text-muted-foreground lg:px-8">
            <div className="mx-auto flex max-w-[1600px] flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-3">
                <span className="font-mono">Terminal status: operational</span>
                <span className="hidden md:inline">|</span>
                <span className="font-mono">Latest snapshot: {latestSnapshot}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono">
                  Leagues: {dashboardQuery.data?.length ?? 0}
                </span>
                <span className="hidden md:inline">|</span>
                <span className="font-mono">{routeMeta.title}</span>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  )
}

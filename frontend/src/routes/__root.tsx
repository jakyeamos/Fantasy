import { useEffect, useMemo, useState } from "react"
import {
  Activity,
  BookOpen,
  Briefcase,
  Database,
  LayoutDashboard,
  Menu,
  Moon,
  Settings2,
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

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    const mediaQuery = window.matchMedia(SYSTEM_THEME_MEDIA_QUERY)
    const handleSystemThemeChange = (event: MediaQueryListEvent) => {
      if (!getStoredTheme()) setTheme(event.matches ? "dark" : "light")
    }
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY) setTheme(getPreferredTheme())
    }
    mediaQuery.addEventListener("change", handleSystemThemeChange)
    window.addEventListener("storage", handleStorageChange)
    return () => {
      mediaQuery.removeEventListener("change", handleSystemThemeChange)
      window.removeEventListener("storage", handleStorageChange)
    }
  }, [])

  useEffect(() => setMobileNavOpen(false), [location.pathname])

  const routeMeta = useMemo(() => {
    const pathname = location.pathname
    if (pathname === "/")
      return { title: "Today", subtitle: "Prepared decisions" }
    if (pathname === "/leagues" || pathname.startsWith("/league/"))
      return { title: "Leagues", subtitle: "Briefing and roster context" }
    if (pathname === "/portfolio")
      return { title: "Portfolio", subtitle: "Cross-league exposure" }
    if (
      pathname === "/research" ||
      pathname === "/opportunities" ||
      pathname.includes("rookie-board") ||
      pathname === "/draft-room"
    )
      return { title: "Research", subtitle: "Evidence and model context" }
    if (pathname === "/operations")
      return {
        title: "Operations",
        subtitle: "Health, freshness, and rollback",
      }
    if (pathname === "/trades")
      return {
        title: "Trade Preparation",
        subtitle: "Manual execution boundary",
      }
    return { title: "Dynasty Intelligence", subtitle: "Local front office" }
  }, [location.pathname])

  const isDark = theme === "dark"
  const toggleTheme = () => {
    setTheme((currentTheme) => {
      const nextTheme = currentTheme === "dark" ? "light" : "dark"
      persistTheme(nextTheme)
      return nextTheme
    })
  }

  const navItems = [
    {
      id: "today",
      label: "Today",
      icon: LayoutDashboard,
      active: location.pathname === "/",
      action: () => void navigate({ to: "/" }),
    },
    {
      id: "leagues",
      label: "Leagues",
      icon: Users,
      active:
        location.pathname === "/leagues" ||
        location.pathname.startsWith("/league/"),
      action: () => void navigate({ to: "/leagues" }),
    },
    {
      id: "portfolio",
      label: "Portfolio",
      icon: Briefcase,
      active: location.pathname === "/portfolio",
      action: () => void navigate({ to: "/portfolio" }),
    },
    {
      id: "research",
      label: "Research",
      icon: BookOpen,
      active:
        location.pathname === "/research" ||
        location.pathname === "/opportunities" ||
        location.pathname === "/draft-room",
      action: () => void navigate({ to: "/research" }),
    },
    {
      id: "operations",
      label: "Operations",
      icon: Settings2,
      active: location.pathname === "/operations",
      action: () => void navigate({ to: "/operations" }),
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
                <p className="font-label text-label-xs uppercase tracking-label text-primary/80">
                  Local front office
                </p>
              </div>
            </button>
          </div>
          <nav
            className="flex-1 space-y-1 px-4 py-5"
            aria-label="Primary navigation"
          >
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={item.action}
                className={`flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left ${item.active ? "border-primary/30 bg-primary/10 text-primary" : "border-transparent text-muted-foreground hover:border-border/60 hover:bg-card/55 hover:text-foreground"}`}
              >
                <item.icon className="size-4" />
                <span className="font-label text-label-sm uppercase tracking-label">
                  {item.label}
                </span>
              </button>
            ))}
            <button
              type="button"
              onClick={() => void navigate({ to: "/trades" })}
              className={`flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left ${location.pathname === "/trades" ? "border-primary/30 bg-primary/10 text-primary" : "border-transparent text-muted-foreground hover:border-border/60 hover:bg-card/55 hover:text-foreground"}`}
            >
              <ArrowLeftRightIcon />
              <span className="font-label text-label-sm uppercase tracking-label">
                Trade prep
              </span>
            </button>
          </nav>
          <div className="space-y-4 border-t border-border/30 px-4 py-5">
            <div className="rounded-xl border border-border/40 bg-card/50 p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-label text-label-xs uppercase tracking-label text-muted-foreground">
                  System status
                </span>
                <span className="font-label text-label-xs uppercase tracking-label text-accent">
                  Local
                </span>
              </div>
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span>Data scope</span>
                  <span className="font-mono text-foreground">Page-owned</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Actions</span>
                  <span className="font-mono text-foreground">Manual</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl border border-border/40 bg-card/50 p-4">
              <div className="flex size-10 items-center justify-center rounded-md border border-primary/25 bg-primary/10 font-headline text-sm font-bold text-primary">
                JY
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">
                  Analyst desk
                </p>
                <p className="font-label text-label-xs uppercase tracking-label text-muted-foreground">
                  Owner controlled
                </p>
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
                    <p className="font-headline text-base font-bold">
                      Dynasty Intelligence
                    </p>
                    <p className="font-label text-label-xs uppercase tracking-label text-primary/75">
                      Local front office
                    </p>
                  </div>
                </div>
                <div className="hidden min-w-0 flex-1 xl:block">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <span className="font-label text-label-xs uppercase tracking-label">
                      Front office
                    </span>
                    <span>/</span>
                    <span className="font-label text-label-xs uppercase tracking-label text-primary">
                      {routeMeta.title}
                    </span>
                    <span>/</span>
                    <span className="font-label text-label-xs uppercase tracking-label">
                      {routeMeta.subtitle}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
                    <Activity className="size-3.5 text-accent" /> Data loads by
                    destination
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="w-10 px-0"
                    onClick={toggleTheme}
                    aria-label={
                      isDark ? "Switch to light mode" : "Switch to dark mode"
                    }
                  >
                    {isDark ? (
                      <Sun className="size-4" />
                    ) : (
                      <Moon className="size-4" />
                    )}
                  </Button>
                </div>
              </div>
              <div className="hidden items-center justify-between xl:flex">
                <div>
                  <h1 className="font-headline text-3xl font-extrabold tracking-tight">
                    {routeMeta.title}
                  </h1>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {routeMeta.subtitle}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg border border-border/40 bg-card/50 px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Database className="size-3.5 text-accent" />
                      <span className="font-label text-label-xs uppercase tracking-label text-muted-foreground">
                        Storage
                      </span>
                    </div>
                    <p className="mt-1 font-mono text-sm text-foreground">
                      Local DuckDB
                    </p>
                  </div>
                  <div className="rounded-lg border border-border/40 bg-card/50 px-3 py-2">
                    <span className="font-label text-label-xs uppercase tracking-label text-muted-foreground">
                      Execution
                    </span>
                    <p className="mt-1 font-mono text-sm text-foreground">
                      Manual only
                    </p>
                  </div>
                </div>
              </div>
              {mobileNavOpen ? (
                <nav
                  className="grid gap-2 border-t border-border/30 pt-4 xl:hidden"
                  aria-label="Mobile navigation"
                >
                  {navItems.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={item.action}
                      className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-left ${item.active ? "border-primary/30 bg-primary/10 text-primary" : "border-border/40 bg-card/50 text-muted-foreground"}`}
                    >
                      <item.icon className="size-4" />
                      <span className="font-label text-label-sm uppercase tracking-label">
                        {item.label}
                      </span>
                    </button>
                  ))}
                </nav>
              ) : null}
            </div>
          </header>
          <main className="flex-1 px-5 py-6 lg:px-8 lg:py-8">
            <div className="mx-auto w-full max-w-[1600px]">
              <Outlet />
            </div>
          </main>
          <footer className="glass-panel border-t border-border/40 px-5 py-3 font-label text-label-xs uppercase tracking-label-wide text-muted-foreground lg:px-8">
            <div className="mx-auto flex max-w-[1600px] flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <span className="font-mono">
                Local-only · manual execution boundary
              </span>
              <span className="font-mono">
                {routeMeta.title} · evidence stays attached
              </span>
            </div>
          </footer>
        </div>
      </div>
    </div>
  )
}

function ArrowLeftRightIcon() {
  return (
    <span
      className="flex size-4 items-center justify-center text-sm"
      aria-hidden="true"
    >
      ↔
    </span>
  )
}

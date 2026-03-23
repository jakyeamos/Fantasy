import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { Link, Outlet, createRootRouteWithContext } from "@tanstack/react-router"
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

  const isDark = theme === "dark"

  const toggleTheme = () => {
    setTheme((currentTheme) => {
      const nextTheme = currentTheme === "dark" ? "light" : "dark"
      persistTheme(nextTheme)
      return nextTheme
    })
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-border/70 bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
              Dynasty Intelligence
            </p>
            <h1 className="text-lg font-semibold">League Dashboard</h1>
          </div>
          <nav className="flex flex-wrap items-center justify-end gap-3 text-sm text-muted-foreground">
            <Link to="/" className="hover:text-foreground">
              Dashboard
            </Link>
            <Link to="/portfolio" className="hover:text-foreground">
              Portfolio
            </Link>
            <Link to="/trades" className="hover:text-foreground">
              Evaluate Trade
            </Link>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-9 px-0"
              onClick={toggleTheme}
              aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}

import { Link, Outlet, createRootRouteWithContext } from "@tanstack/react-router"
import type { QueryClient } from "@tanstack/react-query"

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient
}>()({
  component: RootLayout,
})

function RootLayout() {
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
          <nav className="flex items-center gap-4 text-sm text-muted-foreground">
            <Link to="/" className="hover:text-foreground">
              Dashboard
            </Link>
            <Link to="/trades" className="hover:text-foreground">
              Evaluate Trade
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}

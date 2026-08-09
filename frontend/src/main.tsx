import React from "react"
import ReactDOM from "react-dom/client"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { RouterProvider, createRouter } from "@tanstack/react-router"

import { applyTheme, getPreferredTheme } from "@/lib/theme"
import { routeTree } from "./routeTree.gen"
import "./index.css"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const router = createRouter({
  routeTree,
  context: { queryClient },
})

applyTheme(getPreferredTheme())

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      {import.meta.env.DEV ? (
        <div className="hidden sm:block">
          <ReactQueryDevtools initialIsOpen={false} />
        </div>
      ) : null}
    </QueryClientProvider>
  </React.StrictMode>,
)

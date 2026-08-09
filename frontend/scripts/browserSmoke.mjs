import { existsSync } from "node:fs"

import { chromium } from "playwright"

const appUrl = process.env.APP_URL ?? "http://127.0.0.1:5173"
const readyTimeoutMs = Number(process.env.SMOKE_READY_TIMEOUT_MS ?? 15_000)
const viewportWidth = Number(process.env.SMOKE_VIEWPORT_WIDTH ?? 1440)
const opportunityApiPattern = "**/api/opportunities*"
const defaultChrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
const executablePath =
  process.env.BROWSER_EXECUTABLE_PATH ?? (existsSync(defaultChrome) ? defaultChrome : undefined)

function route(path, expected, fixture = null) {
  return { path, expected, fixture }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function discoverLeague(request) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    try {
      const response = await request.get(`${appUrl}/api/dashboard/summary`, {
        timeout: 30_000,
      })
      if (response.ok()) {
        const leagues = await response.json()
        const first = Array.isArray(leagues) ? leagues[0] : null
        if (first?.league_id) {
          return {
            leagueId: String(first.league_id),
            rosterId: first.user_roster_id ? Number(first.user_roster_id) : null,
          }
        }
      }
    } catch {
      // Retry while local dev refresh finishes warming the DuckDB-backed summary.
    }
    await sleep(1_000)
  }
  return null
}

function buildRoutes(league) {
  const routes = [
    route("/", ["Today", "Decide what matters today"]),
    route("/leagues", ["Leagues", "Choose the roster that needs a decision"]),
    route("/research", ["Research", "Evidence before universal rankings"]),
    route("/operations", ["Operations", "Know what is healthy"]),
    route("/opportunities", ["Opportunity Feed", "Showing"]),
    route("/portfolio", ["Portfolio", "Player Exposure"]),
    route("/trades", ["Trade Preparation", "Evaluate"]),
    route("/draft-room", ["Draft Room"]),
  ]
  if (league) {
    const roster = league.rosterId ? `?rosterId=${league.rosterId}` : ""
    routes.push(
      route(`/league/${league.leagueId}${roster}`, ["League Briefing"]),
      route(`/league/${league.leagueId}/waivers${roster}`, ["Waiver"]),
      route(`/league/${league.leagueId}/managers`, ["Manager"]),
      route(`/league/${league.leagueId}/rookie-board`, ["Rookie"]),
    )
  }
  routes.push(
    route(
      "/opportunities?smokeState=empty",
      ["Opportunity Feed", "No Opportunities Available"],
      "empty",
    ),
    route("/opportunities?smokeState=stale", ["Opportunity Feed", "Stale weekly data"], "stale"),
    route(
      "/opportunities?smokeState=degraded",
      ["Opportunity Feed", "Opportunity Feed Degraded"],
      "degraded",
    ),
    route(
      "/opportunities?smokeState=error",
      ["Opportunity Feed", "Opportunity Feed Unavailable"],
      "error",
    ),
  )
  return routes
}

function fixtureItem() {
  return {
    player_id: "smoke-player",
    player_name: "Smoke Player",
    position: "WR",
    trend_label: "will_rise",
    trend_confidence: "HIGH",
    adp_gap: 4,
    suggested_action: "buy",
    availability: "available",
    impact_score: 80,
    why_summary: "Fixture opportunity for browser state verification.",
    owned_in_leagues: [],
    similar_players: [],
    evidence_freshness: {
      is_stale: true,
      stale_domains: ["weekly"],
      warnings: ["Fixture data is stale."],
    },
    conflict_explanation: null,
    calendar_escalated: false,
    calendar_escalation_label: null,
    cta: null,
    weekly_fit: {
      position: "WR",
      player_name: "Smoke Player",
      gap_to_title_target: 1.5,
      is_stale: true,
      stale_domains: ["weekly"],
    },
  }
}

async function installFixture(page, fixture) {
  if (!fixture) return

  await page.route(opportunityApiPattern, async (route) => {
    if (fixture === "error") {
      await route.abort("failed")
      return
    }

    const items = fixture === "stale" ? [fixtureItem()] : []
    const payload = {
      items,
      total: items.length,
      computed_at: "2026-08-01T00:00:00Z",
      status: fixture === "degraded" ? "degraded" : "ok",
      degraded_reason: fixture === "degraded" ? "Fixture source is partially unavailable." : null,
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    })
  })
}

function trackConsoleProblems(page, consoleProblems, ignoredFragments = []) {
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      const entry = `${message.type()}: ${message.text()}`
      if (!ignoredFragments.some((fragment) => entry.includes(fragment))) {
        consoleProblems.push(entry)
      }
    }
  })
  page.on("pageerror", (error) => {
    consoleProblems.push(`pageerror: ${error.message}`)
  })
}

async function assertRoute(context, target, consoleProblems) {
  const page = await context.newPage()
  trackConsoleProblems(page, consoleProblems, target.fixture === "error" ? ["net::ERR_FAILED"] : [])
  await installFixture(page, target.fixture)
  try {
    await page.goto(`${appUrl}${target.path}`, {
      waitUntil: "domcontentloaded",
      timeout: 30_000,
    })
    try {
      await page.waitForFunction(
        (expected) =>
          expected.every((text) =>
            document.body.innerText.toLowerCase().includes(text.toLowerCase()),
          ),
        target.expected,
        { timeout: readyTimeoutMs },
      )
    } catch (error) {
      const bodyText = await page.locator("body").innerText()
      throw new Error(
        `${target.path} readiness failed: ${error.message}\nbodyStart=${bodyText.slice(0, 500)}\nconsoleProblems=${consoleProblems.slice(-8).join(" | ")}`,
      )
    }
    const bodyText = await page.locator("body").innerText({ timeout: 10_000 })
    const normalizedBody = bodyText.toLowerCase()
    const missing = target.expected.filter((text) => !normalizedBody.includes(text.toLowerCase()))
    const overlayCount = await page
      .locator("text=/Plugin: vite|Failed to load|Unhandled|TypeError|ReferenceError/i")
      .count()
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
    const viewportWidth = await page.evaluate(() => window.innerWidth)
    if (missing.length || overlayCount > 0 || scrollWidth > viewportWidth + 4) {
      throw new Error(
        JSON.stringify(
          {
            path: target.path,
            missing,
            overlayCount,
            scrollWidth,
            viewportWidth,
            bodyStart: bodyText.slice(0, 500),
          },
          null,
          2,
        ),
      )
    }
  } finally {
    if (target.fixture) {
      await page.unroute(opportunityApiPattern)
    }
    await page.close()
  }
}

async function run() {
  const launchOptions = executablePath ? { headless: true, executablePath } : { headless: true }
  const browser = await chromium.launch(launchOptions)
  const context = await browser.newContext({
    viewport: { width: viewportWidth, height: 1100 },
  })
  const page = await context.newPage()
  const consoleProblems = []
  trackConsoleProblems(page, consoleProblems)

  const league = await discoverLeague(context.request)
  const routes = buildRoutes(league)
  for (const target of routes) {
    await assertRoute(context, target, consoleProblems)
  }

  await page.goto(`${appUrl}/opportunities`, {
    waitUntil: "domcontentloaded",
    timeout: 30_000,
  })
  await page
    .locator("h2")
    .filter({ hasText: "Opportunity Feed" })
    .first()
    .waitFor({ timeout: readyTimeoutMs })
  await page.getByRole("button", { name: "High confidence" }).click()
  await page.locator("text=/Showing \\d+ of \\d+ ranked signals\\./").waitFor({
    timeout: readyTimeoutMs,
  })

  const relevantProblems = consoleProblems.filter(
    (entry) =>
      !entry.includes("Download the React DevTools") &&
      !entry.includes("Failed to load resource: the server responded with a status of 404"),
  )
  await browser.close()
  if (relevantProblems.length) {
    throw new Error(`Console problems:\n${relevantProblems.join("\n")}`)
  }
  console.log(
    JSON.stringify(
      {
        appUrl,
        viewportWidth,
        routesChecked: routes.map((target) => target.path),
        league,
        interaction: "opportunities high-confidence filter",
      },
      null,
      2,
    ),
  )
}

run().catch((error) => {
  console.error(error.message)
  console.error(
    "If Playwright browsers are missing, run `pnpm browser:install` or set BROWSER_EXECUTABLE_PATH to a local Chrome executable.",
  )
  process.exit(1)
})

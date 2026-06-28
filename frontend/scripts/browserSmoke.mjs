import { existsSync } from "node:fs"

import { chromium } from "playwright"

const appUrl = process.env.APP_URL ?? "http://127.0.0.1:5173"
const defaultChrome =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
const executablePath =
  process.env.BROWSER_EXECUTABLE_PATH ??
  (existsSync(defaultChrome) ? defaultChrome : undefined)

function route(path, expected) {
  return { path, expected }
}

async function discoverLeague(request) {
  try {
    const response = await request.get(`${appUrl}/api/dashboard/summary`, {
      timeout: 30_000,
    })
    if (!response.ok()) return null
    const leagues = await response.json()
    const first = Array.isArray(leagues) ? leagues[0] : null
    if (!first?.league_id) return null
    return {
      leagueId: String(first.league_id),
      rosterId: first.user_roster_id ? Number(first.user_roster_id) : null,
    }
  } catch {
    return null
  }
}

function buildRoutes(league) {
  const routes = [
    route("/", ["Top moves today"]),
    route("/opportunities", ["Opportunity Feed", "Showing"]),
    route("/portfolio", ["Portfolio", "Player Exposure"]),
    route("/trades", ["Trade Evaluator"]),
    route("/draft-room", ["Draft Room"]),
  ]
  if (!league) return routes
  const roster = league.rosterId ? `?rosterId=${league.rosterId}` : ""
  routes.push(
    route(`/league/${league.leagueId}${roster}`, ["League Briefing"]),
    route(`/league/${league.leagueId}/waivers${roster}`, ["Waiver"]),
    route(`/league/${league.leagueId}/managers`, ["Manager"]),
    route(`/league/${league.leagueId}/rookie-board`, ["Rookie"]),
  )
  return routes
}

async function assertRoute(page, target) {
  await page.goto(`${appUrl}${target.path}`, {
    waitUntil: "networkidle",
    timeout: 45_000,
  })
  const bodyText = await page.locator("body").innerText({ timeout: 10_000 })
  const missing = target.expected.filter((text) => !bodyText.includes(text))
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
}

async function run() {
  const launchOptions = executablePath
    ? { headless: true, executablePath }
    : { headless: true }
  const browser = await chromium.launch(launchOptions)
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
  })
  const page = await context.newPage()
  const consoleProblems = []
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleProblems.push(`${message.type()}: ${message.text()}`)
    }
  })
  page.on("pageerror", (error) => {
    consoleProblems.push(`pageerror: ${error.message}`)
  })

  const league = await discoverLeague(context.request)
  const routes = buildRoutes(league)
  for (const target of routes) {
    await assertRoute(page, target)
  }

  await page.goto(`${appUrl}/opportunities`, {
    waitUntil: "networkidle",
    timeout: 45_000,
  })
  await page.getByRole("button", { name: "High confidence" }).click()
  await page.locator("text=/Showing \\d+ of \\d+ ranked signals\\./").waitFor({
    timeout: 10_000,
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

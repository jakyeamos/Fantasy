import { spawn } from "node:child_process"
import net from "node:net"

const frontendRoot = new URL("..", import.meta.url).pathname.replace(/\/$/, "")
const repositoryRoot = new URL("../..", import.meta.url).pathname.replace(/\/$/, "")
const startupTimeoutMs = Number(process.env.SMOKE_SERVER_TIMEOUT_MS ?? 30_000)

async function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer()
    probe.once("error", reject)
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address()
      if (!address || typeof address === "string") {
        probe.close()
        reject(new Error("could not allocate a local smoke port"))
        return
      }
      probe.close(() => resolve(address.port))
    })
  })
}

function waitForExit(child) {
  return new Promise((resolve, reject) => {
    child.once("error", reject)
    child.once("exit", (code, signal) => resolve({ code: code ?? 1, signal }))
  })
}

async function waitForServer(child, url) {
  const deadline = Date.now() + startupTimeoutMs
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Vite exited before becoming ready (code ${child.exitCode})`)
    }
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(2_000) })
      if (response.ok) return
    } catch {
      // The bounded startup window absorbs normal Vite dependency warm-up.
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`Vite did not become ready within ${startupTimeoutMs}ms`)
}

function stopProcessGroup(child) {
  if (!child.pid) return
  try {
    process.kill(-child.pid, "SIGTERM")
  } catch {
    child.kill("SIGTERM")
  }
}

async function run() {
  const frontendPort = Number(process.env.QR_SMOKE_PORT ?? (await freePort()))
  const apiPort = Number(process.env.QR_SMOKE_API_PORT ?? (await freePort()))
  const appUrl = `http://127.0.0.1:${frontendPort}`
  const apiUrl = `http://127.0.0.1:${apiPort}`
  const migration = spawn(`${repositoryRoot}/backend/.venv/bin/alembic`, ["upgrade", "heads"], {
    cwd: `${repositoryRoot}/backend`,
    stdio: "inherit",
  })
  const migrationResult = await waitForExit(migration)
  if (migrationResult.code !== 0) {
    throw new Error(`backend migrations failed (code ${migrationResult.code})`)
  }

  const backend = spawn(
    `${repositoryRoot}/backend/.venv/bin/uvicorn`,
    ["fantasy.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
    {
      cwd: `${repositoryRoot}/backend`,
      detached: true,
      env: { ...process.env, FANTASY_DEV_AUTO_REFRESH: "0" },
      stdio: "inherit",
    },
  )
  const frontend = spawn(
    "pnpm",
    ["dev", "--host", "127.0.0.1", "--port", String(frontendPort), "--strictPort"],
    {
      cwd: frontendRoot,
      detached: true,
      env: { ...process.env, BROWSER: "none", FANTASY_API_URL: apiUrl },
      stdio: "inherit",
    },
  )
  try {
    await waitForServer(backend, `${apiUrl}/healthz`)
    await waitForServer(frontend, appUrl)
    const smoke = spawn(process.execPath, ["scripts/browserSmoke.mjs"], {
      cwd: frontendRoot,
      env: { ...process.env, APP_URL: appUrl },
      stdio: "inherit",
    })
    const result = await waitForExit(smoke)
    if (result.code !== 0) {
      process.exitCode = result.code
    }
  } finally {
    stopProcessGroup(frontend)
    stopProcessGroup(backend)
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})

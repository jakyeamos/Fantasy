import { createHash } from "node:crypto"
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs"
import { createRequire } from "node:module"
import { dirname, relative, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { spawnSync } from "node:child_process"

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const baselinePath = resolve(root, ".format-baseline.json")
const configPath = resolve(root, ".prettierrc.json")
const supportedExtensions = new Set([
  ".cjs",
  ".css",
  ".js",
  ".jsx",
  ".json",
  ".md",
  ".mjs",
  ".ts",
  ".tsx",
])
const roots = ["src", "scripts", "tests", "README.md", "package.json", ".prettierrc.json"]

function hashFile(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex")
}

function extension(path) {
  const dot = path.lastIndexOf(".")
  return dot === -1 ? "" : path.slice(dot)
}

function collect(path) {
  if (!existsSync(path)) return []
  if (!statSync(path).isDirectory()) return supportedExtensions.has(extension(path)) ? [path] : []
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === "node_modules" || entry.name === "dist") return []
    return collect(resolve(path, entry.name))
  })
}

const files = roots
  .flatMap((entry) => collect(resolve(root, entry)))
  .map((path) => ({ path, relativePath: relative(root, path) }))
  .sort((left, right) => left.relativePath.localeCompare(right.relativePath))

if (process.argv.includes("--update-baseline")) {
  const baseline = {
    schema_version: "frontend-format-baseline/1.0",
    prettier_version: "3.8.1",
    config_sha256: hashFile(configPath),
    files: Object.fromEntries(files.map((file) => [file.relativePath, hashFile(file.path)])),
  }
  writeFileSync(baselinePath, `${JSON.stringify(baseline, null, 2)}\n`)
  console.log(`Recorded ${files.length} legacy formatting hashes.`)
  process.exit(0)
}

if (!existsSync(baselinePath)) {
  console.error(
    "Formatting baseline is missing. Run pnpm format:baseline after reviewing legacy files.",
  )
  process.exit(2)
}

const baseline = JSON.parse(readFileSync(baselinePath, "utf8"))
if (baseline.prettier_version !== "3.8.1" || baseline.config_sha256 !== hashFile(configPath)) {
  console.error("Formatter version or configuration changed without a reviewed baseline update.")
  process.exit(2)
}

const filesRequiringFormatting = files.filter(
  (file) => baseline.files[file.relativePath] !== hashFile(file.path),
)
if (filesRequiringFormatting.length === 0) {
  console.log("Formatting contract passed; no new or modified frontend files require checking.")
  process.exit(0)
}

const require = createRequire(import.meta.url)
const prettierCli = require.resolve("prettier/bin/prettier.cjs")
const result = spawnSync(
  process.execPath,
  [
    prettierCli,
    "--config",
    configPath,
    "--check",
    ...filesRequiringFormatting.map((file) => file.path),
  ],
  { cwd: root, encoding: "utf8", stdio: "inherit" },
)
process.exit(result.status ?? 1)

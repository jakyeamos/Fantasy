export type Theme = "light" | "dark"

export const THEME_STORAGE_KEY = "fantasy-theme"
export const SYSTEM_THEME_MEDIA_QUERY = "(prefers-color-scheme: dark)"

function isTheme(value: string | null): value is Theme {
  return value === "light" || value === "dark"
}

export function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null

  try {
    const theme = window.localStorage.getItem(THEME_STORAGE_KEY)
    return isTheme(theme) ? theme : null
  } catch {
    return null
  }
}

export function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "light"

  return window.matchMedia(SYSTEM_THEME_MEDIA_QUERY).matches ? "dark" : "light"
}

export function getPreferredTheme(): Theme {
  return getStoredTheme() ?? getSystemTheme()
}

export function persistTheme(theme: Theme) {
  if (typeof window === "undefined") return

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Ignore storage failures and keep the in-memory theme.
  }
}

export function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return

  document.documentElement.classList.toggle("dark", theme === "dark")
  document.documentElement.style.colorScheme = theme
}

import {
  type TextmateStyles,
  type ThemesWithColorStyles,
  type ThemeKey,
  themeKeys,
  type ThemeOverrides,
} from '~/types'
import {
  loadShikiTheme,
  type BundledShikiTheme,
  type ExpressiveCodeTheme,
} from 'astro-expressive-code'
import Color from 'color'

export function pick(obj: Record<string, any>, keys: string[]) {
  return Object.fromEntries(
    keys.filter((key) => key in obj).map((key) => [key, obj[key]]),
  )
}

export function flattenThemeColors(theme: ExpressiveCodeTheme): {
  [key: string]: string
} {
  const scopedThemeSettings = theme.settings.reduce(
    (acc, item) => {
      const { scope, settings } = item
      const { foreground } = settings
      if (scope && foreground) {
        for (const s of scope) {
          acc[s] = foreground.toLowerCase().trim()
        }
      }
      return acc
    },
    {} as { [key: string]: string },
  )
  return { ...theme.colors, ...scopedThemeSettings }
}

const unresolvedStyles: TextmateStyles = {
  // VSCode Command: Inspect Editor Tokens And Scopes
  foreground: ['editor.foreground'],
  background: ['editor.background'],
  accent: ['editor.foreground'],
  heading1: ['entity.name.section', 'markup.heading', 'editor.foreground'],
  heading2: ['entity.name.section', 'markup.heading', 'editor.foreground'],
  heading3: ['entity.name.section', 'markup.heading', 'editor.foreground'],
  heading4: ['entity.name.section', 'markup.heading', 'editor.foreground'],
  heading5: ['entity.name.section', 'markup.heading', 'editor.foreground'],
  heading6: ['entity.name.section', 'markup.heading', 'editor.foreground'],
  list: ['punctuation.definition.list.begin.markdown', 'editor.foreground'],
  separator: ['editor.background'],
  italic: ['markup.italic', 'editor.foreground'],
  link: ['markup.underline.link', 'string.other.link', 'editor.foreground'],
  note: ['support.type', 'editor.foreground'],
  tip: ['string', 'editor.foreground'],
  important: ['keyword', 'editor.foreground'],
  caution: ['constant.numeric', 'editor.foreground'],
  warning: ['invalid', 'editor.foreground'],
  blue: ['support.type', 'editor.foreground'],
  green: ['string', 'editor.foreground'],
  red: ['invalid', 'editor.foreground'],
  yellow: ['constant.numeric', 'editor.foreground'],
  magenta: ['keyword', 'editor.foreground'],
  cyan: ['support.function', 'editor.foreground'],
}

export async function resolveThemeColorStyles(
  themes: BundledShikiTheme[],
  overrides?: ThemeOverrides,
): Promise<ThemesWithColorStyles> {
  const validateColor = (color: string) => {
    // Check if the color is a valid hex, rgb, or hsl color via regex
    const colorRegex = /^(#|rgb|hsl)/i
    if (!colorRegex.test(color)) return undefined
    try {
      return new Color(color).hex()
    } catch {
      return undefined
    }
  }
  const resolvedThemes = themes.map(async (theme) => {
    const loadedTheme = await loadShikiTheme(theme)
    const flattenedTheme = flattenThemeColors(loadedTheme)
    const result = {} as { [key in ThemeKey]: string }
    for (const themeKey of Object.keys(unresolvedStyles) as ThemeKey[]) {
      if (overrides?.[theme]?.[themeKey]) {
        const override = overrides[theme][themeKey]
        const overrideColor = validateColor(override)
        if (overrideColor) {
          result[themeKey] = override
          continue
        }
        // If the override is not a valid color, try to resolve it as a highlight group
        if (themeKeys.includes(override as ThemeKey)) {
          for (const textmateGroup of unresolvedStyles[override as ThemeKey]) {
            if (flattenedTheme[textmateGroup]) {
              result[themeKey] = flattenedTheme[textmateGroup]
              break
            }
          }
        }
        if (result[themeKey]) {
          continue
        } else {
          console.warn(
            `Theme override for ${theme}.${themeKey} is not a valid color or theme key: ${override}`,
          )
        }
      }
      // Try to resolve the color from the theme using highlight groups
      for (const textmateGroup of unresolvedStyles[themeKey]) {
        if (flattenedTheme[textmateGroup]) {
          result[themeKey] = flattenedTheme[textmateGroup]
          break
        }
      }
      // If we still don't have a color, use the editor foreground as fallback
      if (!result[themeKey] && flattenedTheme['editor.foreground']) {
        result[themeKey] = flattenedTheme['editor.foreground']
      }
      // Final fallback
      if (!result[themeKey]) {
        result[themeKey] = theme.includes('dark') ? '#ffffff' : '#000000'
      }
    }
    return [theme, result] as [BundledShikiTheme, typeof result]
  })
  return Object.fromEntries(await Promise.all(resolvedThemes))
}

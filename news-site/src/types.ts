import type { BundledShikiTheme } from 'astro-expressive-code'

export type NavLink = {
  name: string
  url: string
  external?: boolean
}

export const themeKeys = [
  'foreground',
  'background',
  'accent',
  // Markdown styles
  'heading1',
  'heading2',
  'heading3',
  'heading4',
  'heading5',
  'heading6',
  'list',
  'separator',
  'italic',
  'link',
  // For admonition styling
  'note',
  'tip',
  'important',
  'caution',
  'warning',
  // Terminal colors for user customization only, not used by default
  'blue',
  'green',
  'red',
  'yellow',
  'magenta',
  'cyan',
] as const

export type ThemeKey = (typeof themeKeys)[number]

export type TextmateStyles = {
  [key in ThemeKey]: string[]
}

export type ColorStyles = {
  [key in ThemeKey]: string
}

export type ThemesWithColorStyles = Partial<Record<BundledShikiTheme, ColorStyles>>
export type ThemeOverrides = Partial<Record<BundledShikiTheme, Partial<ColorStyles>>>

export interface ThemesConfig {
  default: BundledShikiTheme | 'auto'
  mode: 'single' | 'light-dark-auto' | 'select'
  include: BundledShikiTheme[]
  overrides?: ThemeOverrides
}

export type SocialLinks = {
  github?: string
  twitter?: string
  mastodon?: string
  bluesky?: string
  linkedin?: string
  email?: string
  hn?: string
  reddit?: string
  rss?: boolean
}

export interface SiteConfig {
  site: string
  font: string
  title: string
  description: string
  author: string
  tags: string[]
  pageSize: number
  trailingSlashes: boolean
  themes: ThemesConfig
  socialLinks: SocialLinks
  navLinks: NavLink[]
}

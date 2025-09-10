import type { SiteConfig } from '~/types'

const config: SiteConfig = {
  // Absolute URL to the root of your published site, used for generating links and sitemaps.
  site: 'https://news.reckoning.dev',
  // The name of your site, used in the title and for SEO.
  title: 'Reckoning News',
  // The description of your site, used for SEO and RSS feed.
  description:
    'Stay informed with the latest news from technology, science, and global events',
  // The author of the site, used in the footer, SEO, and RSS feed.
  author: 'reckoning.dev',
  // Keywords for SEO, used in the meta tags.
  tags: ['News', 'Technology', 'Science', 'Global', 'Current Events'],
  // Font imported from @fontsource or elsewhere, used for the entire site.
  font: 'JetBrains Mono Variable',
  // For pagination, the number of posts to display per page.
  pageSize: 10,
  // Whether Astro should resolve trailing slashes in URLs or not.
  trailingSlashes: false,
  // The navigation links to display in the header.
  navLinks: [],
  // The theming configuration for the site.
  themes: {
    // The theming mode. One of "single" | "select" | "light-dark-auto".
    mode: 'light-dark-auto',
    // The default theme identifier, used when themeMode is "select" or "light-dark-auto".
    default: 'one-dark-pro',
    // Shiki themes to bundle with the site.
    // These will be used to theme the entire site along with syntax highlighting.
    // To use light-dark-auto mode, only include a light and a dark theme in that order.
    include: ['one-light', 'one-dark-pro'],
    // Optional overrides for specific themes to customize colors.
    overrides: {
      'one-dark-pro': {
        background: '#282c34',
        foreground: '#abb2bf',
        accent: '#61afef',
        heading1: '#e06c75',
        heading2: '#d19a66',
        heading3: '#e5c07b',
        heading4: '#98c379',
        heading5: '#56b6c2',
        heading6: '#c678dd',
        link: '#61afef',
        separator: '#3e4451',
      },
      'one-light': {
        background: '#fafafa',
        foreground: '#383a42',
        accent: '#4078f2',
        heading1: '#e45649',
        heading2: '#c18401',
        heading3: '#986801',
        heading4: '#50a14f',
        heading5: '#0184bc',
        heading6: '#a626a4',
        link: '#4078f2',
        separator: '#e5e5e6',
      },
    },
  },
  // Social links to display in the footer.
  socialLinks: {},
}

export default config

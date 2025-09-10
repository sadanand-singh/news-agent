# Reckoning News - Modern Static News Site

A beautiful, responsive static news site built with AstroJS and TailwindCSS that displays curated news from technology, science, and global events.

## 🚀 Features

- **Responsive Design**: Optimized for both mobile and desktop viewing
- **Lazy Loading**: Progressive loading of news articles as you scroll
- **Sidebar Navigation**: Easy navigation between different news categories
- **Modern UI**: Clean, professional design with smooth animations
- **Daily Updates**: Automatically loads the latest news data file
- **Fast Performance**: Static site generation for optimal speed
- **Accessibility**: Built with semantic HTML and ARIA attributes

## 🛠️ Tech Stack

- **[Astro](https://astro.build/)**: Static site generator
- **[TailwindCSS](https://tailwindcss.com/)**: Utility-first CSS framework
- **TypeScript**: Type-safe development
- **YAML**: Data format for news content

## 📦 Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd news-site
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Place your news data file in `src/data/`:

   ```bash
   # File should be named: news_collections_YYYYMMDD_HHMMSS.yaml
   cp your-news-file.yaml src/data/
   ```

4. Start the development server:

   ```bash
   npm run dev
   ```

5. Open [http://localhost:4321](http://localhost:4321) in your browser

## 📁 Project Structure

```text

news-site/
├── src/
│   ├── components/
│   │   ├── NewsGroup.astro     # News group section component
│   │   ├── NewsItem.astro      # Individual news article component
│   │   └── Sidebar.astro       # Navigation sidebar
│   ├── data/
│   │   └── news_collections_*.yaml  # News data files
│   ├── layouts/
│   │   └── Layout.astro        # Base HTML layout
│   ├── pages/
│   │   └── index.astro         # Main page
│   ├── styles/
│   │   └── global.css          # TailwindCSS imports
│   └── utils/
│       └── loadNewsData.ts     # YAML data loader utilities
├── public/                     # Static assets
├── astro.config.mjs           # Astro configuration
├── tailwind.config.js         # Tailwind configuration
└── package.json
```

## 📄 Data Format

The news data should be in YAML format with the following structure:

```yaml
Topic Name:
  groups:
    - Technology
    - Science
  news:
    - published_date: '2024-07-21'
      sources:
        - https://example.com/article1
        - https://example.com/article2
      summary: "Article summary text..."
      title: "Article Title"
```

## 🎨 Features in Detail

### Responsive Sidebar

- Collapsible on mobile devices
- Smooth scrolling navigation
- Active section highlighting

### Lazy Loading

- Initial load shows first 3 articles per section
- "Load More" buttons for additional content
- Automatic loading when scrolling near content
- Intersection Observer API for performance

### News Article Cards

- Publication date display
- Source links with domain extraction
- Clean typography and spacing
- Hover animations

### Performance Optimizations

- Static site generation
- Minimal JavaScript bundle
- Optimized images and assets
- Custom scrollbar styling

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## 🔧 Customization

### Styling

- Edit `src/styles/global.css` for global styles
- Modify TailwindCSS classes in components
- Update `tailwind.config.js` for custom design tokens

### Data Processing

- Modify `src/utils/loadNewsData.ts` to change data filtering
- Update ignored groups in the filter functions
- Customize sorting and grouping logic

### Layout

- Edit `src/layouts/Layout.astro` for HTML head modifications
- Update `src/pages/index.astro` for main page structure
- Customize components in `src/components/`

## 📱 Mobile Experience

The site is fully responsive with:

- Collapsible navigation menu
- Touch-friendly interface
- Optimized typography for small screens
- Fast loading and smooth scrolling

## 🔄 Daily Updates

To update with new news data:

1. Replace the file in `src/data/` with the latest news collection
2. Rebuild the site: `npm run build`
3. Deploy the updated `dist/` folder

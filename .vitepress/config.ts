import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Finances Bot',
  description: 'Official documentation for Finances Telegram Bot — Real-time financial market tracking, portfolio management, and admin diagnostics.',
  base: '/finances/',

  head: [
    ['meta', { name: 'viewport', content: 'width=device-width, initial-scale=1.0, viewport-fit=cover' }],
    ['meta', { name: 'theme-color', content: '#1dd1a1' }],
    ['meta', { property: 'og:title', content: 'Finances Bot Documentation' }],
    ['meta', { property: 'og:description', content: 'Official documentation for Finances Telegram Bot' }],
    ['link', { rel: 'icon', href: '/finances/favicon.ico' }],
    // Markdown parser
    ['script', { src: 'https://cdn.jsdelivr.net/npm/marked/marked.min.js' }],
    // Mermaid diagrams
    ['script', { src: 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js' }],
  ],

  // Disable default theme — we use a fully custom theme
  appearance: false,

  srcDir: '.',
  outDir: '.vitepress/dist',
})

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useTheme } from './composables/useTheme'
import { useLang } from './composables/useLang'
import { type DocEntry, DOCS_DATA } from './data/docs-data'
import SiteHeader from './components/SiteHeader.vue'
import DocsSidebar from './components/DocsSidebar.vue'
import MermaidModal from './components/MermaidModal.vue'
import SearchModal from './components/SearchModal.vue'
import HomePage from './components/HomePage.vue'
// Syntax highlighting — npm package, no CDN race conditions
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import yaml from 'highlight.js/lib/languages/yaml'
import typescript from 'highlight.js/lib/languages/typescript'
import csharp from 'highlight.js/lib/languages/csharp'
import dockerfile from 'highlight.js/lib/languages/dockerfile'
import ini from 'highlight.js/lib/languages/ini'

hljs.registerLanguage('python', python)
hljs.registerLanguage('json', json)
const enhanceBash = (h) => {
  const grammar = bash(h)
  if (grammar.keywords && Array.isArray(grammar.keywords.built_in)) {
    grammar.keywords.built_in.push(
      'python', 'python3', 'pip', 'docker', 'docker-compose', 'npm', 'node', 'npx', 
      'git', 'apt', 'apt-get', 'yarn', 'pnpm', 'make', 'uvicorn', 'alembic', 
      'pytest', 'poetry', 'systemctl', 'journalctl', 'sudo', 'pm2', 'curl', 'wget'
    )
  }
  if (grammar.contains) {
    grammar.contains.push({
      className: 'attribute',
      begin: /(^|\\s)-{1,2}[a-zA-Z0-9_-]+/
    })
  }
  return grammar
}

hljs.registerLanguage('bash', enhanceBash)
hljs.registerLanguage('shell', enhanceBash)
hljs.registerLanguage('sh', enhanceBash)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('csharp', csharp)
hljs.registerLanguage('cs', csharp)
hljs.registerLanguage('dockerfile', dockerfile)
hljs.registerLanguage('ini', ini)
hljs.registerLanguage('toml', ini)

// ── State ───────────────────────────────────────────────────────────────────
const { theme } = useTheme()
const { lang, strings, docs } = useLang()

type Page = 'home' | 'docs'
const currentPage = ref<Page>('home')
const activeDocKey = ref('readme')
const sidebarOpen = ref(false)
const searchOpen = ref(false)
const mermaidModalSvg = ref('')
const mermaidModalOpen = ref(false)

// ── Docs Rendering ──────────────────────────────────────────────────────────
const docHtml = ref('')
const tocItems = ref<Array<{ id: string; text: string; level: number }>>([])

function cleanMarkdown(rawMd: string): string {
  return rawMd
    .replace(/\[\s*←?\s*(Back\s+to\s+(docs\s+)?index|Повернутися\s+до\s+змісту|Назад\s+до\s+змісту)\s*\]\([^)]+\)/gi, '')
    .replace(/\[\s*←[^\]]+\]\([^)]+\)/gi, '')
    .trim()
}

async function loadDoc(key: string, updateHash = true) {
  const currentDocs = docs.value
  if (!currentDocs[key]) key = 'readme'
  activeDocKey.value = key
  sidebarOpen.value = false

  if (updateHash) window.location.hash = key

  const entry: DocEntry = currentDocs[key]
  if (!entry) return

  if (!entry.content) {
    docHtml.value = `<div style="padding:3rem;text-align:center;color:var(--text-dim)">${strings.value.loadingDoc}</div>`
    try {
      const url = `https://raw.githubusercontent.com/teferdet/finances/main/docs/${entry.file}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const md = cleanMarkdown(await res.text())
      entry.content = md
      DOCS_DATA[lang.value][key].content = md
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      docHtml.value = `<div style="padding:2rem;color:#ff5555;text-align:center">${strings.value.errorLoading} ${msg}</div>`
      return
    }
  } else {
    entry.content = cleanMarkdown(entry.content)
  }

  // @ts-ignore — marked loaded via CDN script
  const rawHtml: string = window.marked?.parse(entry.content!) ?? `<pre>${entry.content}</pre>`
  docHtml.value = rawHtml
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

watch(lang, () => {
  if (currentPage.value === 'docs') {
    loadDoc(activeDocKey.value, false)
  }
})

// ── Post-render: runs after Vue sets innerHTML via v-html ───────────────────
// Uses watch + nextTick so DOM is fully updated before we touch it
let mermaidCounter = 0

watch(docHtml, async () => {
  await nextTick()
  await postRender()
  initTocSpy()
})

async function postRender() {
  const area = document.getElementById('docs-content-area')
  if (!area) return

  // Assign IDs to headings & build TOC
  const headings = Array.from(area.querySelectorAll('h2, h3, h4'))
  tocItems.value = headings.map((h, i) => {
    const id = h.id || `section-${i}`
    h.id = id
    return {
      id,
      text: h.textContent?.replace(/^[#\s]+/, '').trim() ?? '',
      level: parseInt(h.tagName[1]),
    }
  })

  // Wrap tables
  area.querySelectorAll('table').forEach(table => {
    if (table.parentElement?.classList.contains('table-wrapper')) return
    const wrap = document.createElement('div')
    wrap.className = 'table-wrapper'
    table.parentNode?.insertBefore(wrap, table)
    wrap.appendChild(table)
  })

  // Syntax highlighting via highlight.js (synchronous, no CDN race)
  area.querySelectorAll<HTMLElement>('pre code:not(.hljs)').forEach(block => {
    // Skip mermaid blocks
    if (block.classList.contains('language-mermaid')) return
    hljs.highlightElement(block)
  })

  // Copy buttons on code blocks
  const btnLabel = strings.value.btnCopy
  area.querySelectorAll('pre').forEach(pre => {
    if (pre.querySelector('code.language-mermaid')) return
    if (pre.querySelector('.copy-code-btn')) return
    const btn = document.createElement('button')
    btn.className = 'copy-code-btn'
    btn.textContent = btnLabel
    btn.addEventListener('click', () => {
      const text = pre.querySelector('code')?.innerText ?? (pre as HTMLElement).innerText
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = strings.value.copied
        setTimeout(() => { btn.textContent = btnLabel }, 2000)
      })
    })
    pre.appendChild(btn)
  })

  // Internal .md link interception with capture to prevent VitePress router interference
  area.querySelectorAll('a').forEach(a => {
    const href = a.getAttribute('href') ?? ''
    if (!href.includes('.md') || href.startsWith('http')) return
    if ((a as HTMLElement).dataset.intercepted) return
    ;(a as HTMLElement).dataset.intercepted = '1'
    a.addEventListener('click', e => {
      e.preventDefault()
      e.stopPropagation()
      e.stopImmediatePropagation()
      const cleanHref = href.split('#')[0]
      const fileName = cleanHref.split('/').pop()?.toLowerCase() ?? ''
      const matched = Object.keys(docs.value).find(k =>
        docs.value[k].file.split('/').pop()?.toLowerCase() === fileName
      )
      if (matched) {
        showPage('docs')
        loadDoc(matched)
      }
    }, true)
  })

  // Render Mermaid diagrams IN-PLACE (same approach as original app.js)
  await renderMermaid(area)
}

async function renderMermaid(area: HTMLElement) {
  // @ts-ignore
  const mermaid = window.mermaid
  if (!mermaid) return

  const isDark = theme.value === 'dark'
  mermaid.initialize({
    startOnLoad: false,
    theme: isDark ? 'dark' : 'default',
    themeVariables: isDark ? {
      primaryColor: '#132644', primaryTextColor: '#f0f6fc', primaryBorderColor: '#1dd1a1',
      lineColor: '#38bdf8', secondaryColor: '#0b192e', tertiaryColor: '#07101d',
      actorBkg: '#132644', actorTextColor: '#f0f6fc', actorBorder: '#1e3a60',
      signalColor: '#38bdf8', signalTextColor: '#f0f6fc', labelTextColor: '#f0f6fc',
      loopTextColor: '#f0f6fc', noteBkgColor: '#0b192e', noteTextColor: '#f0f6fc', noteBorderColor: '#1dd1a1',
    } : {
      primaryColor: '#e2e8f0', primaryTextColor: '#0f172a', primaryBorderColor: '#0077cc',
      lineColor: '#0077cc', secondaryColor: '#f1f5f9', tertiaryColor: '#ffffff',
      actorBkg: '#ffffff', actorTextColor: '#0f172a', actorBorder: '#0077cc',
      signalColor: '#0077cc', signalTextColor: '#0f172a', labelTextColor: '#0f172a',
    },
    securityLevel: 'loose',
    fontFamily: 'Inter, -apple-system, sans-serif',
  })

  const blocks = area.querySelectorAll('pre code.language-mermaid')
  for (const block of blocks) {
    const pre = block.parentElement!
    if (pre.dataset.mermaidDone) continue
    const code = block.textContent?.trim() ?? ''
    const id = `mermaid-svg-${++mermaidCounter}`
    try {
      const { svg } = await mermaid.render(id, code)

      // Build the container exactly like original app.js — pure DOM, in-place
      const containerDiv = document.createElement('div')
      containerDiv.className = 'mermaid-container'
      containerDiv.innerHTML = `
        <div class="mermaid-toolbar">
          <div class="mermaid-zoom-indicator">100%</div>
          <button class="mermaid-tb-btn mermaid-tb-zoom-in" title="Zoom In">+</button>
          <button class="mermaid-tb-btn mermaid-tb-zoom-out" title="Zoom Out">−</button>
          <button class="mermaid-tb-btn mermaid-tb-zoom-reset" title="Reset Zoom">↺</button>
          <button class="mermaid-tb-btn" title="Expand Fullscreen">⛶ Expand</button>
        </div>
        <div class="mermaid-viewport" tabindex="0" title="Drag to pan, wheel to zoom">
          <div class="mermaid-content">${svg}</div>
        </div>
      `
      pre.replaceWith(containerDiv)
      attachDiagramZoomPan(containerDiv)

      // Wire up expand button to modal
      containerDiv.querySelector('.mermaid-tb-btn:last-child')?.addEventListener('click', () => {
        const svgHtml = containerDiv.querySelector('.mermaid-content')?.innerHTML ?? ''
        mermaidModalSvg.value = svgHtml
        mermaidModalOpen.value = true
      })
    } catch (err) {
      console.warn('Mermaid render error:', err)
    }
  }
}

/** Pure DOM zoom/pan attachment — identical to original app.js */
function attachDiagramZoomPan(container: HTMLElement) {
  const viewport = container.querySelector<HTMLElement>('.mermaid-viewport')!
  const content = container.querySelector<HTMLElement>('.mermaid-content')!
  const indicator = container.querySelector<HTMLElement>('.mermaid-zoom-indicator')
  const btnIn = container.querySelector<HTMLButtonElement>('.mermaid-tb-zoom-in')
  const btnOut = container.querySelector<HTMLButtonElement>('.mermaid-tb-zoom-out')
  const btnReset = container.querySelector<HTMLButtonElement>('.mermaid-tb-zoom-reset')

  viewport.style.touchAction = 'none'

  let scale = 1, translateX = 0, translateY = 0
  let isDragging = false, startX = 0, startY = 0
  let lastPinchDist: number | null = null

  function update() {
    content.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`
    if (indicator) indicator.textContent = `${Math.round(scale * 100)}%`
    viewport.classList.toggle('is-zoomed', scale > 1.05)
  }

  function zoom(delta: number, ox?: number, oy?: number) {
    const old = scale
    scale = Math.min(Math.max(0.4, scale + delta), 3.5)
    if (ox !== undefined && oy !== undefined) {
      const r = viewport.getBoundingClientRect()
      translateX -= ((ox - r.left - r.width / 2) / old) * (scale - old)
      translateY -= ((oy - r.top - r.height / 2) / old) * (scale - old)
    }
    update()
  }

  function reset() { scale = 1; translateX = 0; translateY = 0; update() }

  btnIn?.addEventListener('click', () => zoom(0.2))
  btnOut?.addEventListener('click', () => zoom(-0.2))
  btnReset?.addEventListener('click', reset)

  // Mouse
  viewport.addEventListener('mousedown', (e: MouseEvent) => {
    if (e.button !== 0) return
    isDragging = true; startX = e.clientX - translateX; startY = e.clientY - translateY
    viewport.style.cursor = 'grabbing'
  })
  window.addEventListener('mousemove', (e: MouseEvent) => {
    if (!isDragging) return
    translateX = e.clientX - startX; translateY = e.clientY - startY; update()
  })
  window.addEventListener('mouseup', () => { if (isDragging) { isDragging = false; viewport.style.cursor = 'grab' } })
  viewport.addEventListener('wheel', (e: WheelEvent) => {
    e.preventDefault(); zoom(e.deltaY < 0 ? 0.15 : -0.15, e.clientX, e.clientY)
  }, { passive: false })

  // Touch
  viewport.addEventListener('touchstart', (e: TouchEvent) => {
    e.preventDefault()
    if (e.touches.length === 1) {
      isDragging = true; lastPinchDist = null
      startX = e.touches[0].clientX - translateX; startY = e.touches[0].clientY - translateY
    } else if (e.touches.length === 2) {
      isDragging = false
      lastPinchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY)
    }
  }, { passive: false })
  viewport.addEventListener('touchmove', (e: TouchEvent) => {
    e.preventDefault()
    if (e.touches.length === 1 && isDragging) {
      translateX = e.touches[0].clientX - startX; translateY = e.touches[0].clientY - startY; update()
    } else if (e.touches.length === 2 && lastPinchDist !== null) {
      const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY)
      zoom((d - lastPinchDist) * 0.008, (e.touches[0].clientX + e.touches[1].clientX) / 2, (e.touches[0].clientY + e.touches[1].clientY) / 2)
      lastPinchDist = d
    }
  }, { passive: false })
  viewport.addEventListener('touchend', (e: TouchEvent) => {
    if (e.touches.length < 2) lastPinchDist = null
    if (e.touches.length === 0) isDragging = false
  })
}

// ── Navigation ──────────────────────────────────────────────────────────────
function showPage(page: Page) {
  currentPage.value = page
  sidebarOpen.value = false
  if (page === 'home') {
    window.location.hash = ''
    document.body.classList.remove('view-docs-active')
  } else {
    document.body.classList.add('view-docs-active')
  }
}

function handleNav(page: 'home' | 'docs') {
  showPage(page)
  if (page === 'docs') loadDoc(activeDocKey.value)
}

function handleSidebarSelect(key: string) {
  if (key === '__home__') { showPage('home'); return }
  showPage('docs')
  loadDoc(key)
}

function handleSearchSelect(key: string) {
  if (key === '__open__') { searchOpen.value = true; return }
  showPage('docs')
  loadDoc(key)
  searchOpen.value = false
}

// ── Hash Routing & Global Link Interceptor ─────────────────────────────────
function handleHash() {
  if (typeof window === 'undefined') return
  // If browser landed on /README.md.html or similar path, clean back to base + hash
  if (window.location.pathname.includes('.md') || window.location.pathname.includes('.html')) {
    const targetHash = window.location.hash || ''
    window.history.replaceState(null, '', '/finances/' + targetHash)
  }

  const hash = window.location.hash.substring(1)
  if (hash && docs.value[hash]) {
    showPage('docs')
    loadDoc(hash, false)
  } else if (!hash) {
    showPage('home')
  }
}

function onGlobalClick(e: MouseEvent) {
  const a = (e.target as HTMLElement).closest('a')
  if (!a) return
  const href = a.getAttribute('href') || ''
  if (!href || href.startsWith('http://') || href.startsWith('https://') || href.startsWith('mailto:') || href.startsWith('tel:')) {
    return
  }

  // In-page or doc hash links (e.g. #dashboard_api)
  if (href.startsWith('#')) {
    const targetKey = href.substring(1)
    if (docs.value[targetKey]) {
      e.preventDefault()
      e.stopPropagation()
      e.stopImmediatePropagation()
      showPage('docs')
      loadDoc(targetKey)
      return
    }
  }

  // Intercept any relative markdown/html file links
  if (href.includes('.md') || href.includes('.html')) {
    e.preventDefault()
    e.stopPropagation()
    e.stopImmediatePropagation()
    const cleanHref = href.split('#')[0].replace(/\.html$/i, '')
    const targetHash = href.includes('#') ? href.split('#')[1] : ''
    const fileName = cleanHref.split('/').pop()?.toLowerCase() ?? ''
    const matched = Object.keys(docs.value).find(k => {
      const docFileName = docs.value[k].file.split('/').pop()?.toLowerCase() ?? ''
      return docFileName === fileName || docFileName === `${fileName}.md` || k === fileName
    })
    if (matched) {
      showPage('docs')
      loadDoc(matched)
    } else if (targetHash && docs.value[targetHash]) {
      showPage('docs')
      loadDoc(targetHash)
    }
  }
}

// ── TOC Scroll Spy ──────────────────────────────────────────────────────────
const activeTocId = ref('')
let tocObserver: IntersectionObserver | null = null

function initTocSpy() {
  tocObserver?.disconnect()
  const headings = document.querySelectorAll('#docs-content-area h2, #docs-content-area h3, #docs-content-area h4')
  tocObserver = new IntersectionObserver(entries => {
    for (const e of entries) {
      if (e.isIntersecting) { activeTocId.value = e.target.id; break }
    }
  }, { rootMargin: `-${64 + 24}px 0px -60% 0px` })
  headings.forEach(h => tocObserver!.observe(h))
}

function scrollToToc(id: string) {
  const el = document.getElementById(id)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - 84
  window.scrollTo({ top, behavior: 'smooth' })
}

// ── Global keyboard shortcuts ───────────────────────────────────────────────
function onGlobalKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); searchOpen.value = true }
  if (e.key === 'Escape' && sidebarOpen.value) sidebarOpen.value = false
}

// ── Preload docs for search ─────────────────────────────────────────────────
async function preloadAllDocs() {
  const currentDocs = docs.value
  for (const [, entry] of Object.entries(currentDocs)) {
    if (entry.content) continue
    try {
      const url = `https://raw.githubusercontent.com/teferdet/finances/main/docs/${entry.file}`
      const res = await fetch(url)
      if (res.ok) {
        entry.content = cleanMarkdown(await res.text())
      }
    } catch { /* silent */ }
  }
}

// ── Sidebar Open State Sync ────────────────────────────────────────────────
watch(sidebarOpen, (open) => {
  if (typeof document !== 'undefined') {
    document.body.classList.toggle('sidebar-open', open)
  }
})

// ── Lifecycle ───────────────────────────────────────────────────────────────
onMounted(() => {
  handleHash()
  window.addEventListener('hashchange', handleHash)
  window.addEventListener('keydown', onGlobalKey)
  document.addEventListener('click', onGlobalClick, true)
  preloadAllDocs()
})

onUnmounted(() => {
  window.removeEventListener('hashchange', handleHash)
  window.removeEventListener('keydown', onGlobalKey)
  document.removeEventListener('click', onGlobalClick, true)
  if (typeof document !== 'undefined') {
    document.body.classList.remove('sidebar-open')
  }
  tocObserver?.disconnect()
})
</script>

<template>
  <div class="docs-app" :data-page="currentPage" :class="{ 'sidebar-open': sidebarOpen }">

    <SiteHeader
      :data-page="currentPage"
      @nav="handleNav"
      @open-search="searchOpen = true"
      @toggle-sidebar="sidebarOpen = !sidebarOpen"
    />

    <!-- Mobile sidebar drawer (rendered on all pages so burger menu works everywhere) -->
    <DocsSidebar
      :active-key="activeDocKey"
      @select="handleSidebarSelect"
    />

    <!-- Mobile sidebar backdrop -->
    <div class="sidebar-backdrop" @click="sidebarOpen = false" />

    <!-- Home Page -->
    <main v-if="currentPage === 'home'">
      <HomePage @go-docs="handleNav('docs')" />
    </main>

    <!-- Docs Page -->
    <div v-else class="docs-viewport">
      <!-- Main content -->
      <section class="docs-main">
        <article
          id="docs-content-area"
          class="markdown-body"
          v-html="docHtml"
        />
      </section>

      <!-- Right TOC -->
      <aside class="docs-toc">
        <div class="toc-title">{{ strings.onThisPage }}</div>
        <nav>
          <a
            v-for="item in tocItems"
            :key="item.id"
            class="toc-item"
            :class="{
              'toc-sub': item.level === 3,
              'toc-sub-2': item.level === 4,
              'active': item.id === activeTocId,
            }"
            :href="`#${item.id}`"
            :title="item.text"
            @click.prevent="scrollToToc(item.id)"
          >{{ item.text }}</a>
        </nav>
      </aside>
    </div>

    <!-- Mermaid fullscreen modal -->
    <MermaidModal
      :svg-html="mermaidModalSvg"
      :is-open="mermaidModalOpen"
      @close="mermaidModalOpen = false"
    />

    <!-- Search modal -->
    <SearchModal
      :is-open="searchOpen"
      @close="searchOpen = false"
      @select="handleSearchSelect"
    />
  </div>
</template>

<style scoped>
body.sidebar-open .docs-sidebar { transform: translateX(0) !important; }
</style>

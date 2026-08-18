/**
 * Finances Bot Site & Documentation Engine
 * Multilingual (EN/UK) + v6.6.0 Architecture + Interactive Zoomable Mermaid Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  let activeDocKey = 'readme';
  let currentTheme = localStorage.getItem('theme') || 'dark';
  let currentLang = localStorage.getItem('finances_lang') || 
                    (navigator.language.startsWith('uk') ? 'uk' : 'en');
  let tocObserver = null;
  let mermaidCounter = 0;

  // Initialize Theme
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon();

  // Initialize Language & Modules
  applyLanguage(currentLang);
  initThemeToggle();
  initLangToggle();
  initNavigation();
  initSidebarNav();
  initMobileSidebar();
  initSearch();
  initHashRouting();
  initMermaidModal();
  preloadAllDocsForSearch();

  // ── Language Toggle & Localization ──────────────────────────────────────────
  function initLangToggle() {
    const btn = document.getElementById('lang-toggle-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      currentLang = currentLang === 'en' ? 'uk' : 'en';
      localStorage.setItem('finances_lang', currentLang);
      applyLanguage(currentLang);
      initSidebarNav();
      if (document.getElementById('view-docs')?.classList.contains('active')) {
        loadDoc(activeDocKey);
      }
      preloadAllDocsForSearch();
    });
  }

  function applyLanguage(lang) {
    const strings = window.UI_STRINGS?.[lang] || window.UI_STRINGS?.en;
    if (!strings) return;

    // Update Brand Badge
    const badge = document.querySelector('.brand-badge');
    if (badge) badge.textContent = strings.brandVersion;

    // Update Header Nav
    const btnHome = document.getElementById('nav-btn-home');
    const btnDocs = document.getElementById('nav-btn-docs');
    if (btnHome) btnHome.textContent = strings.navHome;
    if (btnDocs) btnDocs.textContent = strings.navDocs;

    // Update Lang Toggle Button (Text-only EN / UA)
    const labelSpan = document.getElementById('lang-label');
    if (labelSpan) labelSpan.textContent = lang === 'uk' ? 'UA' : 'EN';

    // Update Search Placeholder
    const searchInput = document.getElementById('search-input-field');
    if (searchInput) searchInput.placeholder = strings.searchPlaceholder;

    // Update TOC Title
    const tocTitle = document.querySelector('.toc-title');
    if (tocTitle) tocTitle.textContent = strings.onThisPage;

    // Update Hero Landing Page
    const heroTitle = document.querySelector('.hero-title');
    const heroDesc = document.querySelector('.hero-description');
    if (heroTitle) heroTitle.textContent = strings.heroTitle;
    if (heroDesc) heroDesc.textContent = strings.heroDesc;

    const btnTg = document.querySelector('.btn-tg span');
    const btnDocsHero = document.getElementById('hero-btn-open-docs');
    const btnGh = document.querySelector('.btn-gh span');
    if (btnTg) btnTg.textContent = strings.btnTelegram;
    if (btnDocsHero) btnDocsHero.innerHTML = `<span>${strings.btnDocs}</span>`;
    if (btnGh) btnGh.textContent = strings.btnGitHub;

    // Update Home Feature Cards
    const homeGrid = document.querySelector('.home-grid');
    if (homeGrid && strings.cards) {
      homeGrid.innerHTML = strings.cards.map(c => `
        <div class="home-card">
          <div class="home-card-icon">${c.icon}</div>
          <h3 class="home-card-title">${c.title}</h3>
          <p class="home-card-text">${c.desc}</p>
        </div>
      `).join('');
    }
  }

  function getDocsDataset() {
    return window.DOCS_DATA?.[currentLang] || window.DOCS_DATA?.en || {};
  }

  // ── Theme Toggle ────────────────────────────────────────────────────────────
  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
      localStorage.setItem('theme', currentTheme);
      updateThemeIcon();
      if (document.getElementById('view-docs')?.classList.contains('active')) {
        renderActiveDoc();
      }
    });
  }

  function updateThemeIcon() {
    const iconSpan = document.getElementById('theme-icon');
    if (iconSpan) {
      iconSpan.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
    }
  }

  // ── Mobile Sidebar Drawer Controller ────────────────────────────────────────
  function initMobileSidebar() {
    const toggleBtn = document.getElementById('mobile-sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');

    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('sidebar-open');
      });
    }

    if (backdrop) {
      backdrop.addEventListener('click', () => {
        document.body.classList.remove('sidebar-open');
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
        document.body.classList.remove('sidebar-open');
      }
    });
  }

  // ── Top Page View Router (Home vs Docs) ──────────────────────────────────────
  function initNavigation() {
    const btnHome = document.getElementById('nav-btn-home');
    const btnDocs = document.getElementById('nav-btn-docs');
    const brandHome = document.getElementById('brand-home-link');
    const heroBtnDocs = document.getElementById('hero-btn-open-docs');

    if (btnHome) {
      btnHome.addEventListener('click', () => showPage('home'));
    }
    if (brandHome) {
      brandHome.addEventListener('click', (e) => {
        e.preventDefault();
        showPage('home');
      });
    }
    if (btnDocs) {
      btnDocs.addEventListener('click', () => {
        showPage('docs');
        loadDoc(activeDocKey);
      });
    }
    if (heroBtnDocs) {
      heroBtnDocs.addEventListener('click', () => {
        showPage('docs');
        loadDoc('readme');
      });
    }
  }

  function showPage(pageId) {
    const viewHome = document.getElementById('view-home');
    const viewDocs = document.getElementById('view-docs');
    const btnHome = document.getElementById('nav-btn-home');
    const btnDocs = document.getElementById('nav-btn-docs');

    document.body.classList.remove('sidebar-open');

    if (pageId === 'home') {
      document.body.classList.remove('view-docs-active');
      viewHome?.classList.add('active');
      viewDocs?.classList.remove('active');
      btnHome?.classList.add('active');
      btnDocs?.classList.remove('active');
      window.location.hash = '';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      document.body.classList.add('view-docs-active');
      viewHome?.classList.remove('active');
      viewDocs?.classList.add('active');
      btnHome?.classList.remove('active');
      btnDocs?.classList.add('active');
    }
  }

  // ── Hash Routing ────────────────────────────────────────────────────────────
  function initHashRouting() {
    const hash = window.location.hash.substring(1);
    const docs = getDocsDataset();
    if (hash && docs[hash]) {
      showPage('docs');
      loadDoc(hash, false);
    }

    window.addEventListener('hashchange', () => {
      const h = window.location.hash.substring(1);
      const currentDocs = getDocsDataset();
      if (h && currentDocs[h]) {
        showPage('docs');
        loadDoc(h, false);
      } else if (!h) {
        showPage('home');
      }
    });
  }

  // ── Populate Sidebar Links ──────────────────────────────────────────────────
  function initSidebarNav() {
    const navContainer = document.getElementById('docs-sidebar-nav');
    const docs = getDocsDataset();
    const strings = window.UI_STRINGS?.[currentLang] || window.UI_STRINGS?.en;
    if (!navContainer || !docs) return;

    navContainer.innerHTML = '';

    // Top Navigation Group (Visible in Mobile Drawer)
    const topNavGroup = document.createElement('div');
    topNavGroup.className = 'sidebar-top-nav';
    topNavGroup.innerHTML = `
      <div class="sidebar-group-title">${strings.navHome} / ${strings.navDocs}</div>
      <a class="sidebar-item" id="drawer-home-link" href="#"><span>🏠</span> <span>${strings.navHome}</span></a>
      <a class="sidebar-item" id="drawer-docs-link" href="#readme"><span>📚</span> <span>${strings.navDocs}</span></a>
    `;
    navContainer.appendChild(topNavGroup);

    topNavGroup.querySelector('#drawer-home-link')?.addEventListener('click', (e) => {
      e.preventDefault();
      showPage('home');
    });
    topNavGroup.querySelector('#drawer-docs-link')?.addEventListener('click', (e) => {
      e.preventDefault();
      showPage('docs');
      loadDoc(activeDocKey || 'readme');
    });

    const categories = {};
    Object.keys(docs).forEach(key => {
      const doc = docs[key];
      const cat = doc.category || (currentLang === 'uk' ? 'Загальне' : 'General');
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push({ key, ...doc });
    });

    Object.keys(categories).forEach(catName => {
      const groupTitle = document.createElement('div');
      groupTitle.className = 'sidebar-group-title';
      groupTitle.textContent = catName;
      navContainer.appendChild(groupTitle);

      categories[catName].forEach(item => {
        const link = document.createElement('a');
        link.className = `sidebar-item ${item.key === activeDocKey ? 'active' : ''}`;
        link.setAttribute('data-key', item.key);
        link.href = `#${item.key}`;
        link.innerHTML = `<span>${item.icon || '📄'}</span> <span>${item.title}</span>`;

        link.addEventListener('click', (e) => {
          e.preventDefault();
          showPage('docs');
          loadDoc(item.key);
        });

        navContainer.appendChild(link);
      });
    });
  }

  async function loadDoc(key, updateHash = true) {
    const docs = getDocsDataset();
    if (!docs || !docs[key]) {
      key = 'readme';
    }
    activeDocKey = key;
    document.body.classList.remove('sidebar-open');

    if (updateHash) {
      window.location.hash = `#${key}`;
    }

    document.querySelectorAll('.sidebar-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-key') === key);
    });

    await renderActiveDoc();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Render Markdown Document & Interactive Elements ─────────────────────────
  async function renderActiveDoc() {
    const area = document.getElementById('docs-content-area');
    const docs = getDocsDataset();
    const strings = window.UI_STRINGS?.[currentLang] || window.UI_STRINGS?.en;
    if (!area || !docs[activeDocKey]) return;

    const doc = docs[activeDocKey];
    
    if (!doc.content) {
      area.innerHTML = `<div style="padding: 3rem; text-align: center; color: var(--text-dim);">${strings.loadingDoc}</div>`;
      try {
        const repoUrl = `https://raw.githubusercontent.com/teferdet/finances/main/docs/${doc.file}`;
        const response = await fetch(repoUrl);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        let text = await response.text();
        text = text.replace(/\[←\s*(Back\s+to\s+docs\s+index|Повернутися\s+до\s+змісту)\]\([^)]+\)/gi, '').trim();
        doc.content = text;
      } catch (error) {
        area.innerHTML = `<div style="padding: 2rem; color: #ff5555; text-align: center;">${strings.errorLoading} ${error.message}</div>`;
        return;
      }
    }

    area.innerHTML = marked.parse(doc.content);

    // Generate Table of Contents immediately so it is always visible and populated
    generateTOC(area);

    // Intercept markdown links to other .md files
    area.querySelectorAll('a').forEach(a => {
      const href = a.getAttribute('href');
      if (href && href.endsWith('.md') && !href.startsWith('http')) {
        a.addEventListener('click', e => {
          e.preventDefault();
          let cleanFileName = href.split('/').pop().toLowerCase();
          let matchedKey = null;
          const currentDocs = getDocsDataset();
          Object.keys(currentDocs).forEach(k => {
            const fName = currentDocs[k].file.split('/').pop().toLowerCase();
            if (fName === cleanFileName) {
              matchedKey = k;
            }
          });
          
          if (matchedKey) {
            loadDoc(matchedKey);
          }
        });
      }
    });

    // Wrap tables
    area.querySelectorAll('table').forEach(table => {
      const wrapper = document.createElement('div');
      wrapper.className = 'table-wrapper';
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });

    // Syntax highlighting via Prism
    if (window.Prism) {
      try {
        Prism.highlightAllUnder(area);
      } catch (e) {
        console.warn('Prism highlight issue:', e);
      }
    }

    // Code copy buttons
    area.querySelectorAll('pre').forEach(pre => {
      if (pre.querySelector('code.language-mermaid')) return;

      const copyBtn = document.createElement('button');
      copyBtn.className = 'copy-code-btn';
      copyBtn.textContent = strings.btnCopy;
      copyBtn.addEventListener('click', () => {
        const text = pre.querySelector('code')?.innerText || pre.innerText;
        navigator.clipboard.writeText(text).then(() => {
          copyBtn.textContent = strings.copied;
          setTimeout(() => copyBtn.textContent = strings.btnCopy, 2000);
        });
      });
      pre.appendChild(copyBtn);
    });

    // Render Zoomable Mermaid Diagrams in background without blocking
    try {
      await renderMermaidDiagrams(area);
    } catch (err) {
      console.warn('Mermaid rendering issue:', err);
    }
  }

  // ── Theme-Adaptive & Zoomable Mermaid Diagrams ──────────────────────────────
  async function renderMermaidDiagrams(container) {
    if (!window.mermaid) return;

    const isDark = currentTheme === 'dark';

    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? 'dark' : 'default',
      themeVariables: isDark ? {
        primaryColor: '#132644',
        primaryTextColor: '#f0f6fc',
        primaryBorderColor: '#1dd1a1',
        lineColor: '#38bdf8',
        secondaryColor: '#0b192e',
        tertiaryColor: '#07101d',
        actorBkg: '#132644',
        actorTextColor: '#f0f6fc',
        actorBorder: '#1e3a60',
        signalColor: '#38bdf8',
        signalTextColor: '#f0f6fc',
        labelTextColor: '#f0f6fc',
        loopTextColor: '#f0f6fc',
        noteBkgColor: '#0b192e',
        noteTextColor: '#f0f6fc',
        noteBorderColor: '#1dd1a1',
      } : {
        primaryColor: '#e2e8f0',
        primaryTextColor: '#0f172a',
        primaryBorderColor: '#0077cc',
        lineColor: '#0077cc',
        secondaryColor: '#f1f5f9',
        tertiaryColor: '#ffffff',
        actorBkg: '#ffffff',
        actorTextColor: '#0f172a',
        actorBorder: '#0077cc',
        signalColor: '#0077cc',
        signalTextColor: '#0f172a',
        labelTextColor: '#0f172a',
        loopTextColor: '#0f172a',
        noteBkgColor: '#f0f7ff',
        noteTextColor: '#0f172a',
        noteBorderColor: '#0077cc',
      },
      securityLevel: 'loose',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    });

    const blocks = container.querySelectorAll('pre code.language-mermaid');
    for (const block of blocks) {
      const pre = block.parentElement;
      const diagramCode = block.textContent.trim();
      const id = `mermaid-svg-${++mermaidCounter}`;

      try {
        const { svg } = await mermaid.render(id, diagramCode);
        const containerDiv = document.createElement('div');
        containerDiv.className = 'mermaid-container';
        containerDiv.innerHTML = `
          <div class="mermaid-toolbar">
            <div class="mermaid-zoom-indicator">100%</div>
            <button class="mermaid-tb-btn mermaid-tb-zoom-in" title="Zoom In">+</button>
            <button class="mermaid-tb-btn mermaid-tb-zoom-out" title="Zoom Out">−</button>
            <button class="mermaid-tb-btn mermaid-tb-zoom-reset" title="Reset Zoom">↺</button>
            <button class="mermaid-tb-btn mermaid-tb-fullscreen" title="Expand Fullscreen">⛶ Expand</button>
          </div>
          <div class="mermaid-viewport" tabindex="0" title="Drag to pan, wheel to zoom">
            <div class="mermaid-content">${svg}</div>
          </div>
        `;

        pre.replaceWith(containerDiv);
        attachDiagramZoomPan(containerDiv);
      } catch (err) {
        console.warn('Mermaid render error:', err);
      }
    }
  }

  // Attach Pan & Zoom functionality to diagram container
  function attachDiagramZoomPan(container) {
    const viewport = container.querySelector('.mermaid-viewport');
    const content = container.querySelector('.mermaid-content');
    const indicator = container.querySelector('.mermaid-zoom-indicator');
    const btnIn = container.querySelector('.mermaid-tb-zoom-in');
    const btnOut = container.querySelector('.mermaid-tb-zoom-out');
    const btnReset = container.querySelector('.mermaid-tb-zoom-reset');
    const btnFullscreen = container.querySelector('.mermaid-tb-fullscreen');

    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;

    function updateTransform() {
      content.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
      if (indicator) {
        indicator.textContent = `${Math.round(scale * 100)}%`;
      }
      if (scale > 1.05) {
        viewport.classList.add('is-zoomed');
      } else {
        viewport.classList.remove('is-zoomed');
      }
    }

    function zoom(delta, originX, originY) {
      const oldScale = scale;
      scale = Math.min(Math.max(0.4, scale + delta), 3.5);
      
      if (originX !== undefined && originY !== undefined) {
        const rect = viewport.getBoundingClientRect();
        const mouseX = originX - rect.left - rect.width / 2;
        const mouseY = originY - rect.top - rect.height / 2;
        translateX -= (mouseX / oldScale) * (scale - oldScale);
        translateY -= (mouseY / oldScale) * (scale - oldScale);
      }
      updateTransform();
    }

    function reset() {
      scale = 1;
      translateX = 0;
      translateY = 0;
      updateTransform();
    }

    btnIn?.addEventListener('click', () => zoom(0.2));
    btnOut?.addEventListener('click', () => zoom(-0.2));
    btnReset?.addEventListener('click', reset);

    // Fullscreen View
    btnFullscreen?.addEventListener('click', () => {
      openMermaidModal(content.innerHTML);
    });

    // Drag to Pan
    viewport.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      viewport.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      updateTransform();
    });

    window.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        viewport.style.cursor = 'grab';
      }
    });

    // Mouse Wheel to Zoom
    viewport.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.15 : -0.15;
      zoom(delta, e.clientX, e.clientY);
    }, { passive: false });
  }

  // ── Fullscreen Interactive Diagram Modal ────────────────────────────────────
  function initMermaidModal() {
    const backdrop = document.getElementById('mermaid-modal-backdrop');
    const body = document.getElementById('mermaid-modal-body');
    const content = document.getElementById('mermaid-modal-content');
    const btnClose = document.getElementById('modal-close');
    const btnIn = document.getElementById('modal-zoom-in');
    const btnOut = document.getElementById('modal-zoom-out');
    const btnReset = document.getElementById('modal-zoom-reset');

    if (!backdrop || !body || !content) return;

    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;

    function updateModalTransform() {
      content.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
      if (btnReset) {
        btnReset.textContent = `🔄 ${Math.round(scale * 100)}%`;
      }
    }

    function modalZoom(delta) {
      scale = Math.min(Math.max(0.3, scale + delta), 4.5);
      updateModalTransform();
    }

    function modalReset() {
      scale = 1;
      translateX = 0;
      translateY = 0;
      updateModalTransform();
    }

    function openMermaidModal(svgHtml) {
      content.innerHTML = svgHtml;
      modalReset();
      backdrop.classList.add('active');
    }

    function closeMermaidModal() {
      backdrop.classList.remove('active');
    }

    window.openMermaidModal = openMermaidModal;
    window.closeMermaidModal = closeMermaidModal;

    btnIn?.addEventListener('click', () => modalZoom(0.25));
    btnOut?.addEventListener('click', () => modalZoom(-0.25));
    btnReset?.addEventListener('click', modalReset);
    btnClose?.addEventListener('click', closeMermaidModal);

    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeMermaidModal();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && backdrop.classList.contains('active')) {
        closeMermaidModal();
      }
    });

    body.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      body.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      updateModalTransform();
    });

    window.addEventListener('mouseup', () => {
      if (isDragging) {
        isDragging = false;
        body.style.cursor = 'grab';
      }
    });

    body.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.2 : -0.2;
      modalZoom(delta);
    }, { passive: false });
  }

  // ── Table of Contents Generator & ScrollSpy ────────────────────────────────
  function generateTOC(container) {
    const tocNav = document.getElementById('docs-toc-nav');
    const strings = window.UI_STRINGS?.[currentLang] || window.UI_STRINGS?.en;
    if (!tocNav) return;

    if (tocObserver) {
      tocObserver.disconnect();
      tocObserver = null;
    }

    tocNav.innerHTML = '';
    const headings = Array.from(container.querySelectorAll('h2, h3, h4'));

    if (headings.length === 0) {
      tocNav.innerHTML = `<span style="font-size:0.82rem; color:var(--text-dim); display:block; padding: 0.35rem 0;">${strings.noSubsections}</span>`;
      return;
    }

    const headingMap = new Map();

    headings.forEach((h, idx) => {
      const headingText = h.textContent.replace(/^[#\s]+/, '').trim();
      if (!headingText) return;

      const id = h.id || `section-${idx}`;
      h.id = id;

      const a = document.createElement('a');
      const tag = h.tagName.toLowerCase();
      a.className = `toc-item ${tag === 'h3' ? 'toc-sub' : ''} ${tag === 'h4' ? 'toc-sub-2' : ''}`;
      a.href = `#${id}`;
      a.textContent = headingText;
      a.title = headingText;

      a.addEventListener('click', (e) => {
        e.preventDefault();
        const headerOffset = 84; // 64px header + 20px breathing space
        const elementPosition = h.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });

        document.querySelectorAll('.toc-item').forEach(item => item.classList.remove('active'));
        a.classList.add('active');
      });

      tocNav.appendChild(a);
      headingMap.set(h, a);
    });

    // ScrollSpy to highlight active heading on scroll
    if ('IntersectionObserver' in window && headings.length > 0) {
      tocObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const activeLink = headingMap.get(entry.target);
            if (activeLink) {
              document.querySelectorAll('.toc-item').forEach(item => item.classList.remove('active'));
              activeLink.classList.add('active');
            }
          }
        });
      }, {
        rootMargin: '-80px 0px -65% 0px',
        threshold: 0.1
      });

      headings.forEach(h => tocObserver.observe(h));
    }
  }

  // ── Full-Text Search Modal ──────────────────────────────────────────────────
  function initSearch() {
    const btn = document.getElementById('search-btn');
    const modal = document.getElementById('search-modal-backdrop');
    const input = document.getElementById('search-input-field');
    const results = document.getElementById('search-results-list');

    if (!btn || !modal || !input || !results) return;

    function openSearch() {
      modal.classList.add('active');
      input.value = '';
      input.focus();
      renderSearchResults('');
    }

    function closeSearch() {
      modal.classList.remove('active');
    }

    btn.addEventListener('click', openSearch);

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeSearch();
    });

    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openSearch();
      }
      if (e.key === 'Escape') closeSearch();
    });

    input.addEventListener('input', (e) => {
      renderSearchResults(e.target.value.trim());
    });

    function renderSearchResults(q) {
      const strings = window.UI_STRINGS?.[currentLang] || window.UI_STRINGS?.en;
      results.innerHTML = '';

      if (!q) {
        results.innerHTML = `<div style="padding:1rem; text-align:center; color:var(--text-dim); font-size:0.85rem;">${strings.searchHint}</div>`;
        return;
      }

      const query = q.toLowerCase();
      const matches = [];
      const docs = getDocsDataset();

      Object.keys(docs).forEach(key => {
        const doc = docs[key];
        const titleMatch = doc.title.toLowerCase().includes(query);
        const idx = doc.content ? doc.content.toLowerCase().indexOf(query) : -1;

        if (titleMatch || idx !== -1) {
          let snippet = doc.content || '';
          if (idx !== -1) {
            const start = Math.max(0, idx - 35);
            const end = Math.min(snippet.length, idx + 80);
            snippet = (start > 0 ? '...' : '') + snippet.substring(start, end) + '...';
          } else {
            snippet = snippet.substring(0, 90) + (snippet.length > 90 ? '...' : '');
          }
          matches.push({ key, title: doc.title, icon: doc.icon, snippet });
        }
      });

      if (matches.length === 0) {
        results.innerHTML = `<div style="padding:1rem; text-align:center; color:var(--text-dim); font-size:0.85rem;">${strings.noResults}</div>`;
        return;
      }

      matches.forEach(m => {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        div.innerHTML = `
          <div class="search-result-title">${m.icon || '📄'} ${escapeHtml(m.title)}</div>
          <div class="search-result-snippet">${escapeHtml(m.snippet)}</div>
        `;

        div.addEventListener('click', () => {
          closeSearch();
          showPage('docs');
          loadDoc(m.key);
        });

        results.appendChild(div);
      });
    }
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function preloadAllDocsForSearch() {
    const docs = getDocsDataset();
    Object.keys(docs).forEach(key => {
      const doc = docs[key];
      if (!doc.content) {
        fetch(`https://raw.githubusercontent.com/teferdet/finances/main/docs/${doc.file}`)
          .then(res => {
            if (res.ok) return res.text();
            throw new Error('Not found');
          })
          .then(text => {
            text = text.replace(/\[←\s*(Back\s+to\s+docs\s+index|Повернутися\s+до\s+змісту)\]\([^)]+\)/gi, '').trim();
            doc.content = text;
          })
          .catch(err => console.warn('Search preload failed for', doc.file));
      }
    });
  }
});

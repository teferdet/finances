/**
 * Finances Bot Site & Documentation Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  let activeDocKey = 'readme';
  let currentTheme = localStorage.getItem('theme') || 'dark';

  // Initialize Theme
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon();

  // Initialize Modules
  initNavigation();
  initSidebarNav();
  initSearch();
  initThemeToggle();
  initHashRouting();

  // Theme Toggle
  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
      localStorage.setItem('theme', currentTheme);
      updateThemeIcon();
    });
  }

  function updateThemeIcon() {
    const iconSpan = document.getElementById('theme-icon');
    if (iconSpan) {
      iconSpan.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
    }
  }

  // Top Page View Router (Home vs Docs)
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

    if (pageId === 'home') {
      viewHome?.classList.add('active');
      viewDocs?.classList.remove('active');
      btnHome?.classList.add('active');
      btnDocs?.classList.remove('active');
      window.location.hash = '';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      viewHome?.classList.remove('active');
      viewDocs?.classList.add('active');
      btnHome?.classList.remove('active');
      btnDocs?.classList.add('active');
    }
  }

  // Hash Routing
  function initHashRouting() {
    const hash = window.location.hash.substring(1);
    if (hash && window.DOCS_DATA && window.DOCS_DATA[hash]) {
      showPage('docs');
      loadDoc(hash, false);
    }

    window.addEventListener('hashchange', () => {
      const h = window.location.hash.substring(1);
      if (h && window.DOCS_DATA && window.DOCS_DATA[h]) {
        showPage('docs');
        loadDoc(h, false);
      } else if (!h) {
        showPage('home');
      }
    });
  }

  // Populate Sidebar Links
  function initSidebarNav() {
    const navContainer = document.getElementById('docs-sidebar-nav');
    if (!navContainer || !window.DOCS_DATA) return;

    navContainer.innerHTML = '';

    const categories = {};
    Object.keys(window.DOCS_DATA).forEach(key => {
      const doc = window.DOCS_DATA[key];
      const cat = doc.category || 'General';
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

  function loadDoc(key, updateHash = true) {
    if (!window.DOCS_DATA || !window.DOCS_DATA[key]) return;
    activeDocKey = key;

    if (updateHash) {
      window.location.hash = `#${key}`;
    }

    document.querySelectorAll('.sidebar-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-key') === key);
    });

    renderActiveDoc();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Render Markdown Document
  function renderActiveDoc() {
    const area = document.getElementById('docs-content-area');
    if (!area || !window.DOCS_DATA[activeDocKey]) return;

    const doc = window.DOCS_DATA[activeDocKey];
    area.innerHTML = marked.parse(doc.content);

    if (window.Prism) {
      Prism.highlightAllUnder(area);
    }

    if (window.mermaid) {
      try {
        const blocks = area.querySelectorAll('pre code.language-mermaid');
        blocks.forEach(block => {
          const pre = block.parentElement;
          const div = document.createElement('div');
          div.className = 'mermaid';
          div.textContent = block.textContent;
          pre.replaceWith(div);
        });
        mermaid.contentLoaded();
      } catch (err) {
        console.warn('Mermaid rendering issue:', err);
      }
    }

    area.querySelectorAll('pre').forEach(pre => {
      const copyBtn = document.createElement('button');
      copyBtn.className = 'copy-code-btn';
      copyBtn.textContent = 'Copy';
      copyBtn.addEventListener('click', () => {
        const text = pre.querySelector('code')?.innerText || pre.innerText;
        navigator.clipboard.writeText(text).then(() => {
          copyBtn.textContent = 'Copied!';
          setTimeout(() => copyBtn.textContent = 'Copy', 2000);
        });
      });
      pre.appendChild(copyBtn);
    });

    generateTOC(area);
  }

  // Table of Contents Generator
  function generateTOC(container) {
    const tocNav = document.getElementById('docs-toc-nav');
    if (!tocNav) return;

    tocNav.innerHTML = '';
    const headings = container.querySelectorAll('h2, h3');

    if (headings.length === 0) {
      tocNav.innerHTML = '<span style="font-size:0.8rem; color:var(--text-dim);">No sub-sections</span>';
      return;
    }

    headings.forEach((h, idx) => {
      const id = h.id || `section-${idx}`;
      h.id = id;

      const a = document.createElement('a');
      a.className = `toc-item ${h.tagName === 'H3' ? 'toc-sub' : ''}`;
      a.href = `#${id}`;
      a.textContent = h.textContent;

      a.addEventListener('click', (e) => {
        e.preventDefault();
        h.scrollIntoView({ behavior: 'smooth' });
      });

      tocNav.appendChild(a);
    });
  }

  // Full-Text Search Modal
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
      results.innerHTML = '';

      if (!q) {
        results.innerHTML = '<div style="padding:1rem; text-align:center; color:var(--text-dim); font-size:0.85rem;">Type a query to search documentation...</div>';
        return;
      }

      const query = q.toLowerCase();
      const matches = [];

      Object.keys(window.DOCS_DATA).forEach(key => {
        const doc = window.DOCS_DATA[key];
        const titleMatch = doc.title.toLowerCase().includes(query);
        const idx = doc.content.toLowerCase().indexOf(query);

        if (titleMatch || idx !== -1) {
          let snippet = doc.content;
          if (idx !== -1) {
            const start = Math.max(0, idx - 35);
            const end = Math.min(doc.content.length, idx + 80);
            snippet = (start > 0 ? '...' : '') + doc.content.substring(start, end) + '...';
          } else {
            snippet = doc.content.substring(0, 90) + '...';
          }
          matches.push({ key, title: doc.title, icon: doc.icon, snippet });
        }
      });

      if (matches.length === 0) {
        results.innerHTML = '<div style="padding:1rem; text-align:center; color:var(--text-dim); font-size:0.85rem;">No matching documentation found.</div>';
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
});

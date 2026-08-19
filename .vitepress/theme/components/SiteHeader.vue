<script setup lang="ts">
import { useTheme } from '../composables/useTheme'
import { useLang } from '../composables/useLang'

const { theme, toggle: toggleTheme } = useTheme()
const { strings, lang, toggle: toggleLang } = useLang()

const emit = defineEmits<{
  'nav': [page: 'home' | 'docs']
  'open-search': []
  'toggle-sidebar': []
}>()
</script>

<template>
  <header class="site-header">
    <!-- Brand -->
    <a href="#" class="brand-area" @click.prevent="emit('nav', 'home')">
      <span>📊 Finances Bot</span>
      <span class="brand-badge">{{ strings.brandVersion }}</span>
    </a>

    <!-- Desktop Nav -->
    <nav class="header-nav">
      <button
        class="nav-link-btn"
        :class="{ active: $attrs['data-page'] === 'home' }"
        @click="emit('nav', 'home')"
      >{{ strings.navHome }}</button>
      <button
        class="nav-link-btn"
        :class="{ active: $attrs['data-page'] === 'docs' }"
        @click="emit('nav', 'docs')"
      >{{ strings.navDocs }}</button>
    </nav>

    <!-- Actions -->
    <div class="header-actions">
      <button class="lang-toggle-btn" :title="`Switch language / Змінити мову`" @click="toggleLang">
        {{ lang === 'uk' ? 'UA' : 'EN' }}
      </button>

      <!-- Mobile sidebar toggle -->
      <button class="icon-btn mobile-sidebar-toggle" title="Toggle Documentation Menu" @click="emit('toggle-sidebar')">
        <span>☰</span>
      </button>

      <button class="search-btn" title="Search Documentation (Ctrl+K)" @click="emit('open-search')">
        <span class="search-icon">🔍</span>
        <span class="search-btn-text">{{ 'Search...' }}</span>
        <kbd>Ctrl K</kbd>
      </button>

      <button class="icon-btn" :title="`Toggle ${theme === 'dark' ? 'Light' : 'Dark'} Theme`" @click="toggleTheme">
        <span>{{ theme === 'dark' ? '🌙' : '☀️' }}</span>
      </button>

      <a
        href="https://github.com/teferdet/finances"
        target="_blank" rel="noopener"
        class="icon-btn github-btn"
        title="GitHub Repository"
      >🐙</a>
    </div>
  </header>
</template>

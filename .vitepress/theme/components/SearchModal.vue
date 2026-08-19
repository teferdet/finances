<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useLang } from '../composables/useLang'

interface SearchResult {
  key: string
  title: string
  icon: string
  snippet: string
}

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits<{ 'close': []; 'select': [key: string] }>()

const { strings, docs } = useLang()
const query = ref('')
const results = ref<SearchResult[]>([])

watch(query, (q) => {
  if (!q.trim()) { results.value = []; return }
  const lq = q.toLowerCase()
  results.value = Object.entries(docs.value)
    .filter(([, entry]) => entry.title.toLowerCase().includes(lq))
    .map(([key, entry]) => ({
      key,
      title: entry.title,
      icon: entry.icon,
      snippet: entry.category,
    }))
    .slice(0, 10)
})

watch(() => props.isOpen, (open) => {
  if (!open) { query.value = ''; results.value = [] }
})

function onBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) emit('close')
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

function globalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    if (!props.isOpen) emit('select', '__open__')
  }
}

onMounted(() => window.addEventListener('keydown', globalKeydown))
onUnmounted(() => window.removeEventListener('keydown', globalKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      class="search-modal-backdrop"
      :class="{ active: props.isOpen }"
      @click="onBackdropClick"
      @keydown="onKeydown"
    >
      <div class="search-modal">
        <div class="search-input-wrapper">
          <span>🔍</span>
          <input
            v-model="query"
            class="search-input-field"
            :placeholder="strings.searchPlaceholder"
            autofocus
          />
        </div>
        <div class="search-results-list">
          <div v-if="!query" style="padding: 1rem; color: var(--text-dim); font-size: 0.88rem;">
            {{ strings.searchHint }}
          </div>
          <div v-else-if="results.length === 0" style="padding: 1rem; color: var(--text-dim); font-size: 0.88rem;">
            {{ strings.noResults }}
          </div>
          <div
            v-for="r in results"
            :key="r.key"
            class="search-result-item"
            @click="emit('select', r.key); emit('close')"
          >
            <div class="search-result-title">{{ r.icon }} {{ r.title }}</div>
            <div class="search-result-snippet">{{ r.snippet }}</div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useLang } from '../composables/useLang'

const props = defineProps<{ activeKey: string }>()
const emit = defineEmits<{ 'select': [key: string] }>()

const { strings, categories } = useLang()
</script>

<template>
  <aside class="docs-sidebar">
    <nav>
      <!-- Mobile-only top nav links -->
      <div class="sidebar-top-nav">
        <div class="sidebar-group-title">{{ strings.navHome }} / {{ strings.navDocs }}</div>
        <a class="sidebar-item" href="#" @click.prevent="emit('select', '__home__')">
          <span>🏠</span> <span>{{ strings.navHome }}</span>
        </a>
        <a class="sidebar-item" href="#readme" @click.prevent="emit('select', 'readme')">
          <span>📚</span> <span>{{ strings.navDocs }}</span>
        </a>
      </div>

      <!-- Category groups -->
      <template v-for="(items, catName) in categories" :key="catName">
        <div class="sidebar-group-title">{{ catName }}</div>
        <a
          v-for="item in items"
          :key="item.key"
          class="sidebar-item"
          :class="{ active: item.key === props.activeKey }"
          :href="`#${item.key}`"
          @click.prevent="emit('select', item.key)"
        >
          <span>{{ item.icon }}</span>
          <span>{{ item.title }}</span>
        </a>
      </template>
    </nav>
  </aside>
</template>

<style scoped>
/* sidebar-top-nav hidden on desktop, visible on mobile */
.sidebar-top-nav {
  display: none;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 0.85rem;
  padding-bottom: 0.85rem;
}

/* first real group title after hidden sidebar-top-nav gets no top margin */
.sidebar-top-nav + :deep(.sidebar-group-title) { margin-top: 0; }

@media (max-width: 768px) {
  .sidebar-top-nav { display: block; }
}
</style>

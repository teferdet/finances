<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMermaid } from '../composables/useMermaid'

const props = defineProps<{ svgHtml: string }>()
const emit = defineEmits<{ 'expand': [svgHtml: string] }>()

const viewportEl = ref<HTMLElement | null>(null)
const contentEl = ref<HTMLElement | null>(null)

const { scale, zoom, reset, attach } = useMermaid(viewportEl, contentEl)
const zoomPercent = computed(() => `${Math.round(scale.value * 100)}%`)

onMounted(() => attach())
</script>

<template>
  <div class="mermaid-container">
    <div class="mermaid-toolbar">
      <div class="mermaid-zoom-indicator">{{ zoomPercent }}</div>
      <button class="mermaid-tb-btn" title="Zoom In" @click="zoom(0.2)">+</button>
      <button class="mermaid-tb-btn" title="Zoom Out" @click="zoom(-0.2)">−</button>
      <button class="mermaid-tb-btn" title="Reset Zoom" @click="reset">↺</button>
      <button class="mermaid-tb-btn" title="Expand Fullscreen" @click="emit('expand', props.svgHtml)">
        ⛶ Expand
      </button>
    </div>

    <div ref="viewportEl" class="mermaid-viewport" tabindex="0" title="Drag to pan, wheel to zoom">
      <div ref="contentEl" class="mermaid-content" v-html="props.svgHtml" />
    </div>
  </div>
</template>

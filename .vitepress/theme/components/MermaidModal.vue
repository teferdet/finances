<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useMermaid } from '../composables/useMermaid'

const props = defineProps<{ svgHtml: string; isOpen: boolean }>()
const emit = defineEmits<{ 'close': [] }>()

const bodyEl = ref<HTMLElement | null>(null)
const contentEl = ref<HTMLElement | null>(null)

const { scale, zoom, reset, attach } = useMermaid(bodyEl, contentEl)
const zoomLabel = computed(() => `${Math.round(scale.value * 100)}%`)

watch(() => props.isOpen, async (open) => {
  if (!open) return
  reset()
  await nextTick()
  attach()
  await nextTick()
  prepareSvg()
})

watch(() => props.svgHtml, async () => {
  if (props.isOpen) {
    await nextTick()
    prepareSvg()
  }
})

/** Cleans inline constraints on the rendered SVG so it fills the modal container naturally */
function prepareSvg() {
  const content = contentEl.value
  if (!content) return

  const svg = content.querySelector('svg')
  if (!svg) return

  svg.removeAttribute('width')
  svg.removeAttribute('height')
  svg.style.width = '100%'
  svg.style.height = '100%'
  svg.style.maxWidth = '100%'
  svg.style.maxHeight = '100%'
  svg.style.display = 'block'
}

function onBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      class="mermaid-modal-backdrop"
      :class="{ active: props.isOpen }"
      @click="onBackdropClick"
      @keydown.esc="emit('close')"
    >
      <div class="mermaid-modal">
        <div class="mermaid-modal-header">
          <span class="mermaid-modal-title">📊 Diagram — Interactive Zoom & Pan</span>
          <div class="mermaid-modal-actions">
            <button class="mermaid-modal-btn" title="Zoom In (+)" @click="zoom(0.25)">🔍+</button>
            <button class="mermaid-modal-btn" title="Zoom Out (−)" @click="zoom(-0.25)">🔍−</button>
            <button class="mermaid-modal-btn" title="Reset Zoom (100%)" @click="reset(); prepareSvg()">{{ zoomLabel }}</button>
            <button class="mermaid-modal-btn close-btn" title="Close (Esc)" @click="emit('close')">✕ Close</button>
          </div>
        </div>

        <div ref="bodyEl" class="mermaid-modal-body">
          <div ref="contentEl" class="mermaid-modal-content" v-html="props.svgHtml" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

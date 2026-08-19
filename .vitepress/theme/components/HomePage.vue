<script setup lang="ts">
import { useLang } from '../composables/useLang'

const { strings } = useLang()

const emit = defineEmits<{ 'go-docs': [] }>()

function copy() {
  navigator.clipboard.writeText('git clone https://github.com/teferdet/finances.git')
}
</script>

<template>
  <div class="home-container">
    <div class="hero-box">
      <h1 class="hero-title">{{ strings.heroTitle }}</h1>
      <p class="hero-description">{{ strings.heroDesc }}</p>

      <div class="button-group">
        <a href="https://t.me/fStatisticsBot" target="_blank" rel="noopener" class="btn-action btn-tg">
          <span>{{ strings.btnTelegram }}</span>
        </a>
        <button class="btn-action btn-docs" @click="emit('go-docs')">
          <span>{{ strings.btnDocs }}</span>
        </button>
        <a href="https://github.com/teferdet/finances" target="_blank" rel="noopener" class="btn-action btn-gh">
          <span>{{ strings.btnGitHub }}</span>
        </a>
      </div>

      <div class="code-box">
        <span>git clone https://github.com/teferdet/finances.git</span>
        <button @click="copy" title="Copy Command">📋 Copy</button>
      </div>
    </div>

    <div class="home-grid">
      <div
        v-for="card in strings.cards"
        :key="card.title"
        class="home-card"
      >
        <div class="home-card-icon">{{ card.icon }}</div>
        <h3 class="home-card-title">{{ card.title }}</h3>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <p class="home-card-text" v-html="card.desc" />
      </div>
    </div>
  </div>
</template>

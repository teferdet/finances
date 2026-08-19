import type { Theme } from 'vitepress'
import Layout from './Layout.vue'
import './styles/custom.css'

export default {
  Layout,
  enhanceApp({ app: _app }) {
    // Global components or plugins can be registered here
  },
} satisfies Theme

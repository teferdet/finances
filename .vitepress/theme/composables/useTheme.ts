import { ref, watchEffect } from 'vue'

export type Theme = 'dark' | 'light'

const theme = ref<Theme>('dark')

watchEffect(() => {
  if (typeof window === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme.value)
  localStorage.setItem('theme', theme.value)
})

export function useTheme() {
  function init() {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme') as Theme
      if (saved) theme.value = saved
    }
  }
  function toggle() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }
  return { theme, toggle, init }
}

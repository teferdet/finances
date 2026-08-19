import { ref, watchEffect } from 'vue'

export type Theme = 'dark' | 'light'

const theme = ref<Theme>(
  (typeof window !== 'undefined'
    ? (localStorage.getItem('theme') as Theme)
    : null) ?? 'dark'
)

watchEffect(() => {
  if (typeof window === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme.value)
  localStorage.setItem('theme', theme.value)
})

export function useTheme() {
  function toggle() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }
  return { theme, toggle }
}

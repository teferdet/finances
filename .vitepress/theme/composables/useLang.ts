import { ref, computed } from 'vue'
import { type Lang, UI_STRINGS, DOCS_DATA } from '../data/docs-data'

const lang = ref<Lang>(
  typeof window !== 'undefined'
    ? ((localStorage.getItem('finances_lang') as Lang) ??
       (navigator.language.startsWith('uk') ? 'uk' : 'en'))
    : 'en'
)

export function useLang() {
  function toggle() {
    lang.value = lang.value === 'en' ? 'uk' : 'en'
    localStorage.setItem('finances_lang', lang.value)
  }

  const strings = computed(() => UI_STRINGS[lang.value])
  const docs = computed(() => DOCS_DATA[lang.value])

  /** Grouped sidebar categories derived from DOCS_DATA */
  const categories = computed(() => {
    const groups: Record<string, Array<{ key: string } & typeof DOCS_DATA['en'][string]>> = {}
    for (const [key, entry] of Object.entries(docs.value)) {
      const cat = entry.category
      if (!groups[cat]) groups[cat] = []
      groups[cat].push({ key, ...entry })
    }
    return groups
  })

  return { lang, strings, docs, categories, toggle }
}

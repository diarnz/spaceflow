import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ToastVariant = 'info' | 'success' | 'warning' | 'error'

export interface ToastItem {
  id: string
  title: string
  variant: ToastVariant
}

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<ToastItem[]>([])

  function push(title: string, variant: ToastVariant = 'info') {
    const id = crypto.randomUUID()
    items.value.push({ id, title, variant })
    window.setTimeout(() => dismiss(id), 4500)
  }

  function dismiss(id: string) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  return {
    items,
    push,
    dismiss,
  }
})

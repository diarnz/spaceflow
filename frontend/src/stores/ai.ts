import { ref } from 'vue'
import { defineStore } from 'pinia'

import { aiApi } from '@/api/client'
import type { AgentType, AiMessage, ToolCall } from '@/types'

export const useAiStore = defineStore('ai', () => {
  const messages = ref<AiMessage[]>([])
  const loading = ref(false)
  const open = ref(false)
  const conversationId = ref<string | null>(null)
  const agentType = ref<AgentType>('copilot')
  const context = ref<Record<string, unknown>>({})

  function setPanelState(
    nextOpen: boolean,
    nextAgentType: AgentType = 'copilot',
    nextContext: Record<string, unknown> = {},
  ) {
    open.value = nextOpen
    agentType.value = nextAgentType
    context.value = nextContext
  }

  function resetConversation() {
    messages.value = []
    conversationId.value = null
  }

  async function send(message: string) {
    const userMessage: AiMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }
    messages.value.push(userMessage)
    loading.value = true
    try {
      const data = await aiApi.chat({
        message,
        agent_type: agentType.value,
        context: context.value,
        conversation_id: conversationId.value,
      })

      const assistantMessage: AiMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        toolCalls: data.tool_calls_made as ToolCall[],
      }

      conversationId.value = data.conversation_id
      messages.value.push(assistantMessage)
      return data
    } finally {
      loading.value = false
    }
  }

  return {
    messages,
    loading,
    open,
    conversationId,
    agentType,
    context,
    setPanelState,
    resetConversation,
    send,
  }
})

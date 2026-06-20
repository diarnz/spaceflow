<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import AiMessage from './AiMessage.vue'
import AiTypingIndicator from './AiTypingIndicator.vue'
import { friendlyError } from '@/api/client'
import { useAiStore } from '@/stores/ai'
import { useNotificationsStore } from '@/stores/notifications'

const ai = useAiStore()
const notifications = useNotificationsStore()
const draft = ref('')
const messagesEl = ref<HTMLDivElement | null>(null)

const quickPrompts = computed(() => {
  if (ai.agentType === 'room_designer') {
    return [
      'Design this room for a 40-person workshop with whiteboards.',
      'Set up theater seating facing a stage and TV screen.',
      'Create a hackathon layout with collaborative tables and monitors.',
    ]
  }

  if (ai.agentType === 'planner') {
    return [
      'Generate the operational task plan for this request.',
      'Which tasks are highest priority for this event?',
    ]
  }

  return [
    'What is the current status of this request?',
    'Check for conflicts on this event.',
    'Summarize the quotation and availability.',
  ]
})

async function send() {
  const content = draft.value.trim()
  if (!content || ai.loading) return
  draft.value = ''
  try {
    await ai.send(content)
  } catch (err) {
    notifications.push(friendlyError(err, 'AI request failed.'), 'error')
  }
}

function closePanel() {
  ai.open = false
}

watch(
  () => ai.messages.length,
  async () => {
    await nextTick()
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <div v-if="ai.open">
      <div
        style="
          position: fixed;
          inset: 0;
          background: transparent;
          z-index: 29;
        "
        @click="closePanel"
      />

      <aside
        style="
          position: fixed;
          top: 0;
          right: 0;
          width: min(440px, 100vw);
          height: 100vh;
          background: var(--bg-secondary);
          border-left: 1px solid var(--border);
          box-shadow: -12px 0 32px rgba(18, 38, 58, 0.12);
          z-index: 30;
          display: flex;
          flex-direction: column;
        "
      >
        <header
          style="
            padding: var(--space-4) var(--space-5);
            border-bottom: 1px solid var(--border);
            background: var(--surface);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: var(--space-3);
          "
        >
          <div>
            <div style="font-weight: 700; display: flex; align-items: center; gap: var(--space-2);">
              <span style="color: var(--accent);">✦</span>
              <span>AI Copilot</span>
            </div>
            <div style="font-size: 0.82rem; color: var(--text-tertiary);">
              Mode: {{ ai.agentType }}
            </div>
          </div>

          <div style="display: inline-flex; align-items: center; gap: var(--space-2);">
            <button
              type="button"
              class="button button-ghost"
              style="padding: 0.35rem 0.55rem;"
              @click="ai.resetConversation()"
            >
              Reset
            </button>
            <button
              type="button"
              class="button button-ghost"
              style="padding: 0.35rem 0.55rem;"
              @click="closePanel"
            >
              ×
            </button>
          </div>
        </header>

        <div
          ref="messagesEl"
          style="
            flex: 1;
            overflow-y: auto;
            padding: var(--space-5);
          "
        >
          <div v-if="!ai.messages.length" class="card" style="padding: var(--space-5);">
            <strong style="display: block; margin-bottom: var(--space-2);">
              Ask the assistant anything about venues, requests, inventory, tasks, or room design.
            </strong>
            <p style="margin: 0 0 var(--space-4); color: var(--text-secondary);">
              The assistant uses live backend data and tool calls, so responses are grounded in the current project state.
            </p>
            <div style="display: flex; flex-wrap: wrap; gap: var(--space-2);">
              <button
                v-for="prompt in quickPrompts"
                :key="prompt"
                type="button"
                class="button button-secondary"
                style="padding: 0.55rem 0.8rem; font-size: 0.86rem;"
                @click="draft = prompt"
              >
                {{ prompt }}
              </button>
            </div>
          </div>

          <AiMessage
            v-for="(message, index) in ai.messages"
            :key="`${message.timestamp}-${index}`"
            :message="message"
          />

          <div v-if="ai.loading" style="display: flex; justify-content: flex-start;">
            <div class="card" style="padding: 0.8rem 1rem;">
              <AiTypingIndicator />
            </div>
          </div>
        </div>

        <footer
          style="
            border-top: 1px solid var(--border);
            background: var(--surface);
            padding: var(--space-4) var(--space-5);
            display: flex;
            flex-direction: column;
            gap: var(--space-3);
          "
        >
          <textarea
            v-model="draft"
            class="textarea"
            rows="3"
            placeholder="Type a message for the AI..."
            @keydown.enter.exact.prevent="send"
          />
          <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--space-3);">
            <span style="font-size: 0.8rem; color: var(--text-tertiary);">
              Enter to send • Shift+Enter for new line
            </span>
            <button
              type="button"
              class="button button-primary"
              :disabled="!draft.trim() || ai.loading"
              @click="send"
            >
              Send
            </button>
          </div>
        </footer>
      </aside>
    </div>
  </Teleport>
</template>

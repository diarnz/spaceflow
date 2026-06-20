<script setup lang="ts">
import type { AiProposal } from '@/types'

defineProps<{
  proposal: AiProposal
}>()
</script>

<template>
  <section class="card" style="padding: var(--space-5);">
    <div style="display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-3);">
      <div style="display: inline-flex; align-items: center; gap: var(--space-2);">
        <span style="color: var(--accent); font-size: 1.2rem;">✦</span>
        <strong>AI Proposal</strong>
      </div>
      <span class="badge" :class="proposal.conflicts?.length ? 'badge-warning' : 'badge-success'">
        {{ proposal.conflicts?.length ? 'Needs attention' : 'Ready' }}
      </span>
    </div>

    <p v-if="proposal.summary" style="margin: 0 0 var(--space-4); color: var(--text-secondary); white-space: pre-wrap;">
      {{ proposal.summary }}
    </p>

    <div v-if="proposal.recommended_venue" style="margin-bottom: var(--space-4);">
      <div style="font-size: 0.82rem; color: var(--text-tertiary);">Recommended venue</div>
      <div style="font-weight: 700; margin-top: 0.15rem;">
        {{ proposal.recommended_venue.name ?? 'No venue found' }}
      </div>
      <div style="color: var(--text-secondary); margin-top: 0.3rem;">
        {{ proposal.recommended_venue.reason }}
      </div>
    </div>

    <div v-if="proposal.estimate" class="card" style="padding: var(--space-4); background: var(--bg-secondary);">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2);">
        <span style="color: var(--text-secondary);">Estimated total</span>
        <strong style="font-size: 1.15rem;">EUR {{ proposal.estimate.total.toFixed(2) }}</strong>
      </div>
      <div style="display: flex; justify-content: space-between; color: var(--text-tertiary); font-size: 0.9rem;">
        <span>Subtotal</span>
        <span>EUR {{ proposal.estimate.subtotal.toFixed(2) }}</span>
      </div>
      <div style="display: flex; justify-content: space-between; color: var(--text-tertiary); font-size: 0.9rem;">
        <span>Tax</span>
        <span>EUR {{ proposal.estimate.tax.toFixed(2) }}</span>
      </div>
    </div>
  </section>
</template>

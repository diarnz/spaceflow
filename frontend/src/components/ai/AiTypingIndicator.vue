<template>
  <div style="display: inline-flex; align-items: center; gap: 6px;">
    <span class="ai-dot" />
    <span class="ai-dot" style="animation-delay: 0.15s;" />
    <span class="ai-dot" style="animation-delay: 0.3s;" />
  </div>
</template>

<style scoped>
.ai-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  display: inline-block;
  animation: bounce 0.9s infinite ease-in-out;
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0.7);
    opacity: 0.45;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>

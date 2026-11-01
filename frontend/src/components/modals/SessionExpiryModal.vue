<template>
  <div class="modal-overlay">
    <div class="modal" role="alertdialog" aria-modal="true" aria-labelledby="session-expiry-title">
      <header class="modal-header">
        <Clock class="modal-icon" aria-hidden="true" />
        <h3 id="session-expiry-title">Your session is about to expire</h3>
      </header>

      <div class="modal-body">
        <p class="modal-text">
          You will be logged out in <strong class="countdown">{{ seconds }}</strong> seconds.
        </p>
        <div class="progress" aria-hidden="true">
          <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
        </div>
        <div class="actions">
          <button type="button" class="btn btn--secondary" @click="emit('logout')">Log out</button>
          <button type="button" class="btn btn--primary" :disabled="busy" @click="emit('extend')">
            Extend session
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Clock } from '@lucide/vue'

const props = defineProps({
  seconds: { type: Number, required: true },
  // Length of the warning window, used only to draw the progress bar.
  total: { type: Number, default: 60 },
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['extend', 'logout'])

const progress = computed(() => Math.max(0, Math.min(100, (props.seconds / props.total) * 100)))
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}

.modal {
  width: min(420px, 92vw);
  background: #2a2a2a;
  color: #f5f5f5;
  border: 1px solid #3a3a3a;
  border-radius: 18px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 20px;
  border-bottom: 1px solid #3a3a3a;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}

.modal-icon {
  width: 22px;
  height: 22px;
  color: #b79b58;
}

.modal-text {
  margin: 0;
  color: #dcdcdc;
  font-size: 0.95rem;
}

.countdown {
  color: #b79b58;
  font-variant-numeric: tabular-nums;
}

.progress {
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #b79b58;
  transition: width 1s linear;
}

.modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn {
  border-radius: 10px;
  padding: 10px 18px;
  font-size: 0.95rem;
  cursor: pointer;
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease,
    color 0.25s ease,
    transform 0.2s ease,
    box-shadow 0.25s ease;
}

.btn--secondary {
  background: transparent;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.25);
}

.btn--secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

.btn--primary {
  background: transparent;
  color: #fff;
  font-weight: 600;
  border: 2px solid rgba(183, 155, 88, 0.45);
}

.btn--primary:hover:not(:disabled) {
  background: #b79b58;
  border-color: #b79b58;
  color: #000;
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(183, 155, 88, 0.4);
}

.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>

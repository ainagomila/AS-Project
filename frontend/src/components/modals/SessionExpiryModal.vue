<template>
  <div class="modal-overlay">
    <div class="modal" role="alertdialog" aria-modal="true" aria-labelledby="session-expiry-title">
      <header class="modal-header">
        <h3 id="session-expiry-title">Your session is about to expire</h3>
      </header>

      <div class="modal-body">
        <p>You will be logged out in {{ seconds }} seconds.</p>
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
defineProps({
  seconds: { type: Number, required: true },
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['extend', 'logout'])
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}

.modal {
  width: min(420px, 92vw);
  background: #1e1e1e;
  color: #f5f5f5;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 20px 80px rgba(0, 0, 0, 0.6);
}

.modal-header {
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
  padding: 10px 16px;
  font-size: 0.95rem;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.btn--secondary {
  background: transparent;
  color: #f5f5f5;
}

.btn--primary {
  background: #f5f5f5;
  color: #1e1e1e;
}

.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>

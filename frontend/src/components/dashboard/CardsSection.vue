<template>
  <section class="cards-wrapper">
    <!-- Header -->
    <div class="cards-header">
      <h2 class="cards-title">Your Cards</h2>
      <div class="header-actions">
        <button class="add-card primary" @click="$emit('add-card')">
          <Plus class="icon" /> Add Card
        </button>
      </div>
    </div>

    <!-- Fila con scroll horizontal -->
    <div class="cards-row">
      <div
        v-for="card in cards"
        :key="card.id"
        class="card-item compact"
        @click="goToCardDetail(card)"
      >
        <div class="card-left">
          <!-- Tipo de tarjeta -->
          <div class="card-type">
            <CreditCard class="icon-sm" />
            {{ card.type }}
          </div>

          <!-- Número formateado -->
          <p class="card-number">{{ displayNumber(card) }}</p>

          <!-- Nombre de cuenta derivado del accountId -->
          <p class="meta-line">{{ accountNameOf(card.accountId) }} · {{ card.bank }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { Plus, CreditCard } from '@lucide/vue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/* === Props === */
const props = defineProps({
  cards: {
    type: Array,
    required: true,
    validator: (arr) => arr.every((c) => !!c.id && !!c.type),
  },
  accounts: {
    type: Array,
    required: true,
    validator: (arr) => arr.every((a) => !!a.id && !!a.name),
  },
})

/* === Emits === */
defineEmits(['add-card'])

/* Mapa reactivo de cuentas (para obtener el nombre desde el ID) */
const accountsById = computed(() => {
  const map = new Map()
  for (const a of props.accounts) map.set(a.id, a)
  return map
})

const accountNameOf = (id) => accountsById.value.get(id)?.name ?? 'Unknown'

/* Mostrar los últimos 4 dígitos */
const nbsp = '\u00A0'
const displayNumber = (card) => `••••${nbsp}••••${nbsp}••••${nbsp}${card.last4 || 'nnnn'}`

/* Navegar al detalle de la tarjeta */
const goToCardDetail = (card) => {
  router.push({
    name: 'CardDetail',
    params: { id: card.id }, // id = pan
  })
}
</script>

<style scoped>
.cards-wrapper {
  width: 100%;
  color: #f5f5f5;
  font-family: 'Satoshi', sans-serif;
  background: rgba(0, 0, 0, 0.4);
  padding: 24px 28px;
  border-radius: 20px;
  box-sizing: border-box;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 40px rgba(0, 0, 0, 0.3);
  overflow: visible;
}

.cards-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.cards-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #fff;
}
.header-actions {
  display: flex;
  gap: 12px;
}
.add-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 999px;
  font-weight: 700;
  border: none;
  cursor: pointer;
  transition: 0.25s;
  font-size: 0.95rem;
}
.add-card.primary {
  background: #fff;
  color: #000;
}
.add-card.primary:hover {
  background: #c9b26a;
  color: #fff;
}

.cards-row {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  overflow-y: visible;
  padding-block: 16px;
  padding-inline: 32px;
  scroll-padding-inline: 32px;
  scroll-snap-type: x mandatory;
}
.cards-row::-webkit-scrollbar {
  height: 8px;
}
.cards-row::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.18);
  border-radius: 999px;
}

.card-item {
  --card-w: 240px;
  flex: 0 0 auto;
  width: var(--card-w);
  aspect-ratio: 1.586 / 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  background-color: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 14px 18px;
  gap: 6px;
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease,
    border-color 0.25s ease,
    background-color 0.25s ease;
  backdrop-filter: blur(20px);
  scroll-snap-align: start;
  cursor: pointer;
  will-change: transform;
  transform-origin: center;
}
.card-item.compact {
  min-height: 0;
}

.card-item:hover {
  transform: translateY(-3px) scale(1.03);
  position: relative;
  z-index: 10;
  border-color: rgba(255, 255, 255, 0.25);
  background-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 14px 28px rgba(0, 0, 0, 0.35);
}
.cards-row .card-item:first-child:hover {
  transform-origin: left center;
}
.cards-row .card-item:last-child:hover {
  transform-origin: right center;
}

.card-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 15px;
}
.card-type {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.05rem;
  font-weight: 600;
}
.card-number {
  font-size: 0.95rem;
  color: rgba(220, 220, 220, 0.85);
  letter-spacing: 0.04em;
}
.meta-line {
  font-size: 0.85rem;
  color: rgba(200, 200, 200, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.icon {
  width: 16px;
  height: 16px;
}
.icon-sm {
  width: 18px;
  height: 18px;
}

@media (max-width: 640px) {
  .cards-row {
    padding-inline: 20px;
    scroll-padding-inline: 20px;
  }
  .card-item {
    --card-w: 220px;
  }
  .meta-line {
    max-width: 180px;
  }
}
</style>

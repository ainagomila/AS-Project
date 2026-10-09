<template>
  <!-- Bank Accounts Section -->
  <section class="accounts-wrapper">
    <!-- Header FIJO -->
    <div class="accounts-header">
      <div class="header-left">
        <h2 class="accounts-title">Your Bank Accounts</h2>
      </div>

      <!-- Botones de acción -->
      <div class="header-actions">
        <button class="add-account primary" @click="emitAddAccount">
          <Plus class="icon" /> Add Account
        </button>
      </div>
    </div>

    <!-- Lista de cuentas -->
    <div class="accounts-grid" ref="listEl" :style="listStyle">
      <div
        v-for="(account, i) in accounts"
        :key="account.id"
        class="account-card"
        :ref="(el) => { if (i === 0) firstCard = el }"
        @click="openAccount(account)"               
      >
        <div class="card-left">
          <div class="account-type">
            <Wallet class="icon-sm" />
            <span class="bank">{{ account.bank }}</span>
            <span class="dot">·</span>
            <span class="name">{{ account.name }}</span>
          </div>
          <div class="account-number">{{ account.number }}</div>
          <div class="account-meta">
            <span class="account-label">Available Balance</span>

            <span class="balance">
              {{ account.balance }}
              <span class="currency">{{ currencySymbol(account.currency) }}</span>
            </span>
          </div>

        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { Plus, Wallet } from "lucide-vue-next"
import { ref, onMounted, nextTick, onBeforeUnmount, watch } from "vue"
import { useRouter } from "vue-router"

/* --- Router --- */
const router = useRouter()
function openAccount(acc) {
  // Navega a la vista de detalle con el id de la cuenta
  router.push({ name: "AccountDetail", params: { id: acc.id } })
}

/* --- Props --- */
const props = defineProps({
  accounts: {
    type: Array,
    required: true,
    validator: (arr) => arr.every(a => !!a.id && !!a.bank && !!a.name),
  },
})

/* --- Emits --- */
const emit = defineEmits(["add-account"])
function emitAddAccount() {
  emit("add-account")
}

/* --- Scroll dinámico (mostrar 2 cuentas) --- */
const listEl = ref(null)
let firstCard = null
const listStyle = ref(null)

function measure() {
  if (!listEl.value || !firstCard) {
    listStyle.value = null
    return
  }
  const cardH = firstCard.getBoundingClientRect().height || 0
  const styles = getComputedStyle(listEl.value)
  const gap = parseFloat(styles.rowGap || styles.gap || "20") || 20
  let maxH = cardH * 2 + gap
  if (!maxH || maxH < 100) maxH = 380
  listStyle.value = { maxHeight: `${Math.round(maxH)}px`, overflowY: "auto" }
}

const onResize = () => requestAnimationFrame(measure)

onMounted(async () => {
  await nextTick()
  measure()
  window.addEventListener("resize", onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize)
})

watch(
  () => props.accounts,
  async () => {
    await nextTick()
    requestAnimationFrame(measure)
  },
  { immediate: true }
)

const currencySymbol = (code) => {
  switch (code) {
    case 'EUR': return '€'
    case 'USD': return '$'
    case 'GBP': return '£'
    default: return code   // fallback
  }
}
</script>




<style scoped>
/* Contenedor principal */
.accounts-wrapper {
  width: 100%;
  color: #f5f5f5;
  font-family: 'Satoshi', sans-serif;
  background: rgba(0, 0, 0, 0.4);
  padding: 32px;
  border-radius: 20px;
  box-sizing: border-box;
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 4px 40px rgba(0,0,0,0.3);
}

/* Header fijo */
.accounts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.accounts-title {
  font-size: 1.8rem;
  font-weight: 700;
  color: white;
}
.header-actions { display: flex; gap: 12px; }

/* BOTÓN */
.add-account {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 18px; border-radius: 999px;
  font-weight: 600; border: none; cursor: pointer;
  transition: all .25s ease; font-size: 0.95rem;
}
.add-account.primary { background: #fff; color: #111; }
.add-account.primary:hover { background: #c9b26a; color: #fff; }

/*Scroll vertical */
.accounts-grid {
  display: flex;
  flex-direction: column;
  row-gap: 20px;      
  padding-right: 6px;
  padding-top: 12px;
}
.accounts-grid::-webkit-scrollbar { width: 8px; }
.accounts-grid::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.18);
  border-radius: 999px;
}
.accounts-grid:hover::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.3);
}

/* TARJETA */
.account-card {
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px; padding: 24px 32px;
  transition: all .3s ease; backdrop-filter: blur(20px);
}
.account-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255,255,255,0.25);
  background: rgba(255,255,255,0.08);
  box-shadow: 0 0 12px rgba(255,255,255,0.1);
}

/* Cntenido Tarjeta */
.card-left { display: flex; flex-direction: column; gap: 6px; }
.account-type { display: flex; align-items: center; gap: 8px; font-size: 1.2rem; font-weight: 600; }
.account-type .bank { color: #e2e2e2; font-weight: 550; }
.account-type .dot { opacity: .7; }
.account-type .name { color: #fff; font-weight: 500; }
.account-number { font-size: .9rem; color: rgba(200,200,200,.7); letter-spacing: .04em; }
.account-meta { margin-top: 8px; display: flex; flex-direction: column; }
.account-label { font-size: .75rem; opacity: .6; }
.balance {
  font-size: 1.2rem; font-weight: 700; margin-top: 4px;
  background: linear-gradient(to right, #d5b76f, #f0d785, #d5b76f);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.card-right .details-btn {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 999px; padding: 8px; display: flex; align-items: center; justify-content: center;
  transition: all .25s ease; cursor: pointer;
}
.card-right .details-btn:hover {
  background: rgba(255,255,255,0.2);
  border-color: rgba(255,255,255,0.3);
}

.icon { width: 16px; height: 16px; }
.icon-sm { width: 18px; height: 18px; }


</style>

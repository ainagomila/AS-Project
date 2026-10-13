<template>
  <div class="page-container">
    <!-- HEADER -->
    <header class="fixed-header">
      <HeaderLayout title="Kofre">
      </HeaderLayout>
    </header>

    <!-- MAIN CONTENT -->
    <main class="scroll-content">
      <div class="sections-container">
        <!-- Functionalities / Others -->
        <section id="others" class="dashboard__section">
          <FunctionalitiesSection />
        </section>

        <!-- Accounts -->
        <section id="accounts" class="dashboard__section">
          <BankAccounts
            :accounts="accounts"
            @add-account="openAddModal"
          />
        </section>

        <!-- Cards -->
        <section id="cards" class="dashboard__section">
          <CardsSection
            :cards="cards"
            :accounts="accounts"
            @add-card="openAddCardModal"
          />
        </section>
      </div>

      <!-- FOOTER -->
      <footer class="fixed-footer">
        <FooterLayout />
      </footer>
    </main>

    <!-- MODAL: Add account -->
    <AddAccountModal
      v-if="showAddModal"
      :saving="isSaving"
      @close="showAddModal = false"
      @submit="handleCreateAccount"
    />

    <!-- MODAL: Add card -->
    <AddCardModal
      v-if="showAddCardModal"
      :saving="isSavingCard"
      :accounts="accounts"
      @close="showAddCardModal = false"
      @submit="handleCreateCard"
    />
  </div>
</template>

<script setup>
  import HeaderLayout from '@/components/layout/HeaderLayout.vue'
  import FooterLayout from '@/components/layout/FooterLayout.vue'
  import BankAccounts from '@/components/dashboard/BankAccounts.vue'
  import CardsSection from '@/components/dashboard/CardsSection.vue'
  import FunctionalitiesSection from '@/components/dashboard/FunctionalitiesSection.vue'
  import AddAccountModal from '@/components/modals/AddAccountModal.vue'
  import AddCardModal from '@/components/modals/AddCardModal.vue'
  
  import { ref, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { getAccounts, getCards, addAccount, addCard } from '@/api/userService.js'
  import { useUserStore } from '@/stores/user'
  
  // Router + store
  const router = useRouter()
  const userStore = useUserStore()
  
  // Estado
  const accounts = ref([])
  const cards = ref([])
  
  const showAddModal = ref(false)
  const showAddCardModal = ref(false)
  
  const isSaving = ref(false)
  const isSavingCard = ref(false)
  
  // Helpers IBAN
  const normalizeAccountIban = (v) =>
    String(v ?? '').replaceAll(/\s+/g, '').toUpperCase()
  
  const digits = (s) => (s ?? '').toString().replace(/\D/g, '')
  
  const formatIban = (s) =>
    !s
      ? '—'
      : String(s)
          .replaceAll(/\s+/g, '')
          .replace(/(.{4})/g, '$1 ')
          .trim()
  
  // Mapping de cuentas
  const mapAccount = (a) => {
    const iban = normalizeAccountIban(a.iban)
    const balanceNumber =
      typeof a.balance === 'number' ? a.balance : Number(a.balance ?? 0)
  
    return {
      id: iban,
      bank: a.bank,
      name: a.name,
      iban,
      number: formatIban(iban),
      balance: balanceNumber,
      currency: (a.currency || 'EUR').toUpperCase(),
    }
  }
  
  // Mapping de tarjetas
  const mapCard = (c) => {
    const pan = String(c.pan ?? '').replace(/\s+/g, '')
    const raw = pan || digits(c.last4 ?? '')
    const last4 = (raw || '').slice(-4)
  
    const iban = normalizeAccountIban(c.iban)
  
    return {
      id: pan || c.id || last4,
      pan,
      type: c.type ?? c.brand ?? 'CARD',
      last4: last4 || '••••',
      bank: c.bank ?? '—',
      accountId: iban,
      iban,
      alias: c.alias ?? '—',
      status: c.status ?? 'UNKNOWN',
    }
  }
  
  // Inicialización
  onMounted(async () => {
    userStore.initFromStorage()
  
    if (!userStore.isAuthenticated || !userStore.dni) {
      router.push('/login')
      return
    }
  
    try {
      const accData = await getAccounts(userStore.dni)
      accounts.value = accData.map(mapAccount)
    } catch (e) {
      console.error('GET accounts ERROR ➜', e.response?.data || e)
      alert('Error loading your bank accounts.')
      return
    }
  
    try {
      const cardData = await getCards(userStore.dni)
      cards.value = (cardData || []).map(mapCard)
    } catch (e) {
      console.error('GET Cards ERROR ➜', e.response?.data || e)
      alert('Error loading your cards.')
      return
    }
  })
  
  // Refrescar cuentas
  async function refreshAccounts() {
    const data = await getAccounts(userStore.dni)
    accounts.value = data.map(mapAccount)
  }
  
  // Abrir modales
  function openAddModal() {
    showAddModal.value = true
  }
  
  function openAddCardModal() {
    showAddCardModal.value = true
  }
  
  // Crear cuenta
  async function handleCreateAccount(body) {
    try {
      isSaving.value = true
      await addAccount(userStore.dni, body)
      await refreshAccounts()
      showAddModal.value = false
    } catch (error) {
      console.error('Error creating account:', error)
  
      const status = error?.response?.status
      const code = error?.response?.data?.code
  
      // 409 desde BE: ACCOUNT_ALREADY_EXISTS -> mensaje SIEMPRE en inglés
      if (status === 409 && code === 'ACCOUNT_ALREADY_EXISTS') {
        alert('This account already exists.')
      } else {
        alert('Could not create the account.')
      }
    } finally {
      isSaving.value = false
    }
  }
  
  // Crear tarjeta
  async function handleCreateCard({ iban, body }) {
    try {
      isSavingCard.value = true
      const created = await addCard(userStore.dni, iban, body)
      cards.value.push(mapCard(created))
      showAddCardModal.value = false
    } catch (error) {
      const message =
        error.response?.data?.message || 'Could not create the card.'
      alert(message)
    } finally {
      isSavingCard.value = false
    }
  }
  
  </script>
  

<style scoped>
/* Fondo global */
:global(html, body) {
  background-color: #222;
  margin: 0;
  padding: 0;
}

/*  BASE LAYOUT */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  font-family: 'Satoshi', sans-serif;
  color: #f5f5f5;
  overflow: hidden;
  background-color: #222;
}

/* HEADER  */
.fixed-header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
}

/* NAV */
.left-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}
.header-link,
.lang {
  font-weight: 500;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.95rem;
  cursor: pointer;
  transition:
    color 0.25s,
    transform 0.25s;
}
.header-link:hover,
.lang:hover {
  color: #c9b26a;
  transform: scale(1.08);
}

/* RIGHT HEADER BUTTONS */
.header-buttons {
  display: flex;
  align-items: center;
  gap: 14px;
}
.icon-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 8px;
  cursor: pointer;
  transition: all 0.3s;
}
.icon-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}
.icon {
  width: 18px;
  height: 18px;
  color: #f5f5f5;
}

/* LOGOUT BUTTON */
.logout-btn {
  background: linear-gradient(90deg, #d5b76f, #f0d785, #d5b76f);
  color: #000;
  border-radius: 999px;
  padding: 8px 18px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}
.logout-btn:hover {
  background: linear-gradient(90deg, #f0d785, #d5b76f, #f0d785);
  transform: translateY(-1px);
}

/* MAIN CONTENT */
.scroll-content {
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
  padding-top: 70px;
}

.sections-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 40px 20px;
  gap: 40px;
}

/* SECTIONS */
.dashboard__section {
  max-width: 1000px;
  width: 100%;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 40px rgba(0, 0, 0, 0.3);
  padding: 12px;
  transition: all 0.3s ease;
}
.dashboard__section:hover {
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 60px rgba(255, 255, 255, 0.06);
}

/*  FOOTER  */
.fixed-footer {
  width: 100%;
  backdrop-filter: none;
  bottom: 0;
  left: 0;
  padding-top: 100px;
}
</style>

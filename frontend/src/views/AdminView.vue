<template>
  <div class="page-container">
    <header class="fixed-header">
      <HeaderLayout title="Kofre" />
    </header>

    <main class="scroll-content">
      <section v-if="userStore.isAdmin || userStore.isAuditor" class="admin-section">
        <h2 class="admin-title">Users</h2>
        <p class="admin-note" data-testid="admin-role-note">
          <template v-if="userStore.isAuditor">
            Auditor view: personal data is pseudonymised and nothing can be changed.
          </template>
          <template v-else-if="userStore.isAdmin">
            Administrator view: you can enable or disable customers. Balances and transfers are only
            visible to auditors.
          </template>
          <template v-else>
            Operations view: you can block or reactivate accounts and cards. Balances and transfers
            are not available here.
          </template>
        </p>
        <p v-if="error" class="admin-error" data-testid="admin-error">{{ error }}</p>

        <table class="admin-table" data-testid="admin-users">
          <thead>
            <tr>
              <th>DNI</th>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Role</th>
              <th>Status</th>
              <th v-if="userStore.isAdmin"></th>
              <th v-if="userStore.isAdmin"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in users"
              :key="user.id"
              :class="{ selected: selectedUser?.id === user.id, clickable: userStore.isAuditor }"
              @click="selectUser(user)"
            >
              <td>{{ user.dni }}</td>
              <td>{{ user.name }}</td>
              <td>{{ user.email }}</td>
              <td>{{ user.phone }}</td>
              <td>{{ roleLabel(user.role) }}</td>
              <td>{{ user.active ? 'Active' : 'Disabled' }}</td>
              <td v-if="userStore.isAdmin">
                <button
                  class="admin-btn"
                  :disabled="user.role !== 'customer'"
                  :title="user.role !== 'customer' ? 'Staff accounts cannot be disabled' : ''"
                  @click.stop="toggleActive(user)"
                >
                  {{ user.active ? 'Disable' : 'Enable' }}
                </button>
              </td>
              <td v-if="userStore.isAdmin">
                <button
                  class="admin-btn danger"
                  :disabled="user.role !== 'customer'"
                  @click.stop="removeUser(user)"
                >
                  Delete
                </button>
                <button
                  class="admin-btn"
                  :disabled="user.role !== 'customer'"
                  @click.stop="resetPassword(user)"
                >
                  Reset password
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="userStore.isOperations" class="admin-section">
        <h2 class="admin-title">Operational product controls</h2>
        <p v-if="error" class="admin-error">{{ error }}</p>
        <h3>Accounts</h3>
        <table class="admin-table">
          <thead><tr><th>IBAN</th><th>Status</th><th>Reason</th><th>Change</th></tr></thead>
          <tbody>
            <tr v-for="account in operationAccounts" :key="account.id">
              <td>{{ account.iban }}</td>
              <td>{{ account.status }}</td>
              <td>{{ account.reason || '—' }}</td>
              <td>
                <select v-model="account.nextStatus">
                  <option value="ACTIVE">Active</option>
                  <option value="FROZEN">Frozen</option>
                  <option value="CLOSED">Closed</option>
                </select>
                <input v-model="account.nextReason" maxlength="255" placeholder="Reason" />
                <button class="admin-btn" @click="changeAccountStatus(account)">Save</button>
              </td>
            </tr>
          </tbody>
        </table>
        <h3>Cards</h3>
        <table class="admin-table">
          <thead><tr><th>Card</th><th>IBAN</th><th>Status</th><th>Reason</th><th>Change</th></tr></thead>
          <tbody>
            <tr v-for="card in operationCards" :key="card.id">
              <td>•••• {{ card.last4 }}</td>
              <td>{{ card.iban }}</td>
              <td>{{ card.status }}</td>
              <td>{{ card.reason || '—' }}</td>
              <td>
                <select v-model="card.nextStatus">
                  <option value="ACTIVE">Active</option>
                  <option value="FREEZED">Frozen</option>
                  <option value="DEAD">Cancelled</option>
                </select>
                <input v-model="card.nextReason" maxlength="255" placeholder="Reason" />
                <button class="admin-btn" @click="changeCardStatus(card)">Save</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="userStore.isAdmin" class="admin-section">
        <h2 class="admin-title">Create customer</h2>
        <form class="admin-form" @submit.prevent="createCustomer">
          <input v-model="newUser.name" placeholder="Name" required />
          <input v-model="newUser.dni" placeholder="DNI" required />
          <input v-model="newUser.email" type="email" placeholder="Email" required />
          <input v-model="newUser.phone" placeholder="+34600123456" required />
          <input v-model="newUser.password" type="password" placeholder="Password" required />
          <input v-model="newUser.birthdate" type="date" required />
          <input v-model="newUser.gender" placeholder="Gender" required />
          <input v-model="newUser.pin" type="password" inputmode="numeric" placeholder="PIN" required />
          <button class="admin-btn" type="submit">Create</button>
        </form>
      </section>

      <section v-if="selectedUser" class="admin-section">
        <h2 class="admin-title">Accounts of {{ selectedUser.name }}</h2>
        <p v-if="!accounts.length" class="admin-empty">No accounts.</p>
        <table v-else class="admin-table" data-testid="admin-accounts">
          <thead>
            <tr>
              <th>IBAN</th>
              <th>Name</th>
              <th>Bank</th>
              <th>Balance</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="account in accounts"
              :key="account.id"
              :class="{ selected: selectedAccount?.id === account.id, clickable: true }"
              @click="selectAccount(account)"
            >
              <td>{{ account.iban }}</td>
              <td>{{ account.name }}</td>
              <td>{{ account.bank }}</td>
              <td>{{ formatAmount(account.balance, account.currency) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="selectedAccount" class="admin-section">
        <h2 class="admin-title">Transfers of {{ selectedAccount.iban }}</h2>
        <p v-if="!transfers.length" class="admin-empty">No transfers.</p>
        <table v-else class="admin-table" data-testid="admin-transfers">
          <thead>
            <tr>
              <th>Date</th>
              <th>Concept</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(transfer, index) in transfers" :key="index">
              <td>{{ formatDate(transfer.date) }}</td>
              <td>{{ transfer.title }}</td>
              <td>{{ formatAmount(transfer.amount, transfer.currency) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="userStore.isAuditor" class="admin-section">
        <h2 class="admin-title">Audit trail</h2>
        <p v-if="!events.length" class="admin-empty">No events.</p>
        <table v-else class="admin-table" data-testid="admin-audit">
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Decision</th>
              <th>Rule</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(event, index) in events" :key="index">
              <td>{{ formatDate(event.at) }}</td>
              <td>{{ event.subjectRole }} {{ shortId(event.subjectId) }}</td>
              <td>{{ event.action }}</td>
              <td>{{ event.resourceType }} {{ shortId(event.resourceId) }}</td>
              <td :class="event.decision === 'Permit' ? 'permit' : 'deny'">{{ event.decision }}</td>
              <td>{{ event.rule.replace('urn:kofre:rule:', '') }}</td>
              <td>{{ event.status }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import HeaderLayout from '@/components/layout/HeaderLayout.vue'
import { useUserStore } from '@/stores/user'
import {
  getAllUsers,
  createUser,
  setUserActive,
  resetUserPassword,
  deleteUser,
  getUserAccounts,
  getAccountTransfers,
  getAuditLog,
  getOperationsAccounts,
  setOperationsAccountStatus,
  getOperationsCards,
  setOperationsCardStatus,
} from '@/api/adminService.js'

const userStore = useUserStore()

const users = ref([])
const accounts = ref([])
const transfers = ref([])
const events = ref([])
const operationAccounts = ref([])
const operationCards = ref([])
const selectedUser = ref(null)
const selectedAccount = ref(null)
const error = ref('')
const newUser = ref({
  name: '',
  dni: '',
  email: '',
  phone: '',
  password: '',
  birthdate: '',
  gender: '',
  pin: '',
})

const ROLE_LABELS = { customer: 'Customer', admin: 'Admin', auditor: 'Auditor', operations: 'Operations' }

function roleLabel(role) {
  return ROLE_LABELS[role] ?? role
}

function shortId(id) {
  return id ? `…${id.slice(-6)}` : ''
}

function describe(e) {
  return e.response?.data?.message || e.message || 'Unexpected error'
}

async function loadUsers() {
  error.value = ''
  try {
    users.value = await getAllUsers()
  } catch (e) {
    error.value = describe(e)
  }
}

async function loadAudit() {
  try {
    events.value = await getAuditLog()
  } catch (e) {
    error.value = describe(e)
  }
}

// Only auditors can follow the money; for administrators the policy denies it.
async function selectUser(user) {
  if (!userStore.isAuditor) return
  selectedUser.value = user
  selectedAccount.value = null
  transfers.value = []
  error.value = ''
  try {
    accounts.value = await getUserAccounts(user.id)
  } catch (e) {
    accounts.value = []
    error.value = describe(e)
  }
}

async function selectAccount(account) {
  selectedAccount.value = account
  error.value = ''
  try {
    transfers.value = await getAccountTransfers(selectedUser.value.id, account.id)
  } catch (e) {
    transfers.value = []
    error.value = describe(e)
  }
}

async function toggleActive(user) {
  error.value = ''
  try {
    const updated = await setUserActive(user.id, !user.active)
    user.active = updated.active
  } catch (e) {
    error.value = describe(e)
  }
}

async function resetPassword(user) {
  const password = window.prompt('Enter a new temporary password')
  if (!password) return
  try {
    await resetUserPassword(user.id, password)
  } catch (e) {
    error.value = describe(e)
  }
}

async function removeUser(user) {
  if (!window.confirm(`Delete ${user.name}? This removes their accounts and cards.`)) return
  try {
    await deleteUser(user.id)
    users.value = users.value.filter((candidate) => candidate.id !== user.id)
  } catch (e) {
    error.value = describe(e)
  }
}

async function createCustomer() {
  try {
    const created = await createUser({ ...newUser.value, role: 'customer', active: true })
    users.value.push(created)
    newUser.value = {
      name: '',
      dni: '',
      email: '',
      phone: '',
      password: '',
      birthdate: '',
      gender: '',
      pin: '',
    }

  } catch (e) {
    error.value = describe(e)
  }
}

async function loadOperations() {
  try {
    operationAccounts.value = (await getOperationsAccounts()).map((item) => ({
      ...item,
      nextStatus: item.status,
      nextReason: item.reason || '',
    }))
    operationCards.value = (await getOperationsCards()).map((item) => ({
      ...item,
      nextStatus: item.status,
      nextReason: item.reason || '',
    }))
  } catch (e) {
    error.value = describe(e)
  }
}

async function changeAccountStatus(account) {
  try {
    Object.assign(account, await setOperationsAccountStatus(account.id, account.nextStatus, account.nextReason))
  } catch (e) {
    error.value = describe(e)
  }
}

async function changeCardStatus(card) {
  try {
    Object.assign(card, await setOperationsCardStatus(card.id, card.nextStatus, card.nextReason))
  } catch (e) {
    error.value = describe(e)
  }
}

function formatAmount(amount, currency) {
  return `${Number(amount).toFixed(2)} ${currency || 'EUR'}`
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : ''
}

onMounted(async () => {
  if (userStore.isAdmin || userStore.isAuditor) await loadUsers()
  if (userStore.isAuditor) await loadAudit()
  if (userStore.isOperations) await loadOperations()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  font-family: 'Satoshi', sans-serif;
  background-color: #222;
  color: #fff;
}

.scroll-content {
  flex: 1;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.admin-section {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-sizing: border-box;
  overflow-x: auto;
}

.admin-title {
  margin: 0 0 12px;
  font-size: 1.2rem;
  font-weight: 700;
  color: #f0d785;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.admin-table th,
.admin-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.admin-table tbody tr.clickable {
  cursor: pointer;
}

.admin-table tbody tr.clickable:hover,
.admin-table tbody tr.selected {
  background: rgba(255, 255, 255, 0.08);
}

.admin-btn {
  padding: 4px 12px;
  border-radius: 12px;
  border: 1px solid #d5b76f;
  background: transparent;
  color: #f0d785;
  cursor: pointer;
}

.admin-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.admin-btn.danger {
  border-color: #ff8a80;
  color: #ff8a80;
}

.admin-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
}

.admin-form input {
  min-width: 0;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: #333;
  color: #fff;
}

.admin-section select {
  min-width: 100px;
  padding: 6px 28px 6px 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background-color: #333;
  color: #fff;
  color-scheme: dark;
}

.admin-section select option {
  background-color: #333;
  color: #fff;
}

.admin-error {
  color: #ff8a80;
  margin-bottom: 12px;
}

.admin-empty {
  opacity: 0.7;
}

.admin-note {
  margin: 0 0 12px;
  opacity: 0.75;
  font-size: 0.9rem;
}

.permit {
  color: #9be29b;
}

.deny {
  color: #ff8a80;
}
</style>

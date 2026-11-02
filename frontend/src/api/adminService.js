import apiClient from './apiClient'

/* ====================================
   ADMIN / STAFF API
   Solo usuarios con rol ADMIN o AUDITOR.
   Las operaciones de escritura (POST/PATCH/DELETE)
   solo las permite el backend con rol ADMIN.
==================================== */

function encode(value) {
  return encodeURIComponent(value ?? '')
}

/* ---------------------------- Users ---------------------------- */

export async function getAllUsers() {
  const { data } = await apiClient.get('/admin/users')
  return Array.isArray(data) ? data : []
}

export async function createUser(payload) {
  const { data } = await apiClient.post('/admin/users', payload)
  return data
}

export async function getUserDetail(dni) {
  const { data } = await apiClient.get(`/admin/users/${encode(dni)}`)
  return data
}

export async function setUserActive(dni, active) {
  const { data } = await apiClient.patch(`/admin/users/${encode(dni)}`, { active })
  return data
}

export async function setUserRole(dni, role) {
  const { data } = await apiClient.patch(`/admin/users/${encode(dni)}`, { role })
  return data
}

export async function deleteUser(dni) {
  await apiClient.delete(`/admin/users/${encode(dni)}`)
  return true
}

export async function resetUserPassword(dni, newPassword) {
  const { data } = await apiClient.post(`/admin/users/${encode(dni)}/reset-password`, {
    newPassword,
  })
  return data
}

/* ---------------------------- Accounts ---------------------------- */

export async function getUserAccounts(dni) {
  const { data } = await apiClient.get(`/admin/users/${encode(dni)}/accounts`)
  return data?.accounts ?? []
}

export async function getAllAccounts() {
  const { data } = await apiClient.get('/admin/accounts')
  return data?.accounts ?? []
}

export async function setAccountStatus(iban, status) {
  const { data } = await apiClient.patch(`/admin/accounts/${encode(iban)}`, { status })
  return data
}

/* ---------------------------- Cards ---------------------------- */

export async function getUserCards(dni) {
  const { data } = await apiClient.get(`/admin/users/${encode(dni)}/cards`)
  return data?.cards ?? []
}

export async function getAllCards() {
  const { data } = await apiClient.get('/admin/cards')
  return data?.cards ?? []
}

export async function setCardStatus(pan, status) {
  const { data } = await apiClient.patch(`/admin/cards/${encode(pan)}`, { status })
  return data
}

export async function deleteCard(pan) {
  await apiClient.delete(`/admin/cards/${encode(pan)}`)
  return true
}

/* ---------------------------- Transfers ---------------------------- */

export async function getAccountTransfers(dni, iban) {
  const { data } = await apiClient.get(
    `/admin/users/${encode(dni)}/accounts/${encode(iban)}/transfers`,
  )
  return data?.transfers ?? []
}

export async function getAllTransfers() {
  const { data } = await apiClient.get('/admin/transfers')
  return data?.transfers ?? []
}

/* ---------------------------- Audit log ---------------------------- */

export async function getAuditLogs() {
  const { data } = await apiClient.get('/admin/audit-logs')
  return data?.auditLogs ?? []
}

/* ---------------------------- Settings ---------------------------- */

export async function getSettings() {
  const { data } = await apiClient.get('/admin/settings')
  return data?.settings ?? []
}

export async function updateSetting(key, value) {
  const { data } = await apiClient.patch(`/admin/settings/${encode(key)}`, { value })
  return data
}

/* ---------------------------- Stats ---------------------------- */

export async function getStats() {
  const { data } = await apiClient.get('/admin/stats')
  return data
}

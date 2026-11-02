import apiClient from './apiClient'

/* ====================================
   BACK OFFICE (administradores y auditores)
   Users and accounts are addressed by internal ids, never by DNI or IBAN.
   What each role may call is decided by the backend's XACML policy.
==================================== */

export async function getAllUsers() {
  const { data } = await apiClient.get('/admin/users')
  return Array.isArray(data) ? data : []
}

export async function createUser(payload) {
  const { data } = await apiClient.post('/admin/users', payload)
  return data
}

export async function setUserActive(userId, active) {
  const { data } = await apiClient.patch(`/admin/users/${encodeURIComponent(userId)}`, { active })
  return data
}

export async function resetUserPassword(userId, newPassword) {
  const { data } = await apiClient.post(`/admin/users/${encodeURIComponent(userId)}`, { newPassword })
  return data
}

export async function deleteUser(userId) {
  await apiClient.delete(`/admin/users/${encodeURIComponent(userId)}`)
}

export async function getUserAccounts(userId) {
  const { data } = await apiClient.get(`/admin/users/${encodeURIComponent(userId)}/accounts`)
  return data?.accounts ?? []
}

export async function getAccountTransfers(userId, accountId) {
  const { data } = await apiClient.get(
    `/admin/users/${encodeURIComponent(userId)}/accounts/${encodeURIComponent(accountId)}/transfers`,
  )
  return data?.transfers ?? []
}

export async function getAuditLog() {
  const { data } = await apiClient.get('/admin/audit')
  return data?.events ?? []
}

export async function getOperationsAccounts() {
  const { data } = await apiClient.get('/operations/accounts')
  return data?.accounts ?? []
}

export async function setOperationsAccountStatus(accountId, status, reason) {
  const { data } = await apiClient.patch(`/operations/accounts/${encodeURIComponent(accountId)}`, {
    status,
    reason,
  })
  return data
}

export async function getOperationsCards() {
  const { data } = await apiClient.get('/operations/cards')
  return data?.cards ?? []
}

export async function setOperationsCardStatus(cardId, status, reason) {
  const { data } = await apiClient.patch(`/operations/cards/${encodeURIComponent(cardId)}`, {
    status,
    reason,
  })
  return data
}

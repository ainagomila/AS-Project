import apiClient from './apiClient'

/* ====================================
   ADMIN
   Solo usuarios con rol administrador
==================================== */

export async function getAllUsers() {
  const { data } = await apiClient.get('/admin/users')
  return Array.isArray(data) ? data : []
}

export async function setUserActive(dni, active) {
  const { data } = await apiClient.patch(`/admin/users/${encodeURIComponent(dni)}`, { active })
  return data
}

export async function getUserAccounts(dni) {
  const { data } = await apiClient.get(`/admin/users/${encodeURIComponent(dni)}/accounts`)
  return data?.accounts ?? []
}

export async function getAccountTransfers(dni, iban) {
  const { data } = await apiClient.get(
    `/admin/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(iban)}/transfers`,
  )
  return data?.transfers ?? []
}

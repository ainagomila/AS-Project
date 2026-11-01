// src/api/userService.js
import apiClient from './apiClient'

/* ====================================
   PERFIL
==================================== */
export async function getUser(dni) {
  const { data } = await apiClient.get(`/users/${encodeURIComponent(dni)}`)
  // data tendrá: dni, name, email, phone, birthday/birthdate, gender, pin
  return data
}

/**
 * PATCH /users/{dni}
 * Se usará para actualizar email y/o phone, pasando también pin en el payload.
 * Ejemplo body:
 * { pin: "123456", email: "...", phone: "..." }
 */
export async function updateUser(dni, payload) {
  const { data } = await apiClient.patch(`/users/${encodeURIComponent(dni)}`, payload)
  return data
}

/**
 * ELIMINAR USUARIO (borrar perfil)
 * DELETE /users/{dni}
 * Body: { pin: "123456" }
 */
export async function deleteUser(dni, payload) {
  await apiClient.delete(`/users/${encodeURIComponent(dni)}`, {
    data: payload,
  })
  return true
}



/* ====================================
   SECURITY (PIN / PASSWORD)
==================================== */

/**
 * Verificar PIN
 * POST /users/{dni}/security/verify-pin
 * Body: { pin }
 * Response 200: { pin: "123456" }
 */
export async function verifyPin(dni, pin) {
  const { data } = await apiClient.post(`/users/${encodeURIComponent(dni)}/security/verify-pin`, {
    pin,
  })
  // si ha ido bien, devolvemos el objeto; el caller puede usar data.pin o ignorarlo
  return data
}

/**
 * Verificar password (usando el PIN)
 * POST /users/{dni}/security/verify-password
 * Body: { pin }
 * Response 200: { password: "..." }
 */
export async function verifyPassword(dni, pin) {
  const { data } = await apiClient.post(
    `/users/${encodeURIComponent(dni)}/security/verify-password`,
    { pin },
  )
  return data // { password: "..." }
}

/**
 * Cambiar contraseña
 * PATCH /users/{dni}
 * Body: { pin: "123456", password: "MuySegura_2025" }
 */
export async function changePassword(dni, { pin, newPassword }) {
  await apiClient.patch(`/users/${encodeURIComponent(dni)}`, {
    pin,
    password: newPassword,
  })
  return true
}

/**
 * Cambiar PIN
 * PATCH /users/{dni}
 * Body: { pin: "123456", newPin: "654321" }
 */
export async function changePin(dni, { pin, newPin }) {
  await apiClient.patch(`/users/${encodeURIComponent(dni)}`, {
    pin,
    newPin,
  })
  return true
}

/* ====================================
   ACCOUNTS
   Identificador de cuenta concreta: IBAN
==================================== */

/**
 * Lista TODAS las cuentas de un usuario.
 * Respuesta: array (puede ser []).
 */
// Lista TODAS las cuentas de un usuario.
// El BE devuelve { accounts: [...] }
export async function getAccounts(dni) {
  const { data } = await apiClient.get(`/users/${encodeURIComponent(dni)}/accounts`)

  // Caso ideal: el BE ya devuelve un array
  if (Array.isArray(data)) {
    return data
  }

  // Caso real: el BE devuelve { accounts: [...] }
  if (data && Array.isArray(data.accounts)) {
    return data.accounts
  }

  console.warn('Formato inesperado en GET /accounts:', data)
  return []
}

/**
 * Obtiene una cuenta concreta usando su IBAN.
 */
export async function getAccount(dni, iban) {
  const { data } = await apiClient.get(
    `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(iban)}`,
  )
  return data
}

/**
 * Crea una nueva cuenta.
 * account = { iban, name, bank, currency }; new accounts open at 0
 */
export async function addAccount(dni, account) {
  const { data } = await apiClient.post(`/users/${encodeURIComponent(dni)}/accounts`, account)
  return data
}

/**
 * Actualiza una cuenta concreta identificada por su IBAN.
 * Ejemplo PATCH body: { name: "Ahorro viaje" }
 */
export async function updateAccount(dni, iban, payload) {
  const { data } = await apiClient.patch(
    `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(iban)}`,
    payload,
  )
  return data
}

/**
 * DELETE /users/{dni}/accounts/{iban}
 * Body: { pin: "123456" }
 */
export async function deleteAccount(dni, iban, pin) {
  await apiClient.delete(`/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(iban)}`, {
    data: { pin },
  })
  return true
}

/* ====================================
   CARDS
   Identificador de tarjeta: PAN (card number sin espacios)
==================================== */

/**
 * ADD CARD
 * POST /users/{dni}/accounts/{iban}/cards
 */
export async function addCard(dni, iban, payload) {
  const res = await apiClient.post(
    `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(iban)}/cards`,
    {
      pan: String(payload.pan).replace(/\s+/g, ''), // sin espacios
      expireDate: payload.expireDate, // "MM/YY"
      alias: payload.alias ?? null,
      cvv: payload.cvv,
      pin: payload.pin,
      type: payload.type,
      bank: payload.bank,
    },
  )

  return res.data
}

/**
 * GET USER CARDS
 * GET /users/{dni}/cards
 * Se intenta normalizar la respuesta a SIEMPRE un array.
 */
export async function getCards(dni) {
  const { data } = await apiClient.get(`/users/${encodeURIComponent(dni)}/cards`)

  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.cards)) return data.cards

  console.warn('Formato inesperado en GET /users/{dni}/cards:', data)
  return []
}

/**
 * GET ACCOUNT CARDS
 * GET /users/{dni}/accounts/{iban}/cards
 */
export async function getAccountCards(dni, iban) {
  const res = await apiClient.get(
    `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(iban)}/cards`,
  )
  return res.data
}

/**
 * GET CARD POR IBAN + PAN (lo dejo por si lo usáis en otro sitio)
 * GET /users/{dni}/accounts/{iban}/cards/{pan}
 */
export async function getCard(dni, iban, pan) {
  const normalizedPan = String(pan).replace(/\s+/g, '')
  const res = await apiClient.get(
    `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(
      iban,
    )}/cards/${encodeURIComponent(normalizedPan)}`,
  )
  return res.data
}

/**
 * GET CARD BY PAN (helper para CardDetail)
 * Busca dentro de /users/{dni}/cards el que tenga ese PAN
 */
export async function getCardByPan(dni, pan) {
  const normalizedPan = String(pan).replace(/\s+/g, '')
  const cards = await getCards(dni)

  const found = cards.find((c) => String(c.pan).replace(/\s+/g, '') === normalizedPan)

  return found || null
}

/**
 * VERIFY CARD
 * POST /users/{dni}/security/verify-card
 */

export async function verifyCard(dni, accountId, pan, pin) {
  const url = `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(accountId)}/cards/${encodeURIComponent(pan)}/security/verify-card`


  const res = await apiClient.post(url, { pin })

  return res.data
}
/**
 * DELETE CARD
 * DELETE /users/{dni}/cards/{pan}
 * Body: { pin: "123456" }
 */
export async function deleteCard(dni, iban, pan, pin) {
  const cleanIban = String(iban).replace(/\s+/g, '')
  const cleanPan = String(pan).replace(/\s+/g, '')

  const url = `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(cleanIban)}/cards/${encodeURIComponent(cleanPan)}`

  return apiClient.delete(url, {
    data: { pin },
  })
}

/**
 * UPDATE CARD (alias, status…)
 * PATCH /users/{dni}/cards/{pan}
 */
export async function updateCard(dni, iban, pan, payload) {
  const { data } = await apiClient.patch(
    `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(iban)}/cards/${encodeURIComponent(pan)}`,
    payload,
  )

  return data
}
/**
 * CREATE TRANSFER
 * POST /users/{dni}/accounts/{accountId}/transfers
 */
export async function createTransfer(dni, accountId, payload) {
  const res = await apiClient.post(
    `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(accountId)}/transfers`,
    payload,
  )
  return res.data
}

export async function getTransfers(dni, iban, query = {}) {
  try {
    const cleanIban = String(iban).replace(/\s+/g, '')

    const params = {}

    if (query.q) params.q = query.q
    if (query.onlyExpenses !== undefined) params.onlyExpenses = query.onlyExpenses
    if (query.from) params.from = query.from
    if (query.to) params.to = query.to
    if (query.sort) params.sort = query.sort

    console.log('API Call:', {
      dni,
      iban: cleanIban,
      params,
    })

    const { data } = await apiClient.get(
      `/users/${encodeURIComponent(dni)}/accounts/${encodeURIComponent(cleanIban)}/transfers`,
      { params },
    )

    console.log('API Response:', data)

    // Caso ideal: array directo
    if (Array.isArray(data)) {
      return data
    }

    // Caso real 1 (contrato alternativo): { items: [...] }
    if (data && Array.isArray(data.items)) {
      return data.items
    }

    // Caso real 2 (lo que devuelve *tu* backend): { transfers: [...] }
    if (data && Array.isArray(data.transfers)) {
      return data.transfers
    }

    // ⚠️ Formato desconocido
    console.warn('Formato inesperado en GET /transfers:', data)
    return []
  } catch (error) {
    console.error('Error in getTransfers:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url,
    })
    throw error
  }
}

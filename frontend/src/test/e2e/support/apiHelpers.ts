import { APIRequestContext } from '@playwright/test'
import { API_BASE_URL } from './env'
import { fetchAuthToken, type TestUser } from './testData'

async function authHeaders(request: APIRequestContext, user: TestUser) {
    const token = await fetchAuthToken(request, user.dni, user.password)
    if (!token) {
        throw new Error(`Unable to obtain auth token for ${user.dni}`)
    }
    return {
        Authorization: `Bearer ${token}`,
    }
}

export async function sendSocialContactRequest(
    request: APIRequestContext,
    fromUser: TestUser,
    params: { phone: string; name: string },
): Promise<boolean> {
    const headers = await authHeaders(request, fromUser)
    const response = await request.post(
        `${API_BASE_URL}/users/${encodeURIComponent(fromUser.dni)}/contacts`,
        {
            headers,
            data: {
                phone: params.phone,
                name: params.name,
            },
        },
    )

    if (!response.ok()) {
        if (response.status() === 409 || response.status() === 422) {
            return false
        }
        throw new Error(`Failed to send contact request: ${response.status()} ${await response.text()}`)
    }

    return true
}

export async function acceptSocialContactRequest(
    request: APIRequestContext,
    toUser: TestUser,
    requesterPhone: string,
    alias: string,
) {
    const headers = await authHeaders(request, toUser)
    const response = await request.post(
        `${API_BASE_URL}/users/${encodeURIComponent(toUser.dni)}/contacts/requests/${encodeURIComponent(requesterPhone)}/accept`,
        {
            headers,
            data: {
                name: alias,
            },
        },
    )

    if (!response.ok()) {
        throw new Error(`Failed to accept contact request: ${response.status()} ${await response.text()}`)
    }
}

export async function declineSocialContactRequest(
    request: APIRequestContext,
    toUser: TestUser,
    requesterPhone: string,
) {
    const headers = await authHeaders(request, toUser)
    const response = await request.post(
        `${API_BASE_URL}/users/${encodeURIComponent(toUser.dni)}/contacts/requests/${encodeURIComponent(requesterPhone)}/decline`,
        {
            headers,
        },
    )

    if (!response.ok()) {
        throw new Error(`Failed to decline contact request: ${response.status()} ${await response.text()}`)
    }
}

export async function ensureAcceptedContact(
    request: APIRequestContext,
    owner: TestUser,
    contactUser: TestUser,
    aliasForOwner: string,
) {
    const requestCreated = await sendSocialContactRequest(request, contactUser, {
        phone: owner.phoneE164,
        name: aliasForOwner,
    })
    if (requestCreated) {
        await acceptSocialContactRequest(request, owner, contactUser.phoneE164, aliasForOwner)
    }
}

export type TricountMemberInput = {
    displayName: string
    phone: string
}

export type TricountCreationResponse = {
    tricountId: string
    [key: string]: unknown
}

export async function createTricountViaApi(
    request: APIRequestContext,
    owner: TestUser,
    payload: { title: string; currency?: string; members?: TricountMemberInput[] },
) {
    const headers = await authHeaders(request, owner)
    const response = await request.post(
        `${API_BASE_URL}/users/${encodeURIComponent(owner.dni)}/tricounts`,
        {
            headers,
            data: {
                title: payload.title,
                currency: payload.currency ?? 'EUR',
                members: payload.members ?? [],
            },
        },
    )

    if (!response.ok()) {
        throw new Error(`Failed to create tricount: ${response.status()} ${await response.text()}`)
    }

    return (await response.json()) as TricountCreationResponse
}

export async function inviteUserToTricountViaApi(
    request: APIRequestContext,
    owner: TestUser,
    tricountId: string,
    phone: string,
) {
    const headers = await authHeaders(request, owner)
    const response = await request.post(
        `${API_BASE_URL}/users/${encodeURIComponent(owner.dni)}/tricounts/${encodeURIComponent(tricountId)}/invite`,
        {
            headers,
            data: { phone },
        },
    )

    if (!response.ok()) {
        if (response.status() === 409) {
            return response
        }
        throw new Error(`Failed to invite user ${phone}: ${response.status()} ${await response.text()}`)
    }

    return response
}

export async function acceptTricountInvitationViaApi(
    request: APIRequestContext,
    user: TestUser,
    tricountId: string,
) {
    const headers = await authHeaders(request, user)
    const response = await request.post(
        `${API_BASE_URL}/users/${encodeURIComponent(user.dni)}/tricounts/${encodeURIComponent(tricountId)}/accept`,
        {
            headers,
        },
    )

    if (!response.ok()) {
        throw new Error(`Failed to accept tricount ${tricountId}: ${response.status()} ${await response.text()}`)
    }
}

export async function rejectTricountInvitationViaApi(
    request: APIRequestContext,
    user: TestUser,
    tricountId: string,
) {
    const headers = await authHeaders(request, user)
    const response = await request.post(
        `${API_BASE_URL}/users/${encodeURIComponent(user.dni)}/tricounts/${encodeURIComponent(tricountId)}/reject`,
        {
            headers,
        },
    )

    if (!response.ok()) {
        throw new Error(`Failed to reject tricount ${tricountId}: ${response.status()} ${await response.text()}`)
    }
}


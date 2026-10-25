import { UserManager, WebStorageStateStore, InMemoryWebStorage } from 'oidc-client-ts'

const AUTHORITY = import.meta.env.VITE_OIDC_AUTHORITY || 'https://localhost:8080/o'

export const userManager = new UserManager({
  authority: AUTHORITY,
  client_id: 'kofre-web',
  redirect_uri: `${window.location.origin}/callback`,
  post_logout_redirect_uri: `${window.location.origin}/`,
  response_type: 'code',
  // Redirects replace the current history entry, so "Back" never lands on /login.
  redirectMethod: 'replace',
  scope: 'openid banking',
  // Tokens live in memory only: nothing readable from storage (A3).
  userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
  // Must survive the redirect to the login page, so it cannot be in memory.
  stateStore: new WebStorageStateStore({ store: window.sessionStorage }),
  // The session window (step 6) asks the user instead of renewing silently.
  automaticSilentRenew: false,
  accessTokenExpiringNotificationTimeInSeconds: 60,
})

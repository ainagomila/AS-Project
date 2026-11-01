<template>
  <div id="app">
    <router-view />
    <SessionExpiryModal
      v-if="showExpiry"
      :seconds="secondsLeft"
      :busy="extending"
      @extend="extend"
      @logout="logout"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { userManager } from '@/api/oidc'
import SessionExpiryModal from '@/components/modals/SessionExpiryModal.vue'

const WARNING_SECONDS = 60

const showExpiry = ref(false)
const secondsLeft = ref(0)
const extending = ref(false)
let timer = null
let leaving = false

function stopCountdown() {
  clearInterval(timer)
  showExpiry.value = false
}

// Full sign-out (revokes the tokens in the backend). Guarded: the countdown and
// the "expired" event can fire together.
function logout() {
  if (leaving) return
  leaving = true
  stopCountdown()
  userManager.signoutRedirect()
}

// Refresh-token grant: new access token and a new refresh token, 5 more minutes.
async function extend() {
  extending.value = true
  try {
    await userManager.signinSilent()
    stopCountdown()
  } catch (error) {
    console.error('Session renewal failed:', error)
    logout()
  } finally {
    extending.value = false
  }
}

function onExpiring() {
  clearInterval(timer)
  secondsLeft.value = WARNING_SECONDS
  showExpiry.value = true
  timer = setInterval(() => {
    secondsLeft.value -= 1
    if (secondsLeft.value <= 0) logout()
  }, 1000)
}

onMounted(() => {
  userManager.events.addAccessTokenExpiring(onExpiring)
  userManager.events.addAccessTokenExpired(logout)
})

onUnmounted(() => {
  clearInterval(timer)
  userManager.events.removeAccessTokenExpiring(onExpiring)
  userManager.events.removeAccessTokenExpired(logout)
})
</script>

<style>
body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  background-color: #f5f7fa;
  color: #222;
}
</style>

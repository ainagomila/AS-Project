<template>
  <p>Signing you in…</p>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { userManager } from '@/api/oidc'
import { getUser } from '@/api/userService'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

onMounted(async () => {
  try {
    // Exchanges the one-time code for tokens (PKCE check included).
    const user = await userManager.signinCallback()
    const dni = user.profile.dni
    const profile = await getUser(dni)
    userStore.login(dni, profile)
    router.replace(user.state?.redirect || '/dashboard')
  } catch (error) {
    console.error('Sign-in failed:', error)
    router.replace('/')
  }
})
</script>
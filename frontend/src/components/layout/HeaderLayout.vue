<template>
  <div class="hero-header">
    <!-- Imagen de fondo -->
    <img :src="headerImg" alt="Header background" class="hero-image" />

    <!-- Capa superpuesta con contenido -->
    <div class="hero-overlay">
      <!-- IZQUIERDA: título + enlaces -->
      <div class="hero-left">
        <!-- Título clicable -->
        <h1 class="hero-title" @click="handleTitleClick">{{ title }}</h1>
        <slot name="left"></slot>
      </div>

      <!-- DERECHA -->
      <div class="hero-right">
        <!-- Slot con CONTENIDO POR DEFECTO -->
        <slot name="right">
          <!-- SOLO SE MUESTRAN SI NO ESTAMOS EN LOGIN / SIGNUP / TERMS -->
          <div v-if="!hideIcons" class="header-buttons">
            <!-- ADMIN (solo administradores) -->
            <button
              v-if="userStore.isAdmin"
              class="icon-btn"
              @click="goToAdmin"
              aria-label="Open admin"
            >
              <ShieldCheck class="icon" />
            </button>

            <!-- SETTINGS -->
            <button
              class="icon-btn"
              @click="goToProfile"
              aria-label="Open settings"
            >
              <Settings class="icon" />
            </button>

            <!-- LOGOUT -->
            <button
              class="access-btn logout-btn"
              @click="handleLogout"
              aria-label="Logout"
            >
              <LogOut class="w-4 h-4" />
            </button>
          </div>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import headerImg from '@/assets/header.png'
import { useRouter, useRoute } from 'vue-router'
import { ShieldCheck, Settings, LogOut } from '@lucide/vue'
import { useUserStore } from '@/stores/user'
import { userManager } from '@/api/oidc'
import { computed } from 'vue'

defineProps({
  title: { type: String, required: true },
})

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

/**
 * Rutas donde NO queremos mostrar los iconos de la derecha.
 * Ajusta los nombres para que coincidan con tus rutas reales.
 */
const HIDE_ICONS_ROUTES = ['Login', 'Signup', 'Terms'] 

const hideIcons = computed(() => HIDE_ICONS_ROUTES.includes(route.name))

/**
 * Click sobre el título "Kofre".
 */
const handleTitleClick = () => {
  if (route.name === 'Login' || route.name === 'Landing' || route.name === 'Signup') {
    router.push({ name: 'Landing' })
  } else {
    router.push({ name: 'Dashboard' })
  }
}

const goToAdmin = () => {
  router.push({ name: 'Admin' })
}

const goToProfile = () => {
  router.push({ name: 'Profile' })
}

const handleLogout = () => {
  userStore.logout()
  userManager.signoutRedirect()
}
</script>

<style scoped>
.hero-header {
  position: relative;
  width: 100%;
  height: 65px;
  overflow: hidden;
}

/* Imagen de fondo del header */
.hero-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

/* Capa superpuesta y contenido */
.hero-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  background: transparent;
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.hero-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Título */
.hero-title {
  color: #ffffff;
  font-size: 1.7rem;
  font-weight: 600;
  margin: 0;
  cursor: pointer;
  transition:
    color 0.25s,
    transform 0.25s;
}
.hero-title:hover {
  color: #b79b58;
  transform: scale(1.05);
}

/* BOTONES DERECHA */
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

/* LOGOUT */
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
</style>

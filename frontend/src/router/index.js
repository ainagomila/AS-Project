// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// Vistas base
import LandingView from '@/views/LandingView.vue'
import LoginView from '@/views/LoginView.vue'
import SignupView from '@/views/SignupView.vue'

// Vistas principales
import DashboardView from '@/views/DashboardView.vue'
import AccountDetailView from '@/views/AccountDetailView.vue'
import CardDetailView from '@/views/CardDetailView.vue'

// Lazy-load views
const TransferView = () => import('@/views/TransferView.vue')
const ProfileView = () => import('@/views/ProfileView.vue')
const TermsView = () => import('@/views/TermsView.vue')
const AdminView = () => import('@/views/AdminView.vue')
const CallbackView = () => import('@/views/CallbackView.vue')

// Store
import { useUserStore } from '@/stores/user'

const routes = [
  // ======================
  // PÚBLICAS
  // ======================
  {
    path: '/',
    name: 'Landing',
    component: LandingView,
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { onlyGuest: true }, // Si llegas aquí logueado → hacemos logout suave
  },
  {
    path: '/signup',
    name: 'Signup',
    component: SignupView,
    meta: { onlyGuest: true }, // Igual que login
  },

  // TERMS & CONDITIONS (pública)
  {
    path: '/terms',
    name: 'Terms',
    component: TermsView,
  },

  {
    path: '/callback',
    name: 'Callback',
    component: CallbackView,
  },

  // ======================
  // ÁREA PRIVADA / APP
  // ======================
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    meta: { requiresAuth: true },
  },

  // Cuentas
  {
    path: '/accounts/:id',
    name: 'AccountDetail',
    component: AccountDetailView,
    props: true,
    meta: { requiresAuth: true },
  },
  {
    path: '/accounts/:id/transfer',
    name: 'AccountTransfer',
    component: TransferView,
    props: true,
    meta: { requiresAuth: true },
  },

  // Tarjetas
  {
    path: '/card/:id',
    name: 'CardDetail',
    component: CardDetailView,
    props: true,
    meta: { requiresAuth: true },
  },

  // Perfil
  {
    path: '/profile',
    name: 'Profile',
    component: ProfileView,
    meta: { requiresAuth: true },
  },

  // Administración
  {
    path: '/admin',
    name: 'Admin',
    component: AdminView,
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  // Catch-all
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * Guard global de navegación:
 * - Usa userStore.isAuthenticated como bandera de sesión.
 * - Si vas a login/signup estando autenticado → logout automático (solo FE).
 * - Si intentas entrar en rutas con requiresAuth sin estar autenticado → redirige a /login.
 *
 * Resultado:
 *  - Dashboard → (Atrás) → Login ⇒ se hace logout.
 *  - Luego (Adelante) → Dashboard ⇒ como ya no hay sesión, el guard te manda a Login.
 *  - Igual con Signup.
 */
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  let isLoggedIn = userStore.isAuthenticated

  // 1) Si voy a login/signup (onlyGuest) y estoy logueado → logout frontend
  if (to.meta.onlyGuest && isLoggedIn) {
    userStore.logout()
    isLoggedIn = false
    // Dejamos que navegue a /login o /signup ya como invitado
  }

  // 2) Si la ruta requiere auth y NO estoy logueado → mandar a Login
  if (to.meta.requiresAuth && !isLoggedIn) {
    return next({
      name: 'Login',
      query: { redirect: to.fullPath },
    })
  }

  // 3) Rutas de administración: solo si el perfil guardado es admin
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    return next({ name: 'Dashboard' })
  }

  // 4) En cualquier otro caso, dejar pasar
  return next()
})

export default router

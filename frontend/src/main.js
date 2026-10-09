// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/variables.css'
import { createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

//Hidratar sesión ANTES de usar el router
const userStore = useUserStore()
userStore.initFromStorage()

app.use(router)
app.mount('#app')

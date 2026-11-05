<template>
  <!-- === Functionalities Section === -->
  <section class="functionalities-wrapper wide slim">
    <div class="functionalities-icons">
      <!-- Iconos de funcionalidades -->
      <div
        v-for="(func, index) in functionalities"
        :key="index"
        class="func-item"
        @click="func.action"
      >
        <component :is="func.icon" class="func-icon" />
        <span class="func-name">{{ func.name }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { ShieldCheck, UserRound } from '@lucide/vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const functionalities = computed(() => {
  const items = [
    { name: 'Profile', icon: UserRound, action: () => router.push({ name: 'Profile' }) },
  ]
  if (userStore.isStaff) {
    const name = userStore.isAdmin
      ? 'Admin'
      : userStore.isAuditor
        ? 'Audit'
        : 'Operations'
    items.push({ name, icon: ShieldCheck, action: () => router.push({ name: 'Admin' }) })
  }
  return items
})
</script>

<style scoped>
/* CONTENEDOR PRINCIPAL  */
.functionalities-wrapper.wide.slim {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 12px 32px;
  border-radius: 20px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 40px rgba(0, 0, 0, 0.3);
  box-sizing: border-box;
}

/* CONTENIDO (ICONOS)  */
.functionalities-icons {
  display: flex;
  justify-content: space-around;
  align-items: center;
  flex-wrap: wrap;
  gap: 24px;
}

/*  CADA FUNCIÓN (ICONO + NOMBRE) */
.func-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.25s ease;
}

.func-item:hover {
  transform: translateY(-2px);
}

/* ICONO DORADO */
.func-icon {
  width: 28px;
  height: 28px;
  color: #d5b76f; /* dorado principal de la app */
  margin-bottom: 4px;
  transition: color 0.3s ease;
}

.func-item:hover .func-icon {
  color: #f0d785; /* tono dorado más claro al hover */
}

/*  NOMBRE DEL ICONO  */
.func-name {
  font-size: 0.8rem;
  font-weight: 450;
  color: rgba(245, 245, 245, 0.9);
}
</style>

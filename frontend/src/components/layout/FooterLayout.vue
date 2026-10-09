<template>
  <!-- =========================
       FOOTER PRINCIPAL
       ========================= -->
  <footer class="footer">
    <!-- Imagen de fondo del footer -->
    <img :src="footerImg" alt="Footer background" class="footer-image" />

    <!-- Capa superpuesta semitransparente con texto -->
    <div class="footer-overlay">
      <p class="footer-text">© 2025 Kofre. All rights reserved.</p>
    </div>
  </footer>
</template>

<script setup>
/**
 * Componente: FooterLayout.vue
 * ---------------------------------
 * - Muestra un pie de página con una imagen de fondo.
 * - Superpone texto centrado.
 * - El fondo se importa desde /assets.
 */

import footerImg from '@/assets/header.png' 
</script>

<style scoped>
/* ==========================================================================
   ESTRUCTURA GENERAL DEL FOOTER
   ========================================================================== */
.footer {
  position: relative;
  width: 100%;
  height: 25px;          /* altura visible del footer */
  overflow: hidden;      /* evita que sobresalga la imagen */
  margin-top: auto;      /* empuja el footer al final del contenedor */
}

/* ==========================================================================
   IMAGEN DE FONDO
   ========================================================================== */
.footer-image {
  position: absolute;
  inset: 0;              /* ocupa toda el área del footer */
  width: 100%;
  height: 100%;
  object-fit: cover;     /* mantiene proporciones al rellenar */
  z-index: 0;            /* debajo del overlay */
}

/* ==========================================================================
   CAPA SUPERPUESTA TRANSLÚCIDA
   ========================================================================== */
   .footer-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;            /* encima de la imagen */
  display: flex;
  justify-content: center; /* centra el texto horizontalmente */
  align-items: center;     /* centra el texto verticalmente */
}

/* ==========================================================================
   TEXTO DEL FOOTER
   ========================================================================== */
.footer-text {
  color: #111;           /* color del texto */
  font-size: 0.7rem;     /* tamaño de fuente */
  font-weight: 350;      /* grosor fino */
}
</style>

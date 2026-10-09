<template>
  <div class="page-container dark-mode">
    <header class="fixed-header">
      <HeaderLayout title="Kofre">

        <!-- LEFT NAV -->
        <template #left>
          <nav class="left-nav">
            <a class="header-link" href="#about" @click.prevent="scrollTo('about')">About Us</a>
            <a class="header-link" href="#security" @click.prevent="scrollTo('security')">Security</a>
            <a class="header-link" href="#help" @click.prevent="scrollTo('help')">Help</a>
            <a class="header-link" href="/terms" @click.prevent="goToTerms">Terms & Conditions</a>
          </nav>
        </template>

        <!-- RIGHT BUTTONS -->
        <template #right>
          <div class="header-buttons">
            <button class="access-btn login-btn" @click="goToLogin">Log In</button>
            <button class="access-btn signup-btn" @click="goToSignup">Sign Up</button>
          </div>
        </template>

      </HeaderLayout>
    </header>

    <main class="scroll-content">
      
      <!-- HERO SECTION -->
      <section class="hero-section">
        <div class="hero-content" :class="{ 'fade-in': heroVisible }">
          <h1 class="hero-title">Control your money with clarity and elegance.</h1>
          <p class="hero-sub">
            Kofre helps you track expenses, manage shared costs, and build a clear financial life.
          </p>
          <button class="signup-btn" @click="goToSignup">Start Now</button>
        </div>

        <div class="hero-visual" :class="{ 'scale-in': heroVisible }">
          <div class="image-stack">
            <img src="@/assets/person.jpeg" class="stack-img img-front" />
            <img src="@/assets/person.jpeg" class="stack-img img-back" />
          </div>
        </div>
      </section>


      <!-- ABOUT SECTION -->
      <section
        id="about"
        class="content-section about-section"
        :class="{ 'slide-up': aboutVisible }"
      >
        <div class="section-wrapper">
          <div class="content-image">
            <img src="@/assets/white2-landing.jpeg" class="section-img" />
          </div>

          <div class="content-text">
            <h2 class="section-title">About Kofre</h2>
            <p class="section-description">
              At Kofre, we believe financial freedom begins with control and clarity.
            </p>
            <p class="section-description">
              We build tools that help you plan, save, and track your spending effortlessly.
            </p>

            <div class="features-list">
              <div class="feature-item">✓ Easy expense tracking</div>
              <div class="feature-item">✓ Shared cost management</div>
              <div class="feature-item">✓ Clear financial insights</div>
            </div>
          </div>
        </div>
      </section>


      <!-- TRUST & SECURITY SECTION -->
      <section
        id="security"
        class="content-section security-section"
        :class="{ 'slide-up': securityVisible }"
      >
        <div class="section-wrapper reverse">
          <div class="content-image">
            <img src="@/assets/white3-landing.jpeg" class="section-img" />
          </div>

          <div class="content-text">
            <h2 class="section-title">Trust & Security</h2>
            <p class="section-description">
              We protect your data with advanced encryption and strong authentication.
            </p>
            <p class="section-description">
              Transparency is our priority: you always know how your data is stored and used.
            </p>

            <div class="security-badges">
              <div class="badge">🔒 Encrypted</div>
              <div class="badge">✓ Secure</div>
              <div class="badge">🛡️ Protected</div>
            </div>
          </div>
        </div>
      </section>


      <!-- HELP SECTION -->
      <section
        id="help"
        class="content-section help-section"
        :class="{ 'slide-up': helpVisible }"
      >
        <div class="help-content">
          <h2 class="section-title">Help & Support</h2>
          <p class="section-description">
            Our support team is available 24/7. Contact us at
            <strong>support@kofre.com</strong>.
          </p>
        </div>
      </section>

      <footer class="footer">
        <FooterLayout />
      </footer>

    </main>
  </div>
</template>


<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

import HeaderLayout from '@/components/layout/HeaderLayout.vue'
import FooterLayout from '@/components/layout/FooterLayout.vue'

/* Router */
const router = useRouter()

const goToLogin = () => router.push('/login')
const goToSignup = () => router.push('/signup')
const goToTerms = () => router.push('/terms')   

/* Animation states */
const heroVisible = ref(false)
const aboutVisible = ref(false)
const securityVisible = ref(false)
const helpVisible = ref(false)

/* Smooth scroll */
const scrollTo = (id) => {
  const element = document.getElementById(id)
  if (!element) return
  element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/* Scroll triggered animations */
const handleScroll = () => {
  heroVisible.value = true

  const aboutEl = document.getElementById('about')
  if (aboutEl && window.scrollY + window.innerHeight > aboutEl.offsetTop + 80) {
    aboutVisible.value = true
  }

  const securityEl = document.getElementById('security')
  if (securityEl && window.scrollY + window.innerHeight > securityEl.offsetTop + 80) {
    securityVisible.value = true
  }

  const helpEl = document.getElementById('help')
  if (helpEl && window.scrollY + window.innerHeight > helpEl.offsetTop + 80) {
    helpVisible.value = true
  }
}

onMounted(() => {
  heroVisible.value = true
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>



<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.page-container.dark-mode {
  background: #141414;
  color: #ffffff;
}

.scroll-content {
  padding-top: 80px;
}

/* ==================== HERO SECTION ==================== */
.hero-section {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 80px;
  padding: 120px 80px;
  position: relative;
  overflow: hidden;
}

.hero-content {
  opacity: 0;
  animation: fadeInUp 1.2s ease-out forwards;
}

.hero-title {
  font-size: 4rem;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 20px;
}

.hero-sub {
  font-size: 1.2rem;
  color: #aaa;
  line-height: 1.7;
  margin-bottom: 40px;
  max-width: 450px;
}

.cta-btn {
  padding: 16px 48px;
  background: linear-gradient(135deg, #e8d5a0 0%, #c9b26a 100%);
  color: #000;
  border: none;
  border-radius: 8px;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.4s ease;
  box-shadow: 0 10px 40px rgba(201, 178, 106, 0.15);
}

.cta-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 60px rgba(201, 178, 106, 0.3);
}

.hero-visual {
  opacity: 0;
  animation: scaleIn 1.2s ease-out 0.2s forwards;
}

.image-stack {
  position: relative;
  width: 100%;
  height: 450px;
  border-radius: 12px;
}

.stack-img {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 12px;

  object-fit: cover;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7);
}

.img-front {
  animation: floatImage 3s ease-in-out infinite;
}

.img-back {
  transform: translateX(40px) translateY(40px);
  opacity: 0.6;
  animation: floatImageAlt 3s ease-in-out infinite;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes floatImage {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

@keyframes floatImageAlt {
  0%,
  100% {
    transform: translateX(40px) translateY(40px);
  }
  50% {
    transform: translateX(40px) translateY(60px);
  }
}

/* ==================== CONTENT SECTIONS ==================== */
.content-section {
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: 100px 80px;
  position: relative;
  opacity: 0;
}

.slide-up {
  animation: slideUp 1s ease-out forwards;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(60px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.section-wrapper {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 80px;
  align-items: center;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
}

.section-wrapper.reverse {
  grid-template-columns: 1fr 1fr;
  direction: rtl;
}

.section-wrapper.reverse > * {
  direction: ltr;
}

.content-text {
  padding: 40px;
}

.section-title {
  font-size: 3rem;
  font-weight: 600;
  margin-bottom: 24px;
  letter-spacing: -1px;
}

.section-description {
  font-size: 1.1rem;
  color: #bbb;
  line-height: 1.8;
  margin-bottom: 20px;
}

.features-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 30px;
}

.feature-item {
  font-size: 1rem;
  color: #ddd;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.security-badges {
  display: flex;
  gap: 16px;
  margin-top: 30px;
  flex-wrap: wrap;
}

.badge {
  padding: 12px 24px;
  background: rgba(201, 178, 106, 0.1);
  border: 1px solid rgba(201, 178, 106, 0.3);
  border-radius: 8px;
  font-size: 0.95rem;
  color: #e8d5a0;
  font-weight: 500;
}

.content-image {
  width: 100%;
  height: 500px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7);
}

.section-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.6s ease;
}

.content-image:hover .section-img {
  transform: scale(1.05);
}

/* ==================== HELP SECTION ==================== */
.help-section {
  display: flex;
  justify-content: center;
  align-items: center;
}

.help-content {
  text-align: center;
  max-width: 600px;
}

.help-content .section-title {
  margin-bottom: 24px;
}

.help-content .section-description {
  margin-bottom: 40px;
}

.secondary-btn {
  padding: 14px 40px;
  background: transparent;
  color: #e8d5a0;
  border: 2px solid #e8d5a0;
  border-radius: 8px;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.4s ease;
}

.secondary-btn:hover {
  background: #e8d5a0;
  color: #000;
}

/* ==================== FOOTER ==================== */
.footer {
  margin-top: 60px;
  border-top: none;
}

/* ==================== HEADER STYLES ==================== */
.left-nav {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-left: 8px;
  transform: translateY(3px);
}

.header-link,
.lang {
  font-weight: 500;
  text-decoration: none;
  color: #ffffff;
  font-size: 0.9rem;
  cursor: pointer;
  transition:
    color 0.25s ease,
    transform 0.25s ease;
}

.header-link:hover,
.lang:hover {
  color: #c9b26a;
  transform: scale(1.08);
}

.header-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
}

.login-btn {
  background: transparent;
  color: #fbf8f8;
  border: 2px solid transparent;
  border-radius: 999px;
  padding: 8px 20px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.login-btn:hover {
  background: #fff;
  color: #000;
  border-color: #c9b26a;
  box-shadow: 0 0 6px rgba(201, 178, 106, 0.3);
  transform: translateY(-1px);
}

.signup-btn {
  background: #c9b26a;
  color: #fff;
  border: 2px solid #c9b26a;
  border-radius: 999px;
  padding: 8px 20px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.signup-btn:hover {
  background: #b79b58;
  transform: translateY(-1px);
}

/* ==================== RESPONSIVE ==================== */
@media (max-width: 1024px) {
  .hero-section {
    grid-template-columns: 1fr;
    gap: 40px;
    padding: 80px 40px;
  }

  .hero-title {
    font-size: 3rem;
  }

  .section-wrapper {
    grid-template-columns: 1fr;
    gap: 40px;
  }

  .section-wrapper.reverse {
    grid-template-columns: 1fr;
  }

  .content-section {
    padding: 80px 40px;
  }

  .content-image {
    height: 350px;
  }

  .section-title {
    font-size: 2.2rem;
  }
}

@media (max-width: 768px) {
  .hero-section {
    min-height: auto;
    padding: 60px 20px;
    gap: 30px;
  }

  .hero-title {
    font-size: 2.2rem;
  }

  .hero-sub {
    font-size: 1rem;
  }

  .cta-btn {
    padding: 14px 32px;
    font-size: 1rem;
  }

  .image-stack {
    height: 300px;
  }

  .img-back {
    transform: translateX(20px) translateY(20px);
  }

  .content-section {
    min-height: auto;
    padding: 60px 20px;
  }

  .section-wrapper {
    gap: 30px;
  }

  .content-text {
    padding: 20px;
  }

  .section-title {
    font-size: 1.8rem;
  }

  .section-description {
    font-size: 0.95rem;
  }

  .content-image {
    height: 250px;
  }

  .security-badges {
    gap: 10px;
  }

  .badge {
    padding: 10px 16px;
    font-size: 0.85rem;
  }
}

@media (max-width: 480px) {
  .hero-section {
    padding: 40px 16px;
  }

  .hero-title {
    font-size: 1.8rem;
  }

  .section-wrapper {
    gap: 20px;
  }

  .content-section {
    padding: 40px 16px;
  }

  .section-title {
    font-size: 1.5rem;
  }

  .features-list {
    gap: 8px;
  }

  .feature-item {
    font-size: 0.9rem;
  }
}

.cta-btn {
  padding: 16px 48px;
  background: linear-gradient(135deg, #e8d5a0 0%, #c9b26a 100%);
  color: #000;
  border: none;
  border-radius: 8px;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.4s ease;
  box-shadow: 0 10px 40px rgba(201, 178, 106, 0.15);
}
.cta-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 20px 60px rgba(201, 178, 106, 0.3);
}
</style>

<style scoped>
/* Reduced spacing between sections */
.tightened-layout {
  gap: 40px !important;
}

/* More vertical image shapes */
.vertical-frame {
  height: 600px;
  border-radius: 16px;
  overflow: hidden;
}

.vertical-img {
  border-radius: 16px;
  object-fit: cover;
  border-radius: 12px;
  width: 70%;
  height: 100%;
  margin: 0 auto;
}

/* Help section improvements */
.help-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
  margin-top: 30px;
}

.help-card {
  background: rgba(255, 255, 255, 0.05);
  padding: 20px;
  border-radius: 12px;
  text-align: left;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition:
    transform 0.3s ease,
    background 0.3s ease;
}

.help-card:hover {
  transform: translateY(-6px);
  background: rgba(255, 255, 255, 0.1);
}
/* Simplified hero image animations */
.img-front {
  transform: translateY(0);
  animation: gentleFloat 2s ease-in-out infinite alternate;
}

.img-back {
  opacity: 0.7;
  transform: translateX(30px) translateY(30px);
  animation: gentleFloatBack 2s ease-in-out infinite alternate;
}

@keyframes gentleFloat {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-8px);
  }
}

@keyframes gentleFloatBack {
  from {
    transform: translateX(30px) translateY(30px);
  }
  to {
    transform: translateX(30px) translateY(38px);
  }
}
</style>

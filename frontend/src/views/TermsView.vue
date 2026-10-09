<template>
  <div class="terms-page">
    <HeaderLayout title="Kofre" @click:title="goBack" />

    <div class="terms-content">
      <div class="card">
        <h2 class="card-title">Terms & Conditions</h2>
        <p class="updated">Last updated: October 2025</p>

        <p class="intro">
          Welcome to Kofre. These Terms & Conditions govern the use of our platform,
          mobile application and all related services. By creating a Kofre account or
          using any of our features, you agree to these terms in full. Please read
          them carefully before continuing with the registration process.
        </p>

        <h3 class="section-title">1. About Your Account</h3>
        <p class="text">
          To use Kofre, you must provide accurate, complete and up-to-date information,
          including your full name, DNI, birthdate, gender, email and mobile number.
          You confirm that the information you provide belongs to you and is not being
          used on behalf of another person without authorization.
        </p>
        <p class="text">
          You are responsible for maintaining the confidentiality of your login
          credentials, including your password and 6-digit Kofre security PIN. Any
          activity performed through your account will be considered as performed by
          you, unless you notify us promptly of a suspected compromise.
        </p>

        <h3 class="section-title">2. Security & Authentication</h3>
        <p class="text">
          Kofre uses secure communication channels, encryption and layered
          authentication mechanisms to protect your data. However, no digital service
          can guarantee absolute security. You are responsible for:
        </p>
        <ul class="list">
          <li>Keeping your device updated and protected against malware.</li>
          <li>Not sharing your password, PIN or verification codes with anyone.</li>
          <li>Locking your device when unattended and enabling screen security.</li>
          <li>Informing us immediately if you detect suspicious access.</li>
        </ul>

        <h3 class="section-title">3. Privacy & Data Processing</h3>
        <p class="text">
          Kofre processes your personal data strictly under the applicable data
          protection regulations. Your personal information will not be sold or shared
          with third parties for marketing purposes without your explicit consent.
        </p>

        <h3 class="section-title">4. Transfers, Payments & Responsibilities</h3>
        <p class="text">
          Before confirming any transfer or payment, you must carefully review the
          destination IBAN, the amount and any associated concept. Once a transaction
          has been executed, it may not be possible to reverse it through Kofre.
        </p>

        <h3 class="section-title">5. Fees, Limits & Third-Party Services</h3>
        <p class="text">
          Some services offered through Kofre may be subject to limits or fees. When a
          cost applies, you will be informed before confirming the operation. Kofre may
          connect with third-party services such as banks or payment processors.
        </p>

        <h3 class="section-title">6. Service Availability & Maintenance</h3>
        <p class="text">
          We strive to keep Kofre available 24/7, but the service may experience
          interruptions due to maintenance, incidents in communication networks or
          failures of external providers.
        </p>

        <h3 class="section-title">7. Changes to These Terms</h3>
        <p class="text">
          We may update these Terms & Conditions when we introduce new features,
          adapt to regulatory changes or improve clarity. When relevant modifications
          are made, we will notify you through the app or by email.
        </p>

        <h3 class="section-title">8. Account Suspension & Closure</h3>
        <p class="text">
          You may request closure of your Kofre account at any time. Kofre reserves
          the right to suspend or terminate your account in cases of fraud, misuse,
          violation of these Terms or when required by law.
        </p>

        <h3 class="section-title">9. Contact & Applicable Law</h3>
        <p class="text">
          For questions about these Terms & Conditions or about your Kofre account,
          you can contact our support team through the help section within the app.
          These Terms are governed by the applicable law of your country of residence.
        </p>

        <div class="footer-actions">
          <button class="back-btn" @click="goBack">
            Back
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import HeaderLayout from '@/components/layout/HeaderLayout.vue'

const router = useRouter()
const goBack = () => {
  router.back()
}
</script>

<style scoped>
/* FONDO GENERAL*/
.terms-page {
  background: #1a1a1a;
  min-height: 100vh;
  color: #ffffff;
}

/* CENTRADO DEL CONTENIDO */
.terms-content {
  padding: 3rem 1.5rem 4rem;
  display: flex;
  justify-content: center;
}

/* CARD OSCURA CON BORDE DORADO (LOGIN STYLE) */
.card {
  background: #2a2a2a;            /* panel oscuro */
  padding: 2.5rem 2.6rem;
  border-radius: 24px;
  max-width: 960px;
  width: 100%;
  border: 1px solid #c9b26a;      /* dorado */
  box-shadow: 0 0 40px rgba(250, 204, 21, 0.15);
  color: #f9fafb;
}

/* TÍTULO PRINCIPAL */
.card-title {
  font-size: 1.8rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 0.3rem;
}

/* FECHA */
.updated {
  color: #d1d5db;
  font-size: 0.85rem;
  margin-bottom: 1.6rem;
}

/* INTRODUCCIÓN */
.intro {
  color: #e5e7eb;
  line-height: 1.7;
  margin-bottom: 1.9rem;
  font-size: 0.98rem;
}

/* TÍTULOS DE SECCIÓN */
.section-title {
  margin-top: 2.1rem;
  font-weight: 600;
  font-size: 1.08rem;
  color: #ffffff;
}

/* PÁRRAFOS */
.text {
  margin-top: 0.6rem;
  color: #e5e7eb;
  line-height: 1.7;
  font-size: 0.96rem;
}

/* LISTAS */
.list {
  margin-top: 0.4rem;
  padding-left: 1.2rem;
  color: #e5e7eb;
  line-height: 1.7;
  font-size: 0.95rem;
}

.list li + li {
  margin-top: 0.2rem;
}

/* ACCIONES FOOTER */
.footer-actions {
  margin-top: 2.6rem;
  display: flex;
  justify-content: flex-end;
}

/* BOTÓN VOLVER */
.back-btn {
  padding: 0.75rem 1.8rem;
  border-radius: 999px;
  border: 1px solid #c9b26a;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: #c9b26a;
  transition: transform 0.08s ease, box-shadow 0.08s ease, opacity 0.15s ease,
    background-color 0.15s ease, color 0.15s ease;
}

.back-btn:hover {
  opacity: 0.96;
  transform: translateY(-1px);
  background: #c9b26a;
  color: #111111;
  box-shadow: 0 0 25px rgba(250, 204, 21, 0.4);
}

.back-btn:active {
  transform: translateY(0);
  box-shadow: none;
}
</style>

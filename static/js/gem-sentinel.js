const FIREBASE_SDK_VERSION = '12.16.0';
const FIREBASE_CDN_BASE = `https://cdn.jsdelivr.net/npm/firebase@${FIREBASE_SDK_VERSION}`;
const RECAPTCHA_ENTERPRISE_SITE_KEY = '6LfR-m0tAAAAAA_ZknpoCND2H_ojGXKts5twCl6b';
const MODEL_NAME = 'gemini-2.5-flash';

const DEFAULT_FIREBASE_CONFIG = Object.freeze({
  apiKey: 'AIzaSyDiZyFZenSm7PYsYf2WpHUVHCztlssxBXw',
  authDomain: 'coffee-spark-ai-barista-f9880.firebaseapp.com',
  projectId: 'coffee-spark-ai-barista-f9880',
  storageBucket: 'coffee-spark-ai-barista-f9880.firebasestorage.app',
  messagingSenderId: '460135922205',
  appId: '1:460135922205:web:deec3f5c69753041a6a4f4'
});

const SYSTEM_INSTRUCTION = `You are GEM Sentinel Client Navigator, the official digital assistant for GEM Cybersecurity & Monitoring Assist. Help visitors understand cybersecurity monitoring, incident response, compliance, asset protection, client onboarding, and how to contact the company. Be accurate, concise, calm, and professional. Never claim that a case, account, payment, recovery, investigation, or security event has been verified unless the application supplies evidence. Do not request passwords, seed phrases, private keys, one-time codes, card details, or other secrets. For an active emergency, direct the visitor to the published emergency contact channels.`;

function loadConfig() {
  const globalConfig = window.GEM_SENTINEL_FIREBASE_CONFIG || window.GEM_FIREBASE_CONFIG;
  if (globalConfig && typeof globalConfig === 'object') return globalConfig;

  const meta = document.querySelector('meta[name="gem-sentinel-firebase-config"]');
  if (meta?.content) {
    try { return JSON.parse(meta.content); } catch (_) {}
  }

  return DEFAULT_FIREBASE_CONFIG;
}

function hasRequiredConfig(config) {
  return Boolean(config?.apiKey && config?.appId && config?.projectId);
}

function addMessage(container, role, text) {
  const message = document.createElement('div');
  message.className = `gem-sentinel__message gem-sentinel__message--${role}`;
  message.textContent = text;
  container.appendChild(message);
  container.scrollTop = container.scrollHeight;
}

function describeInitializationError(error) {
  const detail = String(error?.message || error || '');
  if (/app.?check|recaptcha|site key|unauthorized|403/i.test(detail)) {
    return 'App Check could not verify this deployment domain.';
  }
  if (/api.*not enabled|billing|blaze|permission denied/i.test(detail)) {
    return 'Firebase AI Logic is not enabled for this project.';
  }
  if (/content security policy|blocked|failed to fetch dynamically imported module/i.test(detail)) {
    return 'Firebase SDK loading was blocked by the site security policy.';
  }
  return 'Assistant configuration could not be initialized.';
}

function mountWidget() {
  if (document.querySelector('.gem-sentinel')) return null;

  const legacy = document.querySelector('.gem-ai-support');
  if (legacy) legacy.style.display = 'none';

  const root = document.createElement('section');
  root.className = 'gem-sentinel';
  root.setAttribute('aria-label', 'GEM Sentinel Client Navigator');
  root.innerHTML = `
    <div class="gem-sentinel__panel" role="dialog" aria-modal="false" aria-label="GEM Sentinel Client Navigator">
      <header class="gem-sentinel__header">
        <div class="gem-sentinel__title">
          <div class="gem-sentinel__shield">G</div>
          <div><h2>GEM Sentinel</h2><p>Client Navigator · AI-assisted support</p></div>
        </div>
        <button class="gem-sentinel__close" type="button" aria-label="Close assistant">×</button>
      </header>
      <div class="gem-sentinel__messages" aria-live="polite"></div>
      <div class="gem-sentinel__status" aria-live="polite"></div>
      <form class="gem-sentinel__form">
        <input class="gem-sentinel__input" maxlength="1500" autocomplete="off" placeholder="Ask about GEM services…" aria-label="Message">
        <button class="gem-sentinel__send" type="submit">Send</button>
      </form>
      <div class="gem-sentinel__notice">Do not enter passwords, private keys, seed phrases, payment-card details, or one-time codes.</div>
    </div>
    <button class="gem-sentinel__launcher" type="button" aria-label="Open GEM Sentinel">
      <span class="gem-sentinel__dot"></span><strong>Ask GEM Sentinel</strong>
    </button>`;
  document.body.appendChild(root);

  const launcher = root.querySelector('.gem-sentinel__launcher');
  const close = root.querySelector('.gem-sentinel__close');
  launcher.addEventListener('click', () => root.classList.add('is-open'));
  close.addEventListener('click', () => root.classList.remove('is-open'));

  return {
    root,
    form: root.querySelector('.gem-sentinel__form'),
    input: root.querySelector('.gem-sentinel__input'),
    send: root.querySelector('.gem-sentinel__send'),
    messages: root.querySelector('.gem-sentinel__messages'),
    status: root.querySelector('.gem-sentinel__status')
  };
}

async function initializeFirebaseAI(config) {
  // jsDelivr is already permitted by the site's CSP. Loading Firebase from this
  // pinned package endpoint avoids widening script-src to additional hosts.
  const appModule = await import(`${FIREBASE_CDN_BASE}/firebase-app.js`);
  const appCheckModule = await import(`${FIREBASE_CDN_BASE}/firebase-app-check.js`);
  const aiModule = await import(`${FIREBASE_CDN_BASE}/firebase-ai.js`);

  const app = appModule.initializeApp(config);
  const appCheck = appCheckModule.initializeAppCheck(app, {
    provider: new appCheckModule.ReCaptchaEnterpriseProvider(RECAPTCHA_ENTERPRISE_SITE_KEY),
    isTokenAutoRefreshEnabled: true
  });

  // Verify attestation before declaring the assistant protected and ready.
  await appCheckModule.getToken(appCheck, true);

  const ai = aiModule.getAI(app, { backend: new aiModule.GoogleAIBackend() });
  return aiModule.getGenerativeModel(ai, {
    model: MODEL_NAME,
    systemInstruction: SYSTEM_INSTRUCTION,
    generationConfig: { temperature: 0.35, maxOutputTokens: 700 }
  });
}

async function start() {
  const ui = mountWidget();
  if (!ui) return;

  addMessage(ui.messages, 'assistant', 'Hello. I’m GEM Sentinel, the client navigator for GEM Cybersecurity & Monitoring Assist. How may I help you?');

  const config = loadConfig();
  let chat = null;

  if (hasRequiredConfig(config)) {
    try {
      ui.status.textContent = 'Securing connection with App Check…';
      const model = await initializeFirebaseAI(config);
      chat = model.startChat({ history: [] });
      ui.status.textContent = 'Protected by Firebase App Check';
    } catch (error) {
      console.error('GEM Sentinel initialization failed', error);
      ui.status.textContent = describeInitializationError(error);
    }
  } else {
    ui.status.textContent = 'Firebase Web App configuration is required before AI responses can start.';
  }

  ui.form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = ui.input.value.trim();
    if (!text) return;

    addMessage(ui.messages, 'user', text);
    ui.input.value = '';

    if (!chat) {
      addMessage(ui.messages, 'assistant', 'The secure AI connection is not active yet. Please use the website contact options while configuration is completed.');
      return;
    }

    ui.send.disabled = true;
    ui.status.textContent = 'GEM Sentinel is responding…';
    try {
      const result = await chat.sendMessage(text);
      const answer = result?.response?.text?.() || 'I could not produce a response. Please try again.';
      addMessage(ui.messages, 'assistant', answer);
      ui.status.textContent = 'Protected by Firebase App Check';
    } catch (error) {
      console.error('GEM Sentinel request failed', error);
      addMessage(ui.messages, 'assistant', 'The secure assistant is temporarily unavailable. Please try again shortly or contact GEM support.');
      ui.status.textContent = 'Request failed safely';
    } finally {
      ui.send.disabled = false;
      ui.input.focus();
    }
  });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
else start();

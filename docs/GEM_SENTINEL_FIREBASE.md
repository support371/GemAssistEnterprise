# GEM Sentinel Firebase configuration

The browser assistant is implemented in `static/js/gem-sentinel.js` and loaded by `static/js/vercel-analytics.js`.

## Required Firebase Web App configuration

Before production deployment, expose the public Firebase Web App configuration as `window.GEM_SENTINEL_FIREBASE_CONFIG` before `gem-sentinel.js` loads:

```html
<script>
window.GEM_SENTINEL_FIREBASE_CONFIG = {
  apiKey: "YOUR_FIREBASE_WEB_API_KEY",
  authDomain: "coffee-spark-ai-barista-f9880.firebaseapp.com",
  projectId: "coffee-spark-ai-barista-f9880",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_FIREBASE_WEB_APP_ID"
};
</script>
```

These values are the Firebase **Web App configuration**, not a server secret. Retrieve them from Firebase Console → Project settings → Your apps → GEM Sentinel Client Navigator → SDK setup and configuration.

The registered reCAPTCHA Enterprise site key is configured in the browser integration. App Check enforcement should remain disabled until a deployed preview confirms valid App Check traffic and successful Firebase AI Logic responses.

## Verification checklist

1. Open the deployment and launch **Ask GEM Sentinel**.
2. Confirm the status reads **Protected by Firebase App Check**.
3. Send a harmless service question and confirm a Gemini response is returned.
4. Confirm Firebase App Check metrics show valid requests.
5. Test the approved custom domains and the Vercel preview domain.
6. Enable enforcement only after valid traffic is consistently observed.

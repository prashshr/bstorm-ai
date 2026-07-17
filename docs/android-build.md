# Android App (Capacitor) — Build & Install

The AI-Ensemble Android app is a **Capacitor wrapper** of the existing Svelte SPA.
It uses the **same live backend** (`https://ai-ensemble.samkhya.cloud`). No app
code is forked — the web bundle is reused.

## Security model (why it's safe for personal use)

- **Server-side keys only.** On mobile login the backend issues a short-lived
  access token that carries a server session id (`sid`) instead of the UEK. The
  UEK (which decrypts provider secrets) **never leaves the backend** and is held
  in an in-memory cache keyed by `sid`.
- **Refresh tokens in Keystore.** The long-lived refresh token is stored in
  Android Keystore (via `@aparajita/capacitor-secure-storage`). It is used to
  silently obtain a new access token; on logout it is revoked server-side.
- Backward compatible: web clients still get the legacy `uek`-bearing token and
  are completely unaffected.

## Prerequisites (on your build machine, NOT in the dev container)

- Node.js 18+ and the frontend `node_modules` installed (`npm install` in `frontend/`).
- **Android SDK** (cmdline-tools + a platform + build-tools). Easiest: install
  [Android Studio](https://developer.android.com/studio), open the project's
  `android/` folder once, let it download the SDK.
- `JAVA_HOME` pointing at JDK 17 or 21 (Capacitor 8 Gradle prefers 17/21).
- Environment variable for the API base, e.g.:
  ```bash
  export VITE_API_BASE="https://ai-ensemble.samkhya.cloud"
  ```

## Build steps

```bash
cd frontend

# 1. Install deps (Capacitor core/cli/android + secure-storage plugin)
npm install

# 2. Build the SPA (outputs to frontend/dist)
VITE_API_BASE="https://ai-ensemble.samkhya.cloud" npm run build

# 3. Initialize / add the native Android project (first time only)
npx cap add android        # creates frontend/android/

# 4. Copy the built web assets into the native project
npx cap sync android

# 5a. Build a debug APK (sideload-friendly, no signing needed)
cd android && ./gradlew assembleDebug

# 5b. Or open in Android Studio for emulator / device run:
npx cap open android
```

The resulting debug APK is at:

```
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

## Install / test on a device

1. Enable **Developer options → USB debugging** on the phone.
2. `adb install frontend/android/app/build/outputs/apk/debug/app-debug.apk`
   (or copy the file and tap it; allow "Install from unknown sources").
3. Open **AI Ensemble**, log in with your existing account. The first request
   automatically targets the live backend. Tokens are kept in the Keystore.

## Notes

- `capacitor.config.ts` sets `server.url` to the live site so the WebView loads
  the current SPA; API calls use `VITE_API_BASE` (absolute URLs) so they leave
  the WebView and hit the real backend. Keep both pointing at the same origin.
- To ship a release (not required for personal sideload): `./gradlew bundleRelease`
  after creating an upload keystore (`keytool`) and referencing it in
  `android/app/build.gradle`.
- If you change SPA code, rerun `VITE_API_BASE=... npm run build && npx cap sync android`.

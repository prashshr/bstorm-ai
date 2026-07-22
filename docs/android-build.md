# Android App (Capacitor) — Build & Install

The AI-Ensemble Android app is a **Capacitor wrapper** of the existing Svelte SPA.
It uses the **same live backend** (`https://ai-ensemble.samkhya.cloud`). No app
code is forked — the web bundle is rebuilt into a self-contained APK.

## Security model

- **Server-side keys only.** On mobile login the backend issues a short-lived
  access token that carries a server session id (`sid`) instead of the UEK. The
  UEK (which decrypts provider secrets) **never leaves the backend** and is held
  in an in-memory cache keyed by `sid`.
- **Refresh tokens in Keystore.** The long-lived refresh token is stored in
  Android Keystore (via `@aparajita/capacitor-secure-storage`). It is used to
  silently obtain a new access token; on logout it is revoked server-side.
- Backward compatible: web clients still get the legacy `uek`-bearing token and
  are completely unaffected.

## Prerequisites (on your build machine)

- Node.js 18+ and frontend deps (`npm install` in `frontend/`).
- **Android SDK** (cmdline-tools + platform + build-tools). Easiest: install
  [Android Studio](https://developer.android.com/studio), open the project's
  `android/` folder once, let it download the SDK.
- `JAVA_HOME` pointing at JDK 17 or 21.
- Tailscale on both build machine and phone (for file transfer).

## Build steps

```bash
cd frontend

# 1. Build the SPA with API base pointing at production
VITE_API_BASE="https://ai-ensemble.samkhya.cloud" npm run build

# 2. Sync web assets into the native Android project
npx cap sync android

# 3. Build debug APK (sideload-friendly, no signing needed)
cd android && ./gradlew assembleDebug
```

The resulting APK is at:

```
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

## Quick deploy to device

```bash
# Via Tailscale (phone must be active on tailnet)
tailscale file cp frontend/android/app/build/outputs/apk/debug/app-debug.apk <device-name>:

# Or via ADB (USB debugging)
adb install frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

## Install on device

1. **Uninstall** the previous version before installing the new APK (Capacitor
   caches web assets across installs; fresh install avoids stale cache).
2. Copy the `.apk` file to the phone (Tailscale, ADB, or cloud storage).
3. Tap the file and allow "Install from unknown sources".
4. Open **AI Ensemble**, log in with your existing account. All requests go to
   the live backend at `https://ai-ensemble.samkhya.cloud`.

## Architecture notes

- `capacitor.config.ts` sets `webDir: "dist"` — the SPA is **bundled into the
  APK** (no remote URL). API calls use `VITE_API_BASE` (absolute URL baked at
  build time) so they leave the WebView and hit the real backend.
- `CapacitorHttp` plugin is **enabled**, overriding `fetch`/`XMLHttpRequest` with
  Android's native `OkHttp` client. This bypasses WebView CORS restrictions that
  would otherwise block cross-origin API calls from a `file://` or localhost origin.
- `android:windowSoftInputMode="adjustResize"` ensures the chatbox resizes when
  the soft keyboard opens.
- Dark theme is enforced via `DayNight.NoActionBar` with black status/nav bars.

## Manual model entry

Custom proxy-only endpoints (e.g. Tailscale Aperture) don't support `GET /v1/models`
for model discovery. After saving such a provider, expand its row in the sidebar
and type the model name manually (e.g. `DeepseekAI/deepseek-v4-pro`).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Failed to fetch` on login | CORS / CapacitorHttp not enabled | Rebuild with `CapacitorHttp: { enabled: true }` in capacitor config |
| `Unexpected token '<'` response | `VITE_API_BASE` not set at build time | Rebuild with `VITE_API_BASE=https://ai-ensemble.samkhya.cloud` |
| No models shown after saving provider | Backend `/v1/models` returns empty for proxy endpoints | Use manual model entry field |
| Old UI after installing APK | Capacitor cached web assets | **Uninstall first**, then install fresh |

## Changelog (Android-specific)

- **v3.3.0** — Manual model entry; CapacitorHttp for CORS bypass; Tailscale Aperture support
- **v3.2.1** — Custom provider unique keys; self-contained APK
- **v3.2.0** — Dark theme, edge-to-edge, keyboard handling, splash screen

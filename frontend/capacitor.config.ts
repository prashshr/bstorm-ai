import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "cloud.aiensemble.app",
  appName: "AI Ensemble",
  // The Android build bundles this Svelte SPA (webDir: "dist"). For live
  // backend access, the WebView loads the deployed site and API calls use
  // VITE_API_BASE (set in .env at build time).
  server: {
    url: "https://ai-ensemble.samkhya.cloud",
    cleartext: false,
  },
  webDir: "dist",
  android: {
    allowMixedContent: false,
  },
};

export default config;

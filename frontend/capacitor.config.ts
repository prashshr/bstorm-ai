import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "cloud.aiensemble.app",
  appName: "AI Ensemble",
  // The SPA is bundled into the APK (webDir: "dist"). API calls use
  // VITE_API_BASE (set at build time) to reach the production backend.
  // Load from bundled assets instead of a remote URL so the APK version is
  // deterministic and self-contained.
  webDir: "dist",
  android: {
    allowMixedContent: false,
  },
};

export default config;

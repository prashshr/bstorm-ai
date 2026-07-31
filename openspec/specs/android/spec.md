# Specification: Android

## Purpose
Specifies the native Android application wrapper built with Capacitor 8, system window insets fitting, native Keystore secure credential storage, and Gradle build packaging.

## Requirements

### Requirement: Native System Window Insets Fitting
The Android `MainActivity` SHALL configure `WindowCompat.setDecorFitsSystemWindows(getWindow(), true)` to fit the Capacitor WebView within status bar, camera notch, and gesture navigation bar bounds.

#### Scenario: App launches on Android device
- **GIVEN** the Android app opening on a device with camera notch and gesture navigation bar
- **WHEN** the activity creates the window
- **THEN** system decor insets fit the WebView cleanly without top/bottom content cutoff

### Requirement: Android Keystore Secure Credential Storage
The mobile client SHALL store access and refresh JWT tokens in Android Keystore using `@aparajita/capacitor-secure-storage`.

#### Scenario: User logs in on mobile app
- **GIVEN** successful authentication on the Android app
- **WHEN** tokens are received from `/api/auth/login`
- **THEN** the tokens are written to native hardware-backed secure storage

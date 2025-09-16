# Mobile Capture App

This directory contains a lightweight React Native screen for capturing Pokémon GO
screenshots, sending them to the Pokémon Analyzer REST API, and caching the results for
offline review.

## Prerequisites

- [Expo CLI](https://docs.expo.dev/get-started/installation/) or a React Native project
  configured with `expo-image-picker` and `@react-native-async-storage/async-storage`.
- A running instance of the Pokémon Analyzer API (see project README) reachable from your
  device or emulator.

Install the dependencies inside your mobile project:

```bash
expo install expo-image-picker @react-native-async-storage/async-storage
```

If you are using bare React Native, follow the installation instructions provided by each
package.

## Usage

1. Copy `src/screens/CaptureScreen.tsx` into your application and register it with your
   navigator (e.g. React Navigation).
2. Provide the API base URL via the `EXPO_PUBLIC_API_BASE_URL` or `API_BASE_URL`
   environment variable. For Expo, create an `app.config.js` entry or use `app.json`.
3. Launch the screen on a device/emulator, capture or select a screenshot, then tap
   **Analyze** to send it to the backend.
4. Successful scans are cached locally (AsyncStorage) so that the "Recent scans" carousel
   remains available when offline.

## Environment variables

- `EXPO_PUBLIC_API_BASE_URL` (preferred) – API URL exposed to the app at build time.
- `API_BASE_URL` – fallback used if the Expo public variable is not set.

## Offline cache

Scan results are persisted in `AsyncStorage` under the key
`@pogo_analyzer_recent_scans`. Up to 12 entries are retained, keeping the newest results
first. The history list on the screen lets players revisit past analyses without an
active network connection.

# Capacitor setup

The Vue app uses Capacitor 8 with app ID `id.cekrir.app`, name `Cekrir`, and `webDir: 'dist'`. Android and iOS project sources live under `apps/frontend`. Change the app ID before your first store release and update the native project identifiers accordingly.

## Configure the API

Web development uses `/api/v1`, proxied by Vite to FastAPI. Native bundles do not have that proxy. Before building for a device, set an absolute **HTTPS** URL reachable by the device in `apps/frontend/.env`:

```dotenv
VITE_API_BASE_URL=https://your-api.example/api/v1
```

`localhost` on a phone refers to the phone. Do not put a developer workstation's loopback URL in a mobile build. The client reports a configuration error when a native bundle uses a relative or non-HTTPS API URL. For local device testing, use a trusted HTTPS tunnel or an HTTPS development API after adding appropriate authentication.

Vite replaces these variables at build time. Rebuild and sync after changing them. The backend CORS allowlist includes Capacitor's standard iOS and Android local origins; adjust it if you change platform schemes or hostnames.

## Build and open

From the repository root:

```sh
npm run cap:sync --workspace @cekrir/frontend
npm run cap:android --workspace @cekrir/frontend
# Requires macOS and Xcode:
npm run cap:ios --workspace @cekrir/frontend
```

Install Android Studio and the Android SDK for Android builds. iOS builds require macOS, Xcode, signing configuration, and the SDK versions supported by your installed Capacitor version. `cap:sync` builds the web app before copying assets and updating plugins.

If regenerating a platform after changing the app ID:

```sh
npm run cap:add:android --workspace @cekrir/frontend
npm run cap:add:ios --workspace @cekrir/frontend
```

Run these only when the corresponding native directory is absent. Commit native project sources and your platform customizations; native build output and copied web assets are ignored by their generated `.gitignore` files.

## Notification behavior

The “Enable device notifications” button requests permission and uses `@capacitor/local-notifications`. New events fetched while the app is open can produce local device alerts. Android 13+ notification permission is requested by the plugin.

Local notifications do not deliver server events while the application is suspended or closed. To support that flow, add Capacitor Push Notifications, register device tokens with an authenticated backend, and implement APNs/FCM delivery with platform credentials, user preferences, token lifecycle management, and retries.

Native project generation and plugin sync can run on Linux. Native compilation, signing, and permission/device behavior must be tested with the platform toolchains and real devices.

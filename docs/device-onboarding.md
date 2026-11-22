# Device onboarding, push notifications, and tracking

Run the backend migrations before using these features. On the VM, after updating the repository and `apps/backend/.env`, rebuild the existing services from `apps/backend`:

```bash
docker compose --env-file .env up --build -d --force-recreate
```

## ESP32

1. Configure the frontend's `VITE_API_BASE_URL` as `https://api.cekrir.bakuretsumagic.my.id/api/v1` before building the Android app, then log in as an admin. The response includes `location_id` and `esp_device_id`. The first login creates any missing default location or ESP identifier; later logins reuse them. The current live frontend keeps the session only in memory and requires another login after a reload or access-token expiration.
2. In the frontend device screen, issue an ESP key. Alternatively, call `POST /api/v1/locations/{location_id}/esp/credentials` with the admin's bearer token. The response contains the device ID and its key. The key is shown only once. Issuing another key invalidates the previous one.
3. Enter the 2.4 GHz Wi-Fi name and password, API URL, courier, and the PEM root certificate for the API's HTTPS certificate in the frontend generator. The Wi-Fi details and key are used locally to generate `config.h`; keep that file private. Put it at `apps/esp32/include/config.h` on the computer building the firmware.
4. From `apps/esp32`, build and upload using PlatformIO. Replace `COM10` with the board's port:

   ```bash
   "$USERPROFILE/.platformio/penv/Scripts/platformio.exe" run -d . -e esp32_s3_cam_onboarded -t upload --upload-port COM10
   ```

   In Windows Command Prompt, use `%USERPROFILE%` instead of `$USERPROFILE`. The board profile is for the common dual-USB ESP32-S3 CAM; verify the pin map for the actual board. This command replaces its firmware.
5. After upload, the board can run from a power adapter. It connects to Wi-Fi and periodically sends JPEG frames to `POST /api/v1/devices/{device_id}/frames?courier=jne`, using `X-Device-Key`. The API validates the key and checks frames for a barcode. `onboarding_complete` changes after the first authenticated request. The generated firmware is periodic; it does not yet use the proximity sensor.

This is a configuration file for an existing PlatformIO project, not a browser-built binary. A trusted root certificate is necessary for HTTPS verification, and the ESP needs a working clock via network time. Rotation requires rebuilding and uploading the new configuration. The older shared ingestion key routes remain available for legacy devices; that key does not identify an individual device.

## CCTV

Set `CEKRIR_CCTV_ENCRYPTION_KEY` in `apps/backend/.env` to a Fernet key. Generate one once using the backend Python environment:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store and back up the key securely. Keep using the same key: changing or losing it makes previously saved camera credentials unreadable. With an admin access token, call `POST /api/v1/locations/{location_id}/cctv` with `name`, an `rtmp://` or `rtmps://` `stream_url`, `username`, and `password`. Keep credentials out of the URL. The backend encrypts the URL and credentials and returns only the camera ID, location ID and name. This registers the camera; it does not start a stream reader. Multiple cameras can belong to a location.

## Firebase notifications

1. Create a Firebase project and enable Cloud Messaging. Add the Android app using its actual application ID. Place the resulting `google-services.json` at `apps/frontend/android/app/google-services.json`; it is ignored by Git. Rebuild the Android app after running `pnpm --filter @cekrir/frontend exec cap sync android`. A real Firebase project and Android device are needed to test delivery.
2. Create a Firebase Admin service-account JSON file and keep it outside the repository. Make it readable by the API container user. Mount it read-only into the `api` service, for example with a Compose volume mapping from the protected host path to `/run/secrets/firebase-service-account.json:ro`, and set `CEKRIR_FIREBASE_CREDENTIALS_FILE=/run/secrets/firebase-service-account.json` in the backend `.env`. Recreate the container. A host-only path in `.env` is not automatically available inside the container.
3. After login, the Android app requests push permission and sends its FCM token and location ID to `POST /api/v1/notifications/fcm`. The server allows registration only for the location's admin or members. A user can register multiple devices and a device may be associated with multiple locations. Remove registrations on logout using `POST /api/v1/notifications/fcm/unregister` with the token, or `DELETE /api/v1/notifications/fcm/{device_id}`.
4. When a package arrives from a location-mapped camera or ESP, the backend attempts to send FCM to active, verified users who still belong to that location. Delivery is best effort and requires Firebase credentials; there is no retry queue. Email and frontend notifications remain separate channels. The existing in-app list and WebSocket are not yet location-scoped, and live delivery detail screens are not yet connected to the API.

The native push bridge currently supports Android. Browser and iOS push registration require additional platform setup and implementation. The live frontend currently remembers the installation token only in memory, so after a restart it cannot reliably detach the old registration on logout until it receives that token again. A token already owned by a different user is rejected; remove the old registration before switching accounts on the same device.

## BinderByte

Set `CEKRIR_BINDERBYTE_API_KEY` in the backend `.env` and recreate the API container. Call `POST /api/v1/tracking/binderbyte` with an access token and, for example:

```json
{"resi_number":"YOUR_TRACKING_NUMBER","courier":"jne"}
```

For couriers requiring it, include `phone_last_five` as a five-digit string. The endpoint returns BinderByte's summary, detail and history and makes a live provider request, which can use your provider quota. It returns 503 if BinderByte is unavailable or the key is missing. It does not perform screenshot recognition.

# Tuya QR account-linking POC

Use this local pilot to check whether a Cekrir Tuya Cloud Project can access a camera paired to a different household’s Tuya or Smart Life account. The POC displays a QR code from the Tuya console, verifies access to the specified camera, and can request one snapshot. It uses Cloud Project credentials and does not use the personal Smart Control key at `tuya.ai`. [Tuya Cloud Project account linking](https://developer.tuya.com/en/docs/developer/apply-cloud-api-key?id=Kff30z8sv62ah)

## Set up the project

1. In the [Tuya Developer Platform](https://platform.tuya.com/), create a **Smart Home** Cloud Project in a data center that serves the test household’s app account. Authorize the project to query devices. For the snapshot test, enable the Camera Service and Message Service for that project. Check **Devices → All Devices** before linking to confirm the test camera is absent. [Cloud Project setup](https://developer.tuya.com/en/docs/developer/apply-cloud-api-key?id=Kff30z8sv62ah) · [Message Service](https://developer.tuya.com/en/docs/iot/manage-messages?id=Ka49p7loog3ze)
2. Set the project’s Access ID, Access Secret, and data center on the machine running the POC. You can put these in the ignored `apps/backend/.env.tuya-qr-poc` file. The data center values are `cn`, `us`, `us-east`, `eu`, `eu-west`, `in`, and `sg`. Use the value for your Cloud Project. [Tuya regional endpoints](https://developer.tuya.com/en/docs/iot/api-request?id=Ka4a8uuo1j4t4)

   ```dotenv
   TUYA_POC_ACCESS_ID=your-project-access-id
   TUYA_POC_ACCESS_SECRET=your-project-access-secret
   TUYA_POC_DATA_CENTER=sg
   ```

3. From the repository root, run the POC on the local machine. Open `http://127.0.0.1:8003` in a browser on that machine. The credentials stay in the backend process, and the QR image stays in the browser.

   ```sh
   uv run --project apps/backend python -m cekrir.tuya_qr_poc
   ```

## Link and verify a camera

1. In the Cloud Project, open **Devices → Link App Account → Add App Account → Tuya App Account Authorization**. Copy the displayed QR code to an image file and open the image in the POC. The POC uses the QR issued by the console. [Tuya account authorization](https://developer.tuya.com/en/docs/developer/apply-cloud-api-key?id=Kff30z8sv62ah)
2. On the test household’s phone, scan the code from the Tuya or Smart Life app and approve access. Finish linking in the console. Select the pilot camera if manual device linking is available. Copy the linked account’s UID from the console and the camera’s Virtual ID from **Device Information** in the mobile app. [Tuya device linking](https://developer.tuya.com/en/docs/iot/link-devices?id=Ka471nu1sfmkl) · [Tuya device IDs](https://developer.tuya.com/en/miniapp/faq/panel#how-can-i-get-the-device-id-deviceid)
3. Enter those IDs in the POC and click **Verify camera**. A positive result means the project can find that camera in the linked account’s device list. If verification fails, check that the QR is current, linking is complete, the data center matches, and the project has permission to list the account’s devices. [Get User’s Device List](https://developer.tuya.com/en/docs/cloud/ad2823ae46?id=Kconjtzq1vk1q)
4. Optionally click **Request snapshot**. An accepted command returns an ID. For proof of capture, use the project's Message Service consumer to find the `webcam_capture_image` event for that camera at the time of the request. Download the JPEG from `picUrl` and confirm it shows the current scene. Run one request at a time to make the event easy to match. [Capture An Image API](https://developer.tuya.com/en/docs/cloud/d0cfd27341?id=Kbsm7ev5fnv32) · [Camera capture event](https://developer.tuya.com/en/docs/cloud/camera-open-capabilities?id=Kbxdoa8zjorhj)

Record whether account linking, camera verification, command acceptance, and JPEG retrieval succeeded. Keep the project secret, QR image, and signed media URL out of the record. Unlink the pilot account in the console when the test is complete.

If camera verification passes and Tuya returns code `500` during snapshot capture, try **Cloud → API Explorer → Camera Service → Capture An Image** with the same project, data center, and device ID. If Tuya returns the same error there, record the request ID (`tid`) if present and the time of the request for Tuya support. [Tuya API Explorer](https://developer.tuya.com/en/docs/iot/api-debugging?id=Ka6yniaizeiiu) · [Tuya error codes](https://developer.tuya.com/en/docs/iot/error-code?id=K989ruxx88swc)

The POC runs independently of Cekrir sign-in, PostgreSQL, and the existing delivery-photo integration. Automated tests simulate Tuya’s responses. The separate-account QR scan and JPEG retrieval require a live pilot with a real project and camera.

## Hosted OAuth pilot for Singapore

1. In Tuya’s **Configure OAuth 2.0 Authorization** screen, select the Android App Authorization key, enable Singapore, and register `https://api.cekrir.bakuretsumagic.my.id/api/v1/integrations/tuya/oauth/callback/sg`. If you deploy to another HTTPS hostname, keep the path and register that hostname. Upload the [Cekrir package icon](frontend/cekrir-tuya-app-icon.png) under **App Icon** and save the generated **H5 Page URL**. [Tuya OAuth setup](https://developer.tuya.com/en/docs/iot/authorization-code-page-usage?id=Kdkyz44dz6a7r)
2. On the backend VM, add the following to `apps/backend/.env`. Use the credentials from **Authorization → App Authorization** for the key selected in the H5 configuration, and use the same SHA‑1 registered with `id.cekrir.app`. [Tuya app authorization](https://developer.tuya.com/en/docs/iot/manage-application?id=Kag37wnxynw)

   ```dotenv
   CEKRIR_TUYA_OAUTH_CLIENT_ID=your-app-authorization-client-id
   CEKRIR_TUYA_OAUTH_CLIENT_SECRET=your-app-authorization-client-secret
   CEKRIR_TUYA_OAUTH_ANDROID_SHA1=40:7B:B4:24:FB:C1:B1:99:95:D3:BA:85:2F:2D:DC:84:95:B1:C3:13
   CEKRIR_TUYA_OAUTH_H5_URL='paste-the-generated-singapore-h5-page-url'
   ```

3. Deploy the PR’s backend using `sudo docker compose up -d --build api` from `apps/backend`. The OAuth pilot uses the existing Redis service and adds no database migrations. The callback receives the authorization code in the query string. Keep query strings out of reverse-proxy access logs for that path. The repository’s Nginx configuration has access logging disabled.
4. With a current Cekrir admin access token set as `CEKRIR_API_TOKEN` in your shell, use the start endpoint to create an authorization attempt.

   ```sh
   curl --fail-with-body --request POST \
     --header "Authorization: Bearer ${CEKRIR_API_TOKEN}" \
     https://api.cekrir.bakuretsumagic.my.id/api/v1/integrations/tuya/oauth/start/sg
   ```

5. Open the returned `authorization_url` within ten minutes and authorize the test account on Tuya’s page. The callback consumes the state once, exchanges the code in Singapore, and reports success. Start a fresh attempt if anything fails. The pilot discards the returned tokens after confirming the exchange. A live test is required to confirm that Tuya accepts the chosen account and returns the original state. [Tuya authorization code exchange](https://developer.tuya.com/en/docs/iot/authentication-method?id=Ka49gbaxjygox)

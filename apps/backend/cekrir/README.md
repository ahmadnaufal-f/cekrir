# Cekrir Bruno collection

This collection contains requests for the main API at `https://api.cekrir.bakuretsumagic.my.id`. It uses the OpenCollection YAML format in `opencollection.yml`. The separate local camera-preview server is not deployed at this address; its endpoints are described in [the API reference](../API.md).

## Get started

1. Open the `apps/backend/cekrir` collection in the Bruno VS Code extension (or the Bruno app). Refresh or reopen it if the requests do not appear.
2. Select the `VM` environment. Enter your admin email and password in its `email` and `password` variables, then run **Auth > Login**.
3. Copy `access_token` and `refresh_token` from the login response into the environment's `accessToken` and `refreshToken` variables. Run login again when the access token expires (15 minutes); the refresh token expires after one week.
4. Start with **Health**, **List users**, **List shipments**, or **List locations**. Fill `userId`, `locationId`, `shipmentId`, or `paymentId` with IDs from the relevant responses before sending requests that need them.

Keep passwords, tokens, and the ingestion key private. Use Bruno's local secret storage for the secret variables, and do not commit their values to Git or share a login response. Empty values in the supplied environment are placeholders. Requests requiring admin permissions may return 403 with a member account.

## Requests that change data

Run requests individually. Registration, role changes, shipments, detections, location assignments, email, and payments change real data or send real emails on the VM. Use a test environment and test accounts if possible; do not run the whole collection against production. Registration can create an account even if email delivery then fails.

- Set `newEmail` and `newPassword` before testing registration and resend verification. Copy the token from the verification email to `verificationToken` for the verification requests. Email delivery must be configured.
- Set `ingestKey` to `CEKRIR_INGEST_API_KEY` for detection requests. If the server has no ingestion key configured, replace the `X-Ingest-Key` header with `Authorization: Bearer <access token>` instead.
- For **Submit JPEG frame**, choose a JPEG file as a binary request body in Bruno before sending. The file must be no larger than 512 KiB. This request has an empty body until you select a file.
- Set a different `paymentIdempotencyKey` or `emailIdempotencyKey` for each new operation. Reuse the same key only for a retry of the same request. Payment requests create drafts; they do not process QRIS payments.
- **Send email** needs a configured mail provider and an eligible recipient. Use a user ID returned by **List users**.

## Live notifications

For the live notification endpoint, create a WebSocket request in Bruno with URL `wss://api.cekrir.bakuretsumagic.my.id/api/v1/notifications/live` and an `Authorization: Bearer <access token>` header. A successful connection receives `{"type":"ready"}`. Redis must be available and the user needs notification-read permission.

See [the API reference](../API.md) for request fields, authorization, expected responses, and the separate camera server.

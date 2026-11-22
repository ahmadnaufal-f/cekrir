# Tuya Cloud CCTV capture research

Research and live test date: November 22, 2026.

## Question and current evidence

Can a hosted Cekrir backend request a current JPEG from the BARDI Indoor PTZ camera without a separate always-on computer on the camera's LAN?

The camera is paired in the BARDI Smart Home app. Local RTSP/TCP capture with FFmpeg worked three times. ONVIF advertised `SnapshotUri=true` and returned `/snapshot`, but HTTP GET to that URL closed without a response. See [the local POC](cctv-snapshot-poc.md). A Tuya Smart Control key and Singapore API endpoint are now configured in the ignored `apps/backend/.env`; they must stay out of Git and logs.

## Candidate A: Tuya Smart Control end-user API

Tuya's [current end-user API reference](https://tuya.ai/developer/docs) documents IPC Cloud Capture. It uses a bearer API key and an asynchronous two-step flow:

1. `POST /v1.0/end-user/ipc/{device_id}/capture/allocate` with a `PIC` capture request.
2. Poll `POST /v1.0/end-user/ipc/{device_id}/capture/resolve` until the result is ready, then download the returned image URL.

Tuya's [official CLI](https://github.com/tuya/tuya-smart-control-cli) exposes this as `tuya ipc pic <device_id>` and documents `tuya device list` to find devices. It reports that the camera uploads the capture asynchronously and the CLI polls for the image URL. The API reference currently labels the service as a trial with rate limits; it does not establish a production quota or price for this use case.

**Validated for this camera:** The key sees one online `IDR-IPC-PTZ` device, and the IPC capture operation returned a current JPEG. The first test request was accepted, but the test harness incorrectly treated a `resolve.status` of `ACCEPTED` as a terminal failure. A second request confirmed that the resolve response can include `decrypt_image_url` while `status` is still `ACCEPTED`. Capture handling should check for the URL and image validity rather than require `status == READY`.

### Live cloud capture result

On November 22, 2026 at about 22:20 Jakarta time, a backend-side Python process called `GET /v1.0/end-user/devices/all`, then the Tuya `allocate` and `resolve` endpoints over HTTPS. The account returned one online device named `IDR-IPC-PTZ`. The second allocate/resolve run produced a downloadable 99,966-byte JPEG at 2880 × 1620 in 6.48 seconds end to end. The camera's visible timestamp reads 22:20:37, consistent with the test time. The image was saved with mode `0600` at `/tmp/cekrir-tuya-cloud-snapshot.jpg`; neither the API key nor the temporary image URL was printed.

This validates a cloud path from the current backend machine without making a local RTSP request. The machine was still on the camera's Wi-Fi during the test, so operation from an externally hosted backend remains to be verified. The remote backend needs outbound HTTPS access to Tuya and to the returned image host.

### Backend endpoint test

The FastAPI integration now queues a Tuya cloud capture after an accepted detection, stores the JPEG under the shipment UUID, and exposes it through an authenticated shipment photo route. A November 22 live request through `POST /api/v1/detections` against the dedicated test PostgreSQL database returned `photo_status=pending` immediately. The background capture then changed the shipment to `ready`; `GET /api/v1/shipments/{id}/photo` returned a new 92,339-byte, 2880 × 1620 JPEG with a visible camera timestamp of 22:34:06 Jakarta time. An unauthenticated photo request returned 401. The saved test image is `/tmp/cekrir-endpoint-live-photos/95ccbb07-c452-4c6a-bbb0-edd785de7e86.jpg`.

## Candidate B: Tuya Developer Platform cloud project

The [Camera Service API](https://developer.tuya.com/en/docs/cloud/d0cfd27341?id=Kbsm7ev5fnv32) documents `POST /v1.0/cameras/{device_id}/actions/capture`. The command returns an ID; Tuya's [camera event documentation](https://developer.tuya.com/en/docs/cloud/camera-open-capabilities?id=Kbxdoa8zjorhj) says a subsequent message contains a temporary JPEG URL. This path requires a linked device, API authorization, and Tuya Message Service. The documentation does not confirm this operation applies to the owned consumer camera.

The project's link method is a material constraint. Tuya says an OEM app linked through **Link My App** must belong to the same Tuya developer account as the cloud project. A personal project therefore should not assume it can select BARDI's OEM app. Tuya's [Link Devices guide](https://developer.tuya.com/en/docs/iot/link-devices?id=Ka471nu1sfmkl) documents a separate QR-code method for a **Smart Life** app account. BARDI's [FAQ](https://faq.bardi.co.id/Faq/search/47) confirms BARDI is powered by Tuya and describes removing a device from Smart Life before pairing it to BARDI; moving this camera the other direction would be a separate, user-approved pairing experiment.

For a project/account in Indonesia, select the actual account data center rather than assuming from location. Tuya's [mapping](https://developer.tuya.com/en/docs/iot/oem-app-data-center-distributed?id=Kafi0ku9l07qb) places newer Indonesian OEM accounts in Singapore and older ones in Western America. A mismatched region can make linked devices appear absent.

## Smallest live validation

1. Run the same capture from a host outside the camera LAN. Confirm that outbound HTTPS alone suffices and measure latency over several scans.
2. Mount the photo directory on persistent storage and verify the same flow from the deployed API. The current in-process background task is not durable across crashes; use a persistent job worker if high availability is required.
3. Check Tuya's current trial limits, production quota, and pricing before relying on this path in a deployed service.

## Decision state

Cloud capture is **validated for this BARDI unit from the current backend machine and through the new backend endpoint**. The key can see the camera, and current JPEGs were downloaded through Tuya's cloud API. A truly remote deployment has not yet been exercised. Local RTSP/FFmpeg capture is also validated as a fallback when the backend can reach the camera LAN.

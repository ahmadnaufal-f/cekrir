# Cekrir ESP32 camera scanner

Arduino C++ firmware, built with PlatformIO, for a camera-equipped ESP32 with PSRAM. The device captures a JPEG and sends it to FastAPI, which decodes the barcode and reuses the existing shipment/notification workflow. **Barcode decoding runs on the backend.** The firmware does not claim on-device Code 128 decoding.

Package labels commonly contain one-dimensional barcodes. A QR-only ESP32 library is insufficient for that use case. This scaffold supports Code 128, Code 39, ITF, and direct-resi QR codes through the backend's ZXing decoder.

## Before buying hardware

Two board profiles are provided; select the one that matches the actual module:

| Profile                        | Hardware                                                           | Notes                                                                        |
| ------------------------------ | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| `xiao_esp32s3_sense` (default) | Seeed XIAO ESP32S3 **Sense**, including its camera expansion board | Convenient USB programming and PSRAM; a useful starting point for evaluation |
| `ai_thinker_esp32cam`          | AI Thinker ESP32-CAM with OV2640 and PSRAM                         | Usually needs a compatible USB serial programmer or ESP32-CAM-MB             |

An ESP32/S3 chip name alone does not define a camera pinout. Other camera boards need a separate pin mapping and PlatformIO environment. Verify the exact model, sensor, PSRAM, power supply, programming interface, and lens focus distance with the vendor. Test a sample with real labels before buying a batch: focus, lighting, motion blur, barcode size, and camera distance determine whether scanning works. The default capture size is 800×600; higher resolution cannot fix an out-of-focus label.

## Configure and build

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The root scripts run the pinned PlatformIO version in an isolated Python environment; the backend virtual environment is separate.

From the repository root:

```sh
cp apps/esp32/include/config.example.h apps/esp32/include/config.h
# Edit config.h: Wi-Fi, API URL, camera ID, courier, ingestion key, and HTTPS root CA.
pnpm run firmware:build
# Alternative board:
pnpm run firmware:build --environment ai_thinker_esp32cam
```

`config.h` is ignored by Git. Builds without it use the example and halt at runtime until configured. Keep secrets out of build flags and committed files. Credentials are embedded in the flashed firmware; secure provisioning and encrypted storage are future work.

The API base URL ends with `/api/v1`. A phone/workstation loopback address is not reachable from the ESP32. Use a reachable HTTPS API and configure its certificate's PEM root CA in `kApiRootCa`. The firmware synchronizes time with NTP before HTTPS requests and never disables certificate verification or follows redirects.

For a trusted development LAN, explicitly set `kAllowPlainHttp = true`, use your workstation's LAN IP, and bind FastAPI to the LAN interface:

```sh
# PostgreSQL and migrations should already be set up using the root README.
uv run --directory apps/backend uvicorn cekrir.main:app --host 0.0.0.0 --port 8000
```

For example, set `kApiBaseUrl` to `http://192.168.1.20:8000/api/v1`. Set `CEKRIR_INGEST_API_KEY` in `apps/backend/.env` and the matching `kIngestApiKey` in the device config. The key protects camera ingestion only; the rest of this prototype API still needs user authorization before internet exposure.

## Flash and monitor

Connect the board using its supported USB/programmer interface, then run:

```sh
pnpm run firmware:upload --environment xiao_esp32s3_sense --upload-port /dev/ttyACM0
pnpm run firmware:monitor --port /dev/ttyACM0
```

For AI Thinker, use its environment and actual serial port. Follow the board vendor's boot/programming instructions (some boards need GPIO0 held low during flashing, followed by release/reset). On Windows, serial ports look like `COM3`; on macOS they often start with `/dev/cu.`. Pin profiles follow [Espressif's camera examples](https://github.com/espressif/arduino-esp32/blob/2.0.17/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h).

Builds are checked for both profiles in CI. Successful cross-compilation does not verify a physical camera, Wi-Fi, USB flashing, certificate setup, optics, or power stability. Those checks require the purchased hardware.

## Runtime behavior

- Requires PSRAM and initializes JPEG capture at SVGA, quality 12, with one frame buffer.
- Reconnects Wi-Fi and submits a new frame roughly every three seconds while online.
- Sends `POST /api/v1/detections/frame?courier=jne&camera_id=esp32-front-door`, raw `image/jpeg`, and the optional `X-Ingest-Key` header.
- Processes one frame at a time, releases camera buffers, and never records video or writes captures to flash.
- Uses bounded network timeouts and exponential retry delays capped at 60 seconds. Failed/offline frames are discarded; a later attempt captures a new one.
- Waits 15 seconds after a detected barcode, including an existing shipment, to reduce repeated uploads. A new package can be missed during that cooldown; adjust it for the physical workflow.
- Logs counts/statuses, without printing keys, Wi-Fi credentials, resi numbers, images, or response bodies.

The server accepts JPEGs up to 512 KiB, 2 megapixels, and 2048 pixels per side. Blank frames return no detections. Multiple distinct resi-shaped codes are reported as ambiguous and create no shipments; move one label into view. QR URLs and unsupported resi formats are ignored. The courier is configured explicitly because the barcode usually does not identify it.

Frames leave the device and are decoded in backend memory, without being saved to disk or PostgreSQL. Only normalized detection metadata and shipment data are persisted. Automatic frame capture should point at the intended package scanning area.

## Test without hardware

```sh
pnpm run firmware:test
pnpm run db:up
pnpm test
```

Native C++ tests cover timer wraparound, bounded retries, query encoding, and courier validation. Backend tests encode real barcode images, JPEG-compress them, send them to the frame endpoint, and verify decoding, PostgreSQL persistence, duplicate handling, ambiguity, authentication, and image limits. A physical board is not needed for those tests.

Manual API check with a JPEG containing one resi barcode:

```sh
curl 'http://127.0.0.1:8000/api/v1/detections/frame?courier=jne&camera_id=esp32-test' \
  -H 'Content-Type: image/jpeg' \
  -H 'X-Ingest-Key: your-development-key' \
  --data-binary @label.jpg
```

The compact response contains `detected_count`, `ambiguous`, and `detections` (resi number, shipment ID, and whether it was newly created). Successful frames return HTTP 200, including blank/ambiguous frames. Errors use 401 for an invalid configured key, 413 for excessive body size, 415 for the wrong content type, 422 for invalid metadata/images, and 502 for a tracking provider failure. Existing API deduplication prevents repeated frames from creating duplicate shipments or notifications.

# Cekrir ESP32 camera scanner

Arduino C++ firmware, built with PlatformIO, for a camera-equipped ESP32 with PSRAM. The device captures a JPEG and sends it to FastAPI, which decodes the barcode and reuses the existing shipment/notification workflow. **Barcode decoding runs on the backend.** The firmware does not claim on-device Code 128 decoding.

Package labels commonly contain one-dimensional barcodes. A QR-only ESP32 library is insufficient for that use case. This scaffold supports Code 128, Code 39, ITF, and direct-resi QR codes through the backend's ZXing decoder.

## Before buying hardware

Two board profiles are provided; select the one that matches the actual module:

| Profile                        | Hardware                                                           | Notes                                                                        |
| ------------------------------ | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| `xiao_esp32s3_sense` (default) | Seeed XIAO ESP32S3 **Sense**, including its camera expansion board | Convenient USB programming and PSRAM; a useful starting point for evaluation |
| `ai_thinker_esp32cam`          | AI Thinker ESP32-CAM with OV2640 and PSRAM                         | Usually needs a compatible USB serial programmer or ESP32-CAM-MB             |
| `esp32_s3_cam`                 | Common dual-USB ESP32-S3 CAM N16R8                                | Candidate pinout; compare against the actual board before using              |

An ESP32/S3 chip name alone does not define a camera pinout. Other camera boards need a separate pin mapping and PlatformIO environment. Verify the exact model, sensor, PSRAM, power supply, programming interface, and lens focus distance with the vendor. Test a sample with real labels before buying a batch: focus, lighting, motion blur, barcode size, and camera distance determine whether scanning works. The default capture size is 800×600; higher resolution cannot fix an out-of-focus label.

## Wi-Fi camera on Windows

The `esp32_s3_cam_wifi_camera` firmware captures a picture when an object is detected within 10 cm and sends it to a Python camera server on the local network. It beeps once, shows red for three seconds, beeps twice, then uploads the captured picture. The LED is green in standby. The board does not need to stay connected to the computer.

1. Edit `include/wifi_camera_config.h`: set `kWifiSsid` and `kWifiPassword` to your 2.4 GHz Wi-Fi details. Keep the generated `kCameraPassword`. If the file does not exist, copy `include/wifi_camera_config.example.h` to that name and set a strong camera password too. This local file is ignored by Git; keep it private. Credentials are also stored in the flashed firmware.
2. Copy `include/proximity_config.example.h` to `include/proximity_config.h`. Set `kEchoPin` to a verified free GPIO distinct from the buzzer, trigger and LED pins. The example uses the test settings TRIG 41, buzzer 14 and RGB LED 48; verify these against the wiring and board. The ECHO pin starts at -1, which disables detection until it is configured. The HC-SR04's 5 V ECHO output needs a voltage divider or level shifter before it reaches the ESP32. Adjust the distance and buzzer type if needed.
3. Connect the ESP32 to the PC by USB. Double-click `upload_wifi_camera.bat` in the `apps/esp32` folder to build and upload the Wi-Fi camera firmware. It uses `COM10` by default; edit the `PORT` line in the file if needed, or run `upload_wifi_camera.bat COM3` in Command Prompt to use another port. Uploading replaces the firmware currently on the board.

   Alternatively, from the repository root in Command Prompt:

   ```bat
   "%USERPROFILE%\.platformio\penv\Scripts\platformio.exe" run --project-dir apps/esp32 --environment esp32_s3_cam_wifi_camera --target upload --upload-port COM10
   ```

   If Command Prompt is already in `apps\esp32`, use `--project-dir .` instead of `--project-dir apps/esp32`. Replace `COM10` if the board uses a different port.
4. The board joins Wi-Fi after it starts. You can disconnect the USB cable from the PC and connect it to a suitable power adapter. Wait for it to start, and connect your PC to the same Wi-Fi network.
5. Open `http://cekrir-camera.local/` in a browser. If the name does not work, use the camera's IP address instead. Sign in with the camera username and password. The page describes the sensor-triggered behavior; it does not request a picture manually.

### Send pictures to the Python server

1. In `include/wifi_camera_config.h`, set `kBackendUrl` to your PC's local IPv4 address, for example `http://192.168.0.145:8001/camera/frame`. Find the PC address by running `ipconfig` in Command Prompt and looking under the active network adapter. If this address changes, update the URL and upload the firmware again using `upload_wifi_camera.bat`.
2. On the PC, double-click `apps/backend/run_camera.bat`. Keep its window open. The camera server reads the camera username and password from your local `wifi_camera_config.h`; it does not require PostgreSQL or Redis.
3. Power on the ESP32 and wait for it to join Wi-Fi. On the server PC, open `http://localhost:8001/camera`. Sign in with the same camera username and password. The page refreshes the picture every second. The direct image endpoint is `http://localhost:8001/camera/latest.jpg`; the ESP32 uploads to `POST /camera/frame`.
4. Press `Ctrl+C` in the server window to stop it. The server keeps only the latest picture in memory and clears it when stopped. If uploads stop, the last picture remains visible until the server restarts or receives a new picture.

The picture firmware captures at 640 × 480 once per detection. It rearms after the object moves away; it does not keep taking pictures while the object remains in front of the sensor. If no picture arrives, check the sensor pin settings, the Wi-Fi connection, the PC address, and the firewall on port 8001. The serial monitor reports the detection and upload result. Frames are not queued or retried if Wi-Fi or the server is unavailable. The standalone camera server uses port 8001 and is separate from the main backend API.

### Live video

The video build uses the same sensor-triggered firmware at 320 × 240 resolution. It no longer provides continuous live video. The standalone server's video page may continue showing the latest received picture between detections.

To find the current IP address, reconnect the board to the PC and use this command in Command Prompt, then press the board's reset button if no startup messages appear:

```bat
"%USERPROFILE%\.platformio\penv\Scripts\platformio.exe" device monitor --port COM10 --baud 115200
```

Look for `Camera IP` and close the monitor with `Ctrl+C`. You can also find the board in your router's connected-device list or reserve its IP address in the router. If a request fails, try restarting the board, check that both devices use the same network, and check for guest-network isolation or a VPN blocking local connections.

The browser connection uses plain HTTP: the password and pictures are not encrypted in transit. Use it only on a trusted local network and do not expose it to the internet. The existing `capture.bat` and Python capture tool require the separate USB diagnostic firmware described below; they do not capture from the Wi-Fi firmware. To switch between them, upload the matching PlatformIO environment.

## Camera check on Windows

The `esp32_s3_cam_camera_check` environment builds a separate diagnostic firmware for the common ESP32-S3 CAM N16R8 mapping. It does not need Wi-Fi, backend credentials, or a running API. The candidate mapping is in `include/camera_pins.h`; compare it with the vendor's board diagram before uploading. The ESP32-S3 chip marking alone does not establish the camera wiring.

PlatformIO Core is installed on this PC at `C:\Users\vince\.platformio\penv\Scripts\platformio.exe`. In PowerShell, from the repository root:

```powershell
$pio = "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe"
& $pio device list
& $pio run --project-dir apps/esp32 --environment esp32_s3_cam_camera_check
```

The connected USB serial adapter was detected as `COM10`; check the list again if you reconnect it. **Uploading replaces the firmware currently on the board.** Back up any firmware or data you need first. For a board with 16 MB of readable flash, this saves a complete image to the ignored `captures` directory:

```powershell
New-Item -ItemType Directory -Force apps/esp32/captures | Out-Null
$esptool = "$env:USERPROFILE\.platformio\packages\tool-esptool\esptool.exe"
& $esptool --port COM10 --baud 460800 read-flash 0 0x1000000 apps/esp32/captures/esp32-flash-backup.bin
```

The backup can contain credentials or private device data. Keep it private and do not commit it. If flash encryption or read protection is enabled, verify the vendor's recovery procedure before treating a readback as a restorable backup. A complete 16 MB read alone does not prove it can be restored.

To restore that raw backup on the same unencrypted board, after checking that the file is complete and the correct board is on `COM10`, run:

```powershell
& $esptool --port COM10 --baud 460800 write-flash --flash-mode keep --flash-freq keep --flash-size keep 0x0 apps/esp32/captures/esp32-flash-backup.bin
```

This replaces the board's entire 16 MB flash with the backup, including any configuration changed since it was saved. Flash encryption and secure boot were disabled on the board checked in this session; verify the actual board before restoring on another device. The restore procedure has not been exercised here.

With the correct board pinout and a completed backup, upload and inspect the diagnostic:

```powershell
& $pio run --project-dir apps/esp32 --environment esp32_s3_cam_camera_check --target upload --upload-port COM10
& $pio device monitor --port COM10 --baud 115200
```

Press reset if startup output is missing. A healthy run reports a camera sensor PID and `Capture OK` with dimensions and a JPEG byte count every three seconds. Initialization or capture errors point to the pin map, camera ribbon, sensor, power, or PSRAM configuration. Close the monitor with `Ctrl+C` before opening the port from another program.

To capture and open an image on Windows, double-click `capture.bat` in the `apps/esp32` folder. It uses `COM10` by default. If your board uses another port, edit the `PORT` line near the top of the batch file or run `capture.bat COM3` from Command Prompt with the correct port. Each capture replaces `captures/camera-check.jpg`.

You can also save an image using the Python environment installed by PlatformIO, which includes `pyserial`:

```powershell
$pioPython = "$env:USERPROFILE\.platformio\penv\Scripts\python.exe"
& $pioPython apps/esp32/tools/capture_camera_check.py --port COM10
```

Open `apps/esp32/captures/camera-check.jpg` and check focus, lighting, orientation, and whether a real label is readable. The byte count alone does not establish image quality. To capture five images at five-second intervals, add `--count 5 --interval 5`; the same output file is replaced on each capture. The capture directory is ignored by Git.

The `src` folder contains firmware that runs on the ESP32. The `tools` folder contains the optional Python image receiver and its tests, which run on the PC. The `captures` folder contains locally saved images and flash backups.

After editing `camera_check.cpp`, rerun the build command and upload the newly built diagnostic, then repeat the monitor and image capture. The board itself captures periodically once flashed; it does not compile itself. Change `kCheckIntervalMs` in that file to adjust the diagnostic's interval, then rebuild and upload. To return to the application firmware, configure `include/config.h`, then build and upload the `esp32_s3_cam` environment using the same commands with that environment name. The application scan interval is `kScanIntervalMs` in `config.h`; a detected barcode uses `kDetectionCooldownMs` instead.

For the normal firmware after each change, build and run the host-side policy tests with:

```powershell
& $pio run --project-dir apps/esp32 --environment esp32_s3_cam
& $pio test --project-dir apps/esp32 --environment native
```

The native tests check scan timing, retry limits, and input encoding on the PC. They do not test the camera sensor. Flash the application build and test a real label against the running API to check the full device-to-backend flow. The firmware needs a configured `config.h` for that step; without it, startup stops at configuration validation.

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

For example, set `kApiBaseUrl` to `http://192.168.1.20:8000/api/v1`. Set `CEKRIR_INGEST_API_KEY` in `apps/backend/.env` and the matching non-empty `kIngestApiKey` in the device config. The device requires this key to submit frames. It protects camera ingestion only; the rest of this prototype API still needs user authorization before internet exposure.

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
- Sends `POST /api/v1/detections/frame?courier=jne&camera_id=esp32-front-door`, raw `image/jpeg`, and the required `X-Ingest-Key` header.
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
# Buzzer test

`src/buzzer_test.cpp` beeps for 200 ms every two seconds. It is a separate
firmware from the camera program. It starts with `kBuzzerPin = -1`, so it does
not drive a pin until you edit it. Identify a free GPIO on your exact board
first; camera pins, boot pins, USB and flash/PSRAM pins must not be used. The
code rejects several known conflicts but cannot verify your specific board.

The test assumes an active buzzer controlled by a HIGH signal. Set
`kActiveBuzzer` to `false` for a passive buzzer (KY-006 modules are commonly
passive), or change `kActiveHigh` if your active module requires LOW. Confirm
the module's pin markings, drive voltage and current before connecting it;
never connect 5 V to an ESP32 GPIO. If the buzzer requires more current than
the GPIO can safely supply, use a suitable driver circuit.

After configuring the pin and wiring, connect the board over USB and run
`upload_buzzer_test.bat` (defaults to COM10, or pass a COM port as its first
argument). Uploading replaces the board's current firmware. Re-upload the
camera firmware when you want to use the camera again. Unplug power before
changing any wiring.

# Ultrasonic sensor test

`src/proximity_test.cpp` prints the HC-SR04 distance over serial every half
second and reports objects within 30 cm. Set `kTriggerPin` and `kEchoPin` to
two verified free GPIOs first; both default to -1. The pin check excludes
known conflicts, but the exact board schematic must still be checked.

The sensor's 5 V ECHO signal needs a voltage divider or level shifter before
the ESP32 input. Never connect it directly to the ESP32 GPIO. With the board
powered off, use the confirmed sensor wiring and common ground. Then run
`upload_proximity_test.bat`, and use the serial monitor at 115200 baud. The
upload replaces the buzzer or camera firmware currently on the board.

# BARDI CCTV snapshot POC

This is a local backend experiment. It captures one current frame from the BARDI RTSP stream. It does not use PostgreSQL or Redis, attach photos to deliveries, or expose a production camera route.

1. Install FFmpeg and the backend Python dependencies (`uv sync --project apps/backend --frozen`).
2. Copy `apps/backend/.env.example` to `apps/backend/.env` if needed. Set `CEKRIR_CCTV_RTSP_URL` to the ONVIF stream URI, and set `CEKRIR_CCTV_USERNAME` and `CEKRIR_CCTV_PASSWORD` to the camera's ONVIF credentials. The PRD records `rtsp://192.168.18.23:8554/Streaming/Channels/101` as a previously observed URI; confirm the camera's current LAN address before using it. The `.env` file is ignored by Git.
3. From the repository root, start the POC on loopback only:

   ```sh
   uv run --project apps/backend uvicorn cekrir.cctv_poc_app:app --host 127.0.0.1 --port 8002
   ```

4. In another terminal, trigger and save a snapshot:

   ```sh
   curl --fail-with-body --request POST http://127.0.0.1:8002/snapshot --output /tmp/cekrir-cctv-poc.jpg
   file /tmp/cekrir-cctv-poc.jpg
   ```

Open the JPEG and confirm it shows the **current** camera scene. Repeat several times while changing the scene, and record the total request time with `curl -w '%{time_total}\n'`. The service uses RTSP over TCP with FFmpeg's 10-second input timeout and a 15-second process timeout. Failed captures return HTTP 503 without including the URL or credentials in the response.

If the request fails during RTSP `DESCRIBE`, verify the camera's current ONVIF credentials and stream settings in the BARDI app before retrying. A `406` response alone does not establish whether credentials, stream configuration, or another camera condition caused the failure. Do not guess passwords repeatedly.

Run this POC only on a trusted machine on the camera's LAN. Its endpoint has no authentication, so keep the bind address at `127.0.0.1`. FFmpeg receives the credential-bearing URL as a process argument during capture; use a dedicated ONVIF account if the camera supports one.

## Local result, November 22, 2026

After the camera was re-paired and its ONVIF password updated, three separate `POST /snapshot` requests succeeded from the backend machine. Each request started a new FFmpeg process using RTSP/TCP and returned HTTP 200 with a verified 2880 × 1620 JPEG. The measured end-to-end request times were 4.41, 5.89, and 5.98 seconds; image sizes were 167,582, 180,648, and 183,594 bytes. The images differed, and the camera's visible timestamp advanced between captures. This establishes a working on-demand backend capture on this LAN in the tested configuration.

The current camera view was partly blocked by a nearby object. Placement and package visibility still need an actual delivery-scene test. These three samples do not establish long-run reliability or the scan-to-notification latency target. The POC does not persist photos or associate them with deliveries; those are later integration tasks.

## ONVIF direct JPEG test, November 22, 2026

The camera answered WS-Discovery at `192.168.18.23` and advertised its ONVIF service on port 8000. Authenticated `GetCapabilities`, `GetServiceCapabilities`, `GetProfiles`, and `GetSnapshotUri` calls all returned HTTP 200. The media service reported `SnapshotUri=true` and returned `http://192.168.18.23:8000/snapshot`.

Direct HTTP GET requests to that URL produced no HTTP response: the camera closed the connection immediately. This happened without authentication, with ONVIF credentials through HTTP Basic and Digest authentication, and with raw HTTP/1.0 and HTTP/1.1 requests. Port 80 refused connections. No JPEG was retrieved through the advertised snapshot URL in this test. The successful RTSP/FFmpeg route remains the validated capture path. The reason the advertised HTTP snapshot endpoint closes the connection is unknown; a firmware or configuration change could alter this result.

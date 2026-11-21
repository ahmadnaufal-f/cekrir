# Run the backend on an Ubuntu 22.04 VM

This guide installs Docker, runs the main FastAPI backend, PostgreSQL and Redis in containers, and installs Nginx on the VM as the HTTPS reverse proxy. PostgreSQL and Redis have no public ports; the API is published only at `127.0.0.1:8080` on the VM. Nginx forwards requests from ports 80 and 443 to it. Docker stores the database in a named volume so container restarts do not erase it.

The repository files must contain `compose.yaml`, `apps/backend/Dockerfile`, and `deploy/nginx/cekrir.conf`. Commit and push your changes first, or copy your working tree to the VM. No deployment happens when these files are added to the repository.

## 1. Prepare the VM

- Create an Ubuntu 22.04 64-bit VM with SSH access and a public IP address. A 2 GB RAM VM is a reasonable starting point for building the image; requirements depend on traffic.
- Set a DNS A record such as `api.example.com` to the VM's public IP. If you use IPv6, configure the AAAA record only when the VM is reachable over IPv6.
- In your cloud firewall, allow SSH on port 22 and web traffic on ports 80 and 443. Do not expose PostgreSQL 5432, Redis 6379, or API port 8080.
- Connect from your computer, substituting your VM username and IP:

  ```bash
  ssh ubuntu@YOUR_VM_IP
  ```

Everything below is run **on the VM**, except opening the final HTTPS URL in your browser. Replace `api.example.com` with your real domain.

## 2. Install Docker, Compose, Nginx and Git

These commands use [Docker's official Ubuntu installation method](https://docs.docker.com/engine/install/ubuntu/). On an existing VM, check Docker's instructions for conflicting packages first.

```bash
sudo apt update
sudo apt install -y ca-certificates curl git openssl nginx certbot python3-certbot-nginx
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Create Docker's Ubuntu 22.04 repository entry:

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker nginx
sudo docker version
sudo docker compose version
```

This guide uses `sudo docker` throughout, so adding your account to the `docker` group is not necessary.

## 3. Download the project

```bash
git clone https://github.com/ahmadnaufal-f/cekrir.git
cd cekrir
git checkout YOUR_BRANCH_NAME
```

Replace `YOUR_BRANCH_NAME` with the branch containing these files. Confirm `ls compose.yaml apps/backend/Dockerfile` succeeds. Private repositories need your normal GitHub authentication.

## 4. Configure secrets and seed accounts

```bash
cp deploy/vm.env.example .env.vm
chmod 600 .env.vm
nano .env.vm
```

In `nano`, edit the values and save with `Ctrl+O`, `Enter`, then `Ctrl+X`:

- Set `POSTGRES_PASSWORD`, `CEKRIR_JWT_SECRET_KEY`, and `CEKRIR_INGEST_API_KEY` to **different** random values. Run `openssl rand -hex 32` separately for each value and paste the results into the file. A hexadecimal PostgreSQL password also avoids URL-encoding problems. The ingestion key must match the key configured on a camera using the main API.
- Set `CEKRIR_SEED_ADMIN_EMAIL` and `CEKRIR_SEED_MEMBER_EMAIL` to the intended users' actual email addresses. Set different strong passwords for the two accounts, each at least 12 characters and at most 72 UTF-8 bytes. `openssl rand -hex 24` provides a suitable value. Set `CEKRIR_SEED_LOCATION` to the location name.
- On a fresh database, migration `20261120_0007` creates both accounts as **already verified** and assigns the location to the admin. Choose those addresses carefully; this seed bypasses email verification. The member is not automatically assigned to the location.
- To enable Resend, uncomment and fill `CEKRIR_EMAIL_PROVIDER=resend`, `CEKRIR_RESEND_API_KEY`, `CEKRIR_RESEND_FROM`, and the HTTPS `CEKRIR_VERIFICATION_URL`. A verified Resend sending domain is required. Otherwise the server starts, but registration cannot send verification emails until email delivery is configured.
- If you have a web frontend, set `CEKRIR_CORS_ORIGINS` to its exact HTTPS origin as a JSON array. Do not put API keys in the frontend.

`.env.vm` contains private credentials. Keep the file private, do not commit or paste it into chat, and back it up securely. Compose reads it through `--env-file`; the Docker build excludes backend `.env` files.

## 5. Build and start the containers

```bash
sudo docker compose --env-file .env.vm up -d --build
sudo docker compose --env-file .env.vm ps
sudo docker compose --env-file .env.vm logs --tail=80 migrate
```

The first build downloads images and Python dependencies. Compose waits for PostgreSQL to be healthy, runs the Alembic migration service once, then starts the API after migration succeeds and Redis is healthy. The `migrate` container exiting with code 0 is normal. If the migration fails, check its logs and the seed settings; the API will not start successfully until migration completes.

Test from the VM:

```bash
curl -fsS http://127.0.0.1:8080/health
```

Expect JSON containing `"status":"ok"`. The tracking provider defaults to a demo and does not contact a courier. For HTTPS and email setup, continue below before using real passwords over the internet.

## 6. Set up Nginx

```bash
sudo cp deploy/nginx/cekrir.conf /etc/nginx/sites-available/cekrir
sudo nano /etc/nginx/sites-available/cekrir
```

Replace `YOUR_DOMAIN` with your actual DNS name, such as `api.example.com`. Save and exit, then enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/cekrir /etc/nginx/sites-enabled/cekrir
sudo nginx -t
sudo systemctl reload nginx
```

The configuration forwards HTTP requests and WebSocket upgrades to the loopback-only API. It disables access logging so verification tokens in URLs are not written into Nginx access logs. Nginx error logs are still available at `/var/log/nginx/error.log`.

Check `http://api.example.com/health` from a browser. This first connection is unencrypted; do not sign in, submit API keys, or send personal data over HTTP.

## 7. Enable HTTPS

Once DNS points to the VM and port 80 is reachable from the internet, ask Certbot to configure Nginx:

```bash
sudo certbot --nginx -d api.example.com
sudo certbot renew --dry-run
```

Follow the prompts and enable the HTTP-to-HTTPS redirect. Certificates require a real domain and internet-reachable port 80; a raw IP address is not sufficient for this workflow. Certbot changes the Nginx configuration and installs certificate renewal. See the [Certbot Nginx instructions](https://certbot.eff.org/instructions?ws=nginx&os=ubuntufocal).

Open `https://api.example.com/health` and `https://api.example.com/docs`. You can now log in using the seeded admin credentials through `POST /api/v1/auth/login`. The API docs describe the other endpoints. Restart the API if you change runtime values in `.env.vm`:

```bash
sudo docker compose --env-file .env.vm up -d --force-recreate api
```

## 8. Operate and update

Run these from the project folder on the VM:

```bash
# Check containers and logs
sudo docker compose --env-file .env.vm ps
sudo docker compose --env-file .env.vm logs --tail=100 api
sudo docker compose --env-file .env.vm logs --tail=100 db

# After pulling new code, build and explicitly apply new migrations before restarting the API
git pull
sudo docker compose --env-file .env.vm build migrate
sudo docker compose --env-file .env.vm run --rm migrate
sudo docker compose --env-file .env.vm up -d api
```

Before database migrations in an important environment, make and test a backup. For example, this saves a PostgreSQL custom-format dump to a private file in the current directory:

```bash
umask 077
sudo docker compose --env-file .env.vm exec -T db pg_dump -U cekrir -d cekrir -Fc > cekrir-backup.dump
```

Store backups somewhere separate from the VM and test restoration. `docker compose down` stops the stack but preserves the named database volume; **do not use `down -v`** unless you intend to delete it. Changing `POSTGRES_PASSWORD` in `.env.vm` after the volume has already been initialized does not change the database user's password; update PostgreSQL and the configuration together using a planned credential rotation.

## 9. Connect cameras and email

The VM runs the **main backend API**, not the separate local camera-preview server. The ESP32 firmware that submits detections needs the HTTPS API base URL ending in `/api/v1`, the matching ingestion key, and the proper root CA in its device configuration. The Wi-Fi preview firmware that posts to `/camera/frame` does not automatically become a package detector. See [the ESP32 guide](../apps/esp32/README.md) and [API reference](../apps/backend/API.md).

For location emails, first assign the camera ID and members to an admin-owned location through the documented location endpoints. Unassigned cameras do not send location emails. The shared ingestion key does not identify individual cameras, so per-device credentials are still needed before relying on location attribution across untrusted devices. The existing in-app notification feed is global, and email delivery is best-effort without a retry queue.

## Troubleshooting

- **The API will not start:** inspect the `migrate`, `db`, and `api` logs. Confirm `.env.vm` has all required values and the database password uses hexadecimal characters.
- **Nginx returns 502:** run `curl http://127.0.0.1:8080/health` on the VM, then check the API logs. Confirm Nginx points to port 8080.
- **Certbot fails:** verify the domain resolves to this VM and port 80 is reachable in the cloud firewall; check `sudo nginx -t`.
- **Browser frontend reports CORS errors:** set `CEKRIR_CORS_ORIGINS` to the exact frontend HTTPS origin and recreate the API container.
- **No mail arrives:** check the Resend API key, verified sender domain, `CEKRIR_VERIFICATION_URL`, and provider dashboard. Package mail also requires a camera-to-location mapping and verified, active recipients.

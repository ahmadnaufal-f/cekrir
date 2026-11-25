# Run the backend on an Ubuntu 22.04 VM

This guide installs Docker, runs the main FastAPI backend, PostgreSQL and Redis in containers, and installs Nginx on the VM as the HTTPS reverse proxy. PostgreSQL and Redis have no public ports; the API is published on port 8000 on the VM. Nginx forwards requests from ports 80 and 443 to it. Restrict access to port 8000 in the VM provider's firewall. Docker stores the database in a named volume so container restarts do not erase it.

The repository files must contain `apps/backend/compose.yaml`, `apps/backend/Dockerfile`, and `deploy/nginx/cekrir.conf`. Commit and push your changes first, or copy your working tree to the VM. No deployment happens when these files are added to the repository.

## 1. Prepare the VM

- Create an Ubuntu 22.04 64-bit VM with SSH access and a public IP address. A 2 GB RAM VM is a reasonable starting point for building the image; requirements depend on traffic.
- Set a DNS A record such as `api.example.com` to the VM's public IP. If you use IPv6, configure the AAAA record only when the VM is reachable over IPv6.
- In your cloud firewall, allow SSH on port 22 and web traffic on ports 80 and 443. Do not expose PostgreSQL 5432, Redis 6379, or API port 8000.
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

Replace `YOUR_BRANCH_NAME` with the branch containing these files. Confirm `ls apps/backend/compose.yaml apps/backend/Dockerfile` succeeds. Private repositories need your normal GitHub authentication.

## 4. Configure secrets and seed accounts

Run the remaining commands from the backend directory:

```bash
cd apps/backend
```

If `apps/backend/.env` already exists, keep it and add any missing settings from `../../deploy/vm.env.example` instead of overwriting it. If upgrading from the previous VM setup, copy your existing settings first, choosing whichever file you used:

```bash
cp -n ../../.env .env
# Or, if your previous file was named .env.vm:
cp -n ../../.env.vm .env
```

For a new setup, create `.env` from the example. This command will not overwrite an existing `.env`:

```bash
cp -n ../../deploy/vm.env.example .env
chmod 600 .env
nano .env
```

In `nano`, edit the values and save with `Ctrl+O`, `Enter`, then `Ctrl+X`:

- Set `POSTGRES_PASSWORD` to the password for the PostgreSQL user `postgres`. This Compose configuration expects a password containing only letters and numbers, so it can be safely used in the backend's connection URL. For a fresh database, choose a strong password. Set `CEKRIR_JWT_SECRET_KEY` and `CEKRIR_INGEST_API_KEY` to **different** random values. Run `openssl rand -hex 32` separately for each key and paste the results into the file. The ingestion key must match the key configured on a camera using the main API.
- Set `CEKRIR_SEED_ADMIN_EMAIL` and `CEKRIR_SEED_MEMBER_EMAIL` to the intended users' actual email addresses. Set different strong passwords for the two accounts, each at least 12 characters and at most 72 UTF-8 bytes. `openssl rand -hex 24` provides a suitable value. Set `CEKRIR_SEED_LOCATION` to the location name.
- On a fresh database, migration `20261120_0007` creates both accounts as **already verified** and assigns the location to the admin. Choose those addresses carefully; this seed bypasses email verification. The member is not automatically assigned to the location.
- To enable Resend, uncomment and fill `CEKRIR_EMAIL_PROVIDER=resend`, `CEKRIR_RESEND_API_KEY`, `CEKRIR_RESEND_FROM`, and the HTTPS `CEKRIR_VERIFICATION_URL`. A verified Resend sending domain is required. Otherwise the server starts, but registration cannot send verification emails until email delivery is configured.
- Set `CEKRIR_CORS_ORIGINS` to include the hosted frontend and Capacitor origins. An existing `.env` overrides the backend defaults, so update its list explicitly:

  ```dotenv
  CEKRIR_CORS_ORIGINS='["https://cekrir.arkaes.dev","http://localhost:5173","http://127.0.0.1:5173","capacitor://localhost","http://localhost","https://localhost"]'
  ```

  Include any other trusted frontend origins your deployment needs. Do not put API keys in the frontend.

`apps/backend/.env` contains private credentials. Keep the file private, do not commit or paste it into chat, and back it up securely. Compose reads it automatically when run from this directory; the Docker build excludes it.

**If the VM already has database data**, verify the old Compose project name before starting the new configuration:

```bash
sudo docker compose ls --all
sudo docker volume ls --filter name=vm_postgres_data
```

The volume is normally named `<project-name>_vm_postgres_data`. The moved Compose file defaults to project name `cekrir`, preserving `cekrir_vm_postgres_data`. If your existing volume has another project prefix, add `COMPOSE_PROJECT_NAME=your-old-project-name` to `.env` before running Compose. Verify the exact old volume and take a tested backup first; otherwise Compose could create a new empty volume. The project name can also be overridden by a shell environment variable or the `-p` option.

Earlier Compose versions initialized PostgreSQL with user `cekrir`. An existing volume does not automatically switch to user `postgres` or adopt a new password. Before starting the updated configuration, confirm that its database has the `postgres` role with the intended password. If not, keep using the existing database credentials until the role is provisioned; do not delete the volume. When backing up an older database, use its existing PostgreSQL user in the `pg_dump -U` option.

## 5. Build and start the containers

```bash
sudo docker compose build --pull --no-cache api
sudo docker compose up -d db redis
sudo docker compose run --rm api alembic -c /workspace/apps/backend/alembic.ini upgrade head
sudo docker compose up -d api
sudo docker compose ps
```

The first build downloads base images and Python dependencies. It builds one shared image from `apps/backend/Dockerfile`; the `db`, `redis`, and `api` services run that image in three separate containers with different commands. The database container retains the official PostgreSQL entrypoint and the PostgreSQL 17 Alpine base. The build installs available Alpine package updates, but this does not guarantee that all image vulnerabilities are fixed. Scan the completed image before deployment. The `run --rm` command temporarily uses the API image to apply Alembic migrations, then removes that one-off container. Compose passes the seed settings from `.env` into the API container. Recreate the container after editing `.env` to update its environment. Migrations do not run automatically on container startup; run the Alembic command separately. If the migration fails, fix the error and rerun it before starting the API. Compose waits for PostgreSQL and Redis to be healthy before starting the API.

The API's Uvicorn command is visible in `apps/backend/compose.yaml` under `api.command`. It starts `cekrir.main:app` on port 8000 inside the container. The shared image defaults to PostgreSQL; Compose supplies the Redis and API commands for the other containers.

After building, if Docker Scout is installed on the VM, inspect the **final shared image** for critical and high vulnerabilities:

```bash
sudo docker scout cves --only-severity critical,high cekrir-stack:vm
```

Check the reported package, CVE, and fix availability before deployment. The `postgres:17-alpine` tag can point to a different image over time. Rebuilding with `--pull --no-cache` fetches current base images and reruns Alpine package updates, but it does not guarantee that all findings are fixed. The shared image also contains Redis, Python, and application dependencies, which need their own review.

### How PostgreSQL is set up

You do **not** need to install PostgreSQL separately on Ubuntu. The shared image is based on PostgreSQL 17 Alpine. The `db` service starts PostgreSQL in Docker. The first time it starts with a new database volume, it creates:

- Database: `cekrir`
- Database user: `postgres`
- Password: the `POSTGRES_PASSWORD` value you put in `.env`

The Dockerfile supplies the `postgres` user and `cekrir` database defaults; Compose supplies the password from `.env`. The official PostgreSQL entrypoint creates them only when the database volume is empty. The one-off Alembic command then creates the tables and seed records. The backend connects to the database using the Docker service name `db`; neither PostgreSQL nor Redis is exposed on the VM's public network. The `vm_postgres_data` Docker volume keeps the database files when containers restart.

If the existing volume was initialized with the earlier `cekrir` PostgreSQL user, changing `POSTGRES_USER` here does not create a `postgres` role or change its password. Confirm the existing roles and take a backup before switching credentials; the earlier `cekrir` user may still be needed to access that database.

Check that PostgreSQL is ready and that Alembic created its tables:

To connect with DBeaver through SSH, see the [DBeaver setup guide](dbeaver-setup.md), which explains how to add a VM-only PostgreSQL port mapping.

```bash
sudo docker compose exec db pg_isready -U postgres -d cekrir
sudo docker compose exec db psql -U postgres -d cekrir -c '\dt'
sudo docker compose exec db psql -U postgres -d cekrir -c 'SELECT version_num FROM alembic_version;'
```

You should see `accepting connections`, a table list, and the latest migration version. These commands use `psql` **inside the database container**, so the VM does not need a separate PostgreSQL client installation. The password and database are initialized only when the volume is first created; changing the value in `.env` later does not automatically change the database password.

Test from the VM:

```bash
curl -fsS http://127.0.0.1:8000/health
```

Expect JSON containing `"status":"ok"`. The tracking provider defaults to a demo and does not contact a courier. For HTTPS and email setup, continue below before using real passwords over the internet.

## 6. Set up Nginx

For a detailed walkthrough using the Cekrir API domain, see the [Nginx setup guide](nginx-setup.md).

```bash
sudo cp ../../deploy/nginx/cekrir.conf /etc/nginx/sites-available/cekrir
sudo nano /etc/nginx/sites-available/cekrir
```

Replace `YOUR_DOMAIN` with your actual DNS name, such as `api.example.com`. Save and exit, then enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/cekrir /etc/nginx/sites-enabled/cekrir
sudo nginx -t
sudo systemctl reload nginx
```

The configuration forwards HTTP requests and WebSocket upgrades to the API through the VM's loopback address. It disables access logging so verification tokens in URLs are not written into Nginx access logs. Nginx error logs are still available at `/var/log/nginx/error.log`.

Check `http://api.example.com/health` from a browser. This first connection is unencrypted; do not sign in, submit API keys, or send personal data over HTTP.

## 7. Enable HTTPS

Once DNS points to the VM and port 80 is reachable from the internet, ask Certbot to configure Nginx:

```bash
sudo certbot --nginx -d api.example.com
sudo certbot renew --dry-run
```

Follow the prompts and enable the HTTP-to-HTTPS redirect. Certificates require a real domain and internet-reachable port 80; a raw IP address is not sufficient for this workflow. Certbot changes the Nginx configuration and installs certificate renewal. See the [Certbot Nginx instructions](https://certbot.eff.org/instructions?ws=nginx&os=ubuntufocal).

Open `https://api.example.com/health` and `https://api.example.com/docs`. You can now log in using the seeded admin credentials through `POST /api/v1/auth/login`. The API docs describe the other endpoints. Restart the API if you change runtime values in `.env`:

```bash
sudo docker compose up -d --force-recreate api
```

## 8. Operate and update

Run these from `apps/backend` on the VM. **If this VM already has PostgreSQL data, take and verify a backup before changing the image or running migrations.** The configuration keeps the existing `vm_postgres_data` volume name, but a database image change should be tested against a restored backup on a separate VM before using it with the original volume.

```bash
# Check containers and logs
sudo docker compose ps
sudo docker compose logs --tail=100 api
sudo docker compose logs --tail=100 db

# Back up the existing database before updating; keep this file outside the VM too
umask 077
sudo docker compose exec -T db pg_dump -U postgres -d cekrir -Fc > cekrir-backup.dump

# After testing the new image and backup restoration, pull and update
git pull
sudo docker compose build --pull --no-cache api
sudo docker compose run --rm api alembic -c /workspace/apps/backend/alembic.ini upgrade head
sudo docker compose up -d
```

Before database migrations in an important environment, make and test a backup. For example, this saves a PostgreSQL custom-format dump to a private file in the current directory:

```bash
umask 077
sudo docker compose exec -T db pg_dump -U postgres -d cekrir -Fc > cekrir-backup.dump
```

Store backups somewhere separate from the VM and test restoration. `sudo docker compose down` stops the stack but preserves the named database volume; **do not add `-v`** unless you intend to delete it. Changing `POSTGRES_PASSWORD` in `.env` after the volume has already been initialized does not change the database user's password; update PostgreSQL and the configuration together using a planned credential rotation.

## 9. Connect cameras and email

The VM runs the **main backend API**, not the separate local camera-preview server. The ESP32 firmware that submits detections needs the HTTPS API base URL ending in `/api/v1`, the matching ingestion key, and the proper root CA in its device configuration. The Wi-Fi preview firmware that posts to `/camera/frame` does not automatically become a package detector. See [the ESP32 guide](../apps/esp32/README.md) and [API reference](../apps/backend/API.md).

For location emails, first assign the camera ID and members to an admin-owned location through the documented location endpoints. Unassigned cameras do not send location emails. The shared ingestion key does not identify individual cameras, so per-device credentials are still needed before relying on location attribution across untrusted devices. The existing in-app notification feed is global, and email delivery is best-effort without a retry queue.

## Troubleshooting

- **The API will not start:** inspect the `db` and `api` logs. If migrations failed, check the output from the one-off Alembic command. Confirm `.env` has all required values and the database password uses only letters and numbers.
- **Nginx returns 502:** run `curl http://127.0.0.1:8000/health` on the VM, then check the API logs. Confirm Nginx points to port 8000.
- **Certbot fails:** verify the domain resolves to this VM and port 80 is reachable in the cloud firewall; check `sudo nginx -t`.
- **Browser frontend reports CORS errors:** set `CEKRIR_CORS_ORIGINS` to the exact frontend HTTPS origin and recreate the API container.
- **No mail arrives:** check the Resend API key, verified sender domain, `CEKRIR_VERIFICATION_URL`, and provider dashboard. Package mail also requires a camera-to-location mapping and verified, active recipients.

# Set up Nginx for the Cekrir API

This guide connects `https://api.cekrir.bakuretsumagic.my.id` to the backend on an Ubuntu 22.04 VM. Nginx runs on the VM and forwards requests to the Docker backend at `127.0.0.1:8000`.

## 1. Point the domain to the VM

At your DNS provider, create an A record for `api.cekrir.bakuretsumagic.my.id` pointing to your VM's public IPv4 address. If you manage `bakuretsumagic.my.id`, the host/name is usually `api.cekrir`. DNS changes may take time to propagate. Only add an AAAA record if the VM is reachable over IPv6.

## 2. Check the backend

Connect to the VM, then go to `apps/backend` inside the repository:

```bash
cd ~/cekrir/apps/backend
sudo docker compose ps
curl -fsS http://127.0.0.1:8000/health
```

Adjust the path if you cloned the repository elsewhere. The health request should return a response. If it fails, check `sudo docker compose logs --tail=100 api` and fix the backend first. The [VM setup guide](ubuntu-vm-setup.md) explains how to build and start it.

## 3. Install Nginx and Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable --now nginx
```

## 4. Configure Nginx

If `/etc/nginx/sites-available/cekrir` already contains a configuration you use, back it up before replacing it. In particular, replacing a configuration previously edited by Certbot can remove its HTTPS settings.

Open the configuration file:

```bash
sudo nano /etc/nginx/sites-available/cekrir
```

Paste the following complete configuration into the file:

```nginx
map $http_upgrade $cekrir_connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    listen [::]:80;
    server_name api.cekrir.bakuretsumagic.my.id;

    access_log off;
    client_max_body_size 512k;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $cekrir_connection_upgrade;
        proxy_read_timeout 3600s;
    }
}
```

Save with **Ctrl+O**, press **Enter**, and exit with **Ctrl+X**. This configuration forwards traffic to port 8000 and supports WebSocket connections. It turns off access logs to avoid recording verification tokens in URLs.

Enable the configuration and test it:

```bash
sudo ln -sf /etc/nginx/sites-available/cekrir /etc/nginx/sites-enabled/cekrir
sudo nginx -t
```

If the test succeeds, reload Nginx:

```bash
sudo systemctl reload nginx
```

## 5. Allow web traffic

Allow inbound TCP ports **80** and **443** in your VM provider's firewall or security group. If UFW is active on the VM, allow Nginx there too:

```bash
sudo ufw status
sudo ufw allow 'Nginx Full'
```

If UFW is inactive and you decide to enable it, allow SSH first so you can still connect to the VM.

## 6. Enable HTTPS

Once DNS points to the VM and port 80 is reachable from the internet, obtain a certificate:

```bash
sudo certbot --nginx -d api.cekrir.bakuretsumagic.my.id
```

Follow the prompts and choose HTTP-to-HTTPS redirection if asked. Test automatic certificate renewal:

```bash
sudo certbot renew --dry-run
```

## 7. Test the API

Open these addresses in a browser:

- Health check: https://api.cekrir.bakuretsumagic.my.id/health
- API documentation: https://api.cekrir.bakuretsumagic.my.id/docs

If you get **502 Bad Gateway**, check the backend health command from step 2 and its logs. If Certbot fails, check DNS, public port 80, and `sudo nginx -t`. Nginx errors are available in `/var/log/nginx/error.log`.

# Connect DBeaver to the VM database

The PostgreSQL container listens on port 5432. Add a VM-only port mapping so DBeaver can reach it through an SSH tunnel without publishing PostgreSQL to the internet. This guide assumes SSH access to the VM is already working.

## Apply the Compose change on the VM

On the VM, open `apps/backend/compose.yaml` and add these lines under the `db` service:

```yaml
ports:
  - '127.0.0.1:15432:5432'
```

Then run these commands from `apps/backend`:

```bash
sudo docker compose up -d --no-deps db
sudo docker compose ps db
```

Recreating the database container briefly interrupts database connections. The existing `vm_postgres_data` volume is retained; do not add `-v` or remove the volume. Confirm that the existing PostgreSQL role and password match your configuration. The mapping uses VM port 15432 to avoid conflicting with a PostgreSQL server already using port 5432.

## Configure DBeaver on your computer

1. Choose **New Database Connection** and select **PostgreSQL**.
2. On the **Main** tab, enter:
   - Host: `127.0.0.1`
   - Port: `15432`
   - Database: `cekrir`
   - Username: `postgres`
   - Password: the PostgreSQL password from the VM's `apps/backend/.env`.
3. Open the **SSH** tab (or add SSH under network settings) and enable **Use SSH Tunnel**.
4. Set the SSH host to `103.103.23.125`, the SSH port to `22` unless your VM uses another port, and the username and authentication method to those you normally use to SSH into the VM. Select your private key or enter your SSH password as appropriate.
5. Test the SSH tunnel, then choose **Test Connection**. Let DBeaver download the PostgreSQL driver if asked, then save the connection.

The host and port in the Main tab refer to PostgreSQL **on the VM**, accessed through SSH. The SSH credentials are separate from the database credentials. DBeaver's [SSH configuration guide](https://dbeaver.com/docs/dbeaver/SSH-Configuration/) has screenshots and additional options.

If the connection fails, check that the database container is healthy, the VM port 15432 is available, and you can log in to the VM over SSH. If the existing volume was initialized with a different PostgreSQL user or password, use its actual database credentials; changing `.env` alone does not change an existing user's password.

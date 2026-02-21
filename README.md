## Development

Access from other devices on the same network:
 - The app binds to all interfaces by default (`0.0.0.0`), so you can open it
	from another device on the same LAN using the host machine's IP, for example
	`http://192.168.1.42:5000` (the exact IP is printed when the app starts).
	- If you need to expose the app to the public internet, use a secure tunnel
		such as `ngrok` or place the app behind a properly configured reverse proxy
		with HTTPS.

### Public access from any area (recommended)

For parents outside your Wi‑Fi/network, deploy once on Render and share the permanent HTTPS URL.

- Follow [DEPLOY.md](DEPLOY.md).
- After deploy, share your Render URL (example: `https://grades4.onrender.com`).
- This is more reliable than temporary tunnel links.

### LAN Access (Windows)

If parents need to open the site from other devices on the same Wi‑Fi/ LAN, follow these easy options (choose one):

- **Quick browser check:** try a hard refresh (Ctrl+F5) or open in an Incognito/Private window to rule out caching. Confirm the address bar shows the LAN IP (e.g. `http://192.168.100.79:5000`).

- **Preferred (make the network Private):** run the PowerShell helper to set the current Public network to Private (run in an elevated/admin PowerShell):

```powershell
.\scripts\set_network_private.ps1
```

- **Alternative (open firewall port 5000):** run the helper to allow inbound TCP 5000 (run in admin PowerShell). By default it adds the rule for the `Private` profile; pass `-Profile Public` if you prefer:

```powershell
.\scripts\open_firewall_port_5000.ps1
# to allow on Public networks (less recommended):
.\scripts\open_firewall_port_5000.ps1 -Profile Public
```

- **To remove the firewall rule later:**

```powershell
.\scripts\close_firewall_port_5000.ps1
```

- **If you can't run admin commands:** use a tunneling tool like `ngrok` to share the local server temporarily. Example:

```powershell
# install ngrok and run:
ngrok http 5000
# then share the forwarded URL shown by ngrok
```

- **One command (app + public link):** if ngrok is installed and configured, run:

```powershell
.\scripts\start_public_app.ps1
```

For custom port:

```powershell
.\scripts\start_public_app.ps1 -Port 5001
```

Notes:
- These steps require administrator privileges for changing network profile or firewall rules.
- After making changes, restart the Flask app and confirm the startup message shows the LAN IP.

# Grade 4 Math Results — Simple Lookup

This small app lets parents check Grade 4 Math exam results by entering a Student ID.

Quick setup (Windows):

1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Create the sample database

```powershell
python generate_db.py
```

4. (Optional) Set a stronger secret key via environment variable

```powershell
$env:SECRET_KEY = 'a-strong-secret'
```

5. Run

```powershell
python app.py
```

### Keep link working after closing VS Code (Windows)

If you close VS Code while running `python app.py` in its terminal, the app stops and the link stops working.
Start the app in background instead:

```powershell
.\scripts\start_app_background.ps1
```

Stop it later:

```powershell
.\scripts\stop_app_background.ps1
```

For a custom port:

```powershell
.\scripts\stop_app_background.ps1 -Port 5001
```

Check status anytime:

```powershell
.\scripts\status_app_background.ps1
```

For a custom port:

```powershell
.\scripts\status_app_background.ps1 -Port 5001
```

If `app.pid` is stale/invalid, the status script removes it automatically.

Notes:
- The script writes PID to `app.pid`, stdout logs to `app.log`, and errors to `app.err.log`.
- You can pass another port: `./scripts/start_app_background.ps1 -Port 5001`.
- Use `http://<your-ip>:5000` (or chosen port) for other devices on your LAN.

Open http://localhost:5000 in a mobile device browser or emulator.

Security notes:
- Inputs are validated server-side and queries use parameterized SQL to prevent injection.
- Rate limiting protects the lookup endpoint from abuse.
- Use HTTPS and a strong `SECRET_KEY` in production.

Reverse proxy / trusted proxy note:
- If you run the app behind a reverse proxy (nginx, IIS, etc.) that sets `X-Forwarded-For`, set the `TRUSTED_PROXIES` environment variable to a comma-separated list of proxy IPs so the app can correctly identify the real client IP for local-only routes like `/admin/token-login`.

Example (PowerShell):
```powershell
$env:TRUSTED_PROXIES = "127.0.0.1,::1"
```

Access from other devices on the same network:
- The app binds to all interfaces by default (`0.0.0.0`), so you can open it
	from another device on the same LAN using the host machine's IP, for example
	`http://192.168.1.42:5000` (the exact IP is printed when the app starts).
- If you need to expose the app to the public internet, use a secure tunnel
	such as `ngrok` or place the app behind a properly configured reverse proxy
	with HTTPS.

Example (find LAN IP and run):
```powershell
# On the host machine, set the trusted proxies if using a reverse proxy
$env:TRUSTED_PROXIES = "127.0.0.1,::1"

python app.py
# then open http://<host-lan-ip>:5000 from your phone or another computer
```

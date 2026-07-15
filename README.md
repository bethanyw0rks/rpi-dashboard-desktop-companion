# rpi-dashboard-desktop-companion
Companion app for rpi-dashboard that can run on a desktop and be queried by an RPI for information about the current active application and more.

## What this project does

This app exposes a lightweight API from your desktop computer so another device on your network, such as a Raspberry Pi, can request information about the currently active application.

## Prerequisites

Before you begin, make sure you have:

- Python 3.10 or newer installed
- A terminal or command prompt
- Access to the project folder on your computer

## Step-by-step setup

### 1. Open the project folder

In your terminal, change into the project directory:

```bash
cd /path/to/desktop-companion-rpi-dashboard
```

### 2. Create a virtual environment

A virtual environment keeps this project’s Python packages isolated from other Python projects on your computer.

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

The virtual environment is created in a folder named `.venv` inside the project. You will usually activate it each time you work on the project.

### 3. Install dependencies

The project dependencies are listed in `requirements.txt`. Install them with:

```bash
pip install -r requirements.txt
```

If `pip` is not recognized, try:

```bash
python3 -m pip install -r requirements.txt
```

### 4. Configure CORS (optional)

If your frontend or another service will call this API from a browser, create a `.env` file in the project root with a comma-separated list of allowed origins:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://bethanyw0rks.github.io
```

If you leave this unset, the API will default to allowing common local development origins such as `http://localhost:3000`.

To limit calendar results to a specific account or calendar, add a `CALENDAR_FILTER` entry to the same `.env` file. The value is matched against the calendar title, account description, and source identifier, so a value like `bethany@coursearc.com` will only return events from that calendar/account.

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://bethanyw0rks.github.io
CALENDAR_FILTER=bethany@coursearc.com
```

### 5. Run the API

Start the local API server with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8010
```

This will start the app so it can be reached from other devices on your local network.

If you are running the app with a launch agent on macOS, use the wrapper script in [start_api.sh](start_api.sh) so launchd starts the server from the project directory using the virtual environment. This avoids the common issue where launchd does not inherit the shell environment from your terminal session.

### 6. Test it locally

In another terminal window, you can test the server with:

```bash
curl http://127.0.0.1:8010/health
```

You should receive a JSON response like:

```json
{"status":"ok"}
```

## Endpoints

- `GET /health` returns a simple health payload.
- `GET /api/active-app` returns the current frontmost application details, including its name, bundle identifier, process ID, and platform.
- `GET /api/calendar-next` returns the next upcoming calendar event from your Apple Calendar.
- `GET /api/calendar-now` returns the currently underway calendar event, if one is active now.

## Useful tips

- If you close the terminal where the server is running, the API will stop.
- To keep it running after a reboot, you may want to set it up as a background service or launch agent, depending on your operating system.
- If you are using a Raspberry Pi or another device on the same network, you can access the API using the desktop computer’s local IP address and port `8010`.

- Calendar access: The `calendar-next` and `calendar-now` endpoints use macOS EventKit via `pyobjc-framework-EventKit`. macOS will prompt you to grant Calendar permission the first time the endpoint is used; allow access in System Settings → Privacy & Security → Calendars. If permission is denied or EventKit is unavailable, the endpoint will return empty fields for events.

- To trigger the permission prompt and verify access, run the server from your virtual environment and call the endpoint:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8010

# In another terminal, trigger the endpoint which will prompt for Calendar access
curl http://127.0.0.1:8010/api/calendar-next
```

- The macOS permission dialog will show the process requesting access (for example `Terminal` or `python`). You can review or revoke Calendar permissions at System Settings → Privacy & Security → Calendars.

## macOS launch agent (optional)

If you are using a Mac and want the companion app to start automatically after a reboot, a launch agent can do that for you. The most reliable setup is to point the agent at a small wrapper script that starts the app from the project directory using the virtual environment.

### 1. Create the wrapper script

Create a file named [start_api.sh](start_api.sh) in the project root with the following contents:

```bash
#!/bin/bash
set -euo pipefail

cd /Users/your-username/path/to/desktop-companion-rpi-dashboard
exec /Users/your-username/path/to/desktop-companion-rpi-dashboard/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Then make it executable:

```bash
chmod +x start_api.sh
```

### 2. Create the plist file

Create a file at:

```bash
~/Library/LaunchAgents/com.desktop-companion.api.plist
```

Put the following contents in it:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.desktop-companion.api</string>

    <key>ProgramArguments</key>
    <array>
      <string>/Users/your-username/path/to/desktop-companion-rpi-dashboard/start_api.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/your-username/path/to/desktop-companion-rpi-dashboard</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/your-username/path/to/desktop-companion-rpi-dashboard/api.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/your-username/path/to/desktop-companion-rpi-dashboard/api.error.log</string>
  </dict>
</plist>
```

Replace the placeholder paths with your actual username and project location.

### 3. Load the launch agent

Run:

```bash
launchctl bootout gui/$UID/com.desktop-companion.api 2>/dev/null || true
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.desktop-companion.api.plist
```

If you need to force a restart after changing the script or plist, use:

```bash
launchctl kickstart -k gui/$UID/com.desktop-companion.api
```

### 4. Verify it

You can check whether the service is loaded with:

```bash
launchctl list | grep desktop-companion
```

And test the API with:

```bash
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/api/calendar-next
```

If you want the service to start on boot automatically, the `RunAtLoad` setting handles that for you.

#### 5. Switching between launch agent and manual runs 

Switch from launch agent to manual launch: 

```
launchctl bootout gui/$UID/com.desktop-companion.api 2>/dev/null || true
pkill -f "uvicorn app.main:app" || true
cd /Users/bethanyb00m/ProjectDev/desktop-companion-rpi-dashboard
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Switch between from manual to launch agent: 

```
pkill -f "uvicorn app.main:app" || true
launchctl bootout gui/$UID/com.desktop-companion.api 2>/dev/null || true
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.desktop-companion.api.plist
launchctl kickstart -k gui/$UID/com.desktop-companion.api
```

## Development notes

If you want to run the test suite:

```bash
pytest
```
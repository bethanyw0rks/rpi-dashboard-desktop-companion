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

On Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

If you are new to this, the virtual environment is created in a folder named `.venv` inside the project. You will usually activate it each time you work on the project.

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

If your frontend or another service will call this API from a browser, set a comma-separated list of allowed origins before starting the server:

On macOS or Linux:

```bash
export CORS_ALLOWED_ORIGINS="https://dashboard.example.com,https://admin.example.com"
```

On Windows:

```powershell
$env:CORS_ALLOWED_ORIGINS="https://dashboard.example.com,https://admin.example.com"
```

If you leave this unset, the API will not add CORS headers.

### 5. Run the API

Start the local API server with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8010
```

This will start the app so it can be reached from other devices on your local network.

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

## Useful tips

- If you close the terminal where the server is running, the API will stop.
- To keep it running after a reboot, you may want to set it up as a background service or launch agent, depending on your operating system.
- If you are using a Raspberry Pi or another device on the same network, you can access the API using the desktop computer’s local IP address and port `8010`.

## macOS launch agent (optional)

If you are using a Mac and want the companion app to start automatically after a reboot, you can install a launch agent.

### 1. Create the plist file

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
      <string>/Users/your-username/path/to/desktop-companion-rpi-dashboard/.venv/bin/python</string>
      <string>-m</string>
      <string>uvicorn</string>
      <string>app.main:app</string>
      <string>--host</string>
      <string>0.0.0.0</string>
      <string>--port</string>
      <string>8010</string>
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

### 2. Load the launch agent

Run:

```bash
launchctl load ~/Library/LaunchAgents/com.desktop-companion.api.plist
```

### 3. Verify it

You can check whether the service is loaded with:

```bash
launchctl list | grep desktop-companion
```

And test the API with:

```bash
curl http://127.0.0.1:8010/health
```

If you want the service to start on boot automatically, the `RunAtLoad` setting handles that for you.

## Development notes

If you want to run the test suite:

```bash
pytest
```

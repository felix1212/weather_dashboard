# Weather Dashboard for Waveshare 7.3" E-Ink Display

This Python-based weather dashboard fetches weather data from Hong Kong Observatory and OpenWeatherMap APIs, processes it, and renders a graphical display on a Waveshare 7.3-inch e-ink screen.

## Features

- Real-time weather data from:
  - Hong Kong Observatory (HKO)
  - OpenWeatherMap
- Displays:
  - Current temperature and humidity
  - Wind speed and direction
  - Max/min/feels-like temperature
  - Sunrise and sunset times
  - Latest warning summaries and details
  - 7-day weather forecast
- Chinese font rendering
- Update data at a configurable refresh interval
- Direct output to e-ink or preview in DEV mode

## Project Structure

```
.
├── main.py                   # Main execution script
├── settings.ini             # Configuration file
├── static/
│   ├── fonts/               # TTF font files (English & Chinese)
│   └── icon/
│       ├── large/           # Large weather icons (e.g., 50.bmp)
│       └── small/           # Small icons (sunset, wind, etc.)
```

## Prerequisites

- Python 3.8+
- Dependencies:
  - `Pillow`
  - `requests`
  - `waveshare_epd` (for PRD mode with e-ink display)

Install them via:

```bash
pip install -r requirements.txt
```

> **Note**: `waveshare_epd` is specific to Waveshare displays and must be installed from Waveshare's Python examples or GitHub.

## Configuration

Edit `settings.ini` to customize:

- Fonts
- Language (`tc` for Traditional Chinese)
- API keys
- Refresh interval (`refresh_seconds`)
- Default location (used for temperature & humidity)

Example:
```ini
[Settings]
log_level = DEBUG
language = tc
openweathermap_apikey = your_api_key
hko_location = 沙田
refresh_seconds = 900
```

## Usage

### DEV Mode (default one to preview on screen)

```bash
python main.py --mode DEV
```

### PRD Mode (display on e-ink screen)

```bash
python main.py --mode PRD
```

## Logging

Logging is output to stdout by default and can be controlled via the `log_level` setting.

## Deployment

Two helper scripts manage running the dashboard on a device (e.g. a Raspberry Pi): `start.sh` and `update.sh`. Both hardcode the device's absolute path, so the actual scripts are excluded from git — `start.sh.example` and `update.sh.example` are checked in as templates. On each device:

```bash
cp start.sh.example start.sh
cp update.sh.example update.sh
chmod +x start.sh update.sh
```

Then edit `PROJECT_DIR` in both files to match the device's actual path to this project.

### `start.sh`

Launches the dashboard in PRD mode using the device's virtual environment:

```bash
#!/bin/bash
PROJECT_DIR="/path/to/weather_dashboard"
cd "$PROJECT_DIR"
"$PROJECT_DIR/venv/bin/python" main.py --mode PRD
```

Run it directly to start the dashboard manually:

```bash
./start.sh
```

To start it automatically on every boot, add it to the crontab:

```bash
crontab -e
```
```
@reboot /path/to/weather_dashboard/start.sh >> /path/to/weather_dashboard/crontab.log 2>&1
```

### `update.sh`

Pulls the latest code from a given branch, installs any new dependencies, and restarts the running dashboard.

```bash
./update.sh                     # update to the latest main
./update.sh <branch-name>       # update to any other branch
```

What it does, in order:

1. Fetches and checks out the given branch (defaults to `main`), then pulls the latest commit.
2. Installs any new packages from `requirements.txt` into the existing virtual environment.
3. Sends `SIGINT` to the running dashboard process (graceful e-ink shutdown), then restarts it via `start.sh`.

Check the running dashboard's log:

```bash
tail -f crontab.log
```

Check what commit is currently deployed:

```bash
git log -1 --oneline
```

![Version](https://img.shields.io/badge/version-1.3.0-green.svg)

## Change Log

- **1.0.0** – Initial working version  
- **1.1.0** – Refactored program  
- **1.2.0** – Added special weather tips data to warning information bracket; refactored to move functions into `main.py`  
- **1.2.1** – Fine-tuned fonts and layouts
- **1.2.2** - Always display specific corresponding icons for special weather situation such as Typhoons
- **1.3.0** - Redesigned dashboard layout: colour title bar and warning badges (severity-based), alert panel with warning details, and 7-day temperature range bars

## Credits

- Weather data from [Hong Kong Observatory Open Data API](https://data.weather.gov.hk/weatherAPI/doc/)
- Supplemented by [OpenWeatherMap](https://openweathermap.org/)
- Display rendering using [Pillow](https://python-pillow.org)

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

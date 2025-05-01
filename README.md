# Weather Dashboard for Waveshare 7.3" E-Ink Display

This Python-based weather dashboard fetches weather data from Hong Kong Observatory and OpenWeatherMap APIs, processes it, and renders a graphical display on a Waveshare 7.3-inch e-ink screen. It supports both development (`DEV`) and production (`PRD`) modes.

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
- Special Weather Tips (SWT) integration
- Chinese font rendering
- Configurable refresh interval
- Supports direct output to e-ink or preview in DEV mode

## Project Structure

```
.
├── main.py                   # Main execution script
├── process_warning_data.py  # Legacy warning data handler (deprecated by updated main.py logic)
├── settings.ini             # Configuration file
├── swt.json                 # Sample SWT data
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

### DEV Mode (preview on screen)

```bash
python main.py --mode DEV
```

### PRD Mode (display on e-ink screen)

```bash
python main.py --mode PRD
```

## Logging

Logging is output to stdout by default and can be controlled via the `log_level` setting.

![Version](https://img.shields.io/badge/version-1.2.1-green.svg)

## Change Log

- **1.0.0** – Initial working version  
- **1.1.0** – Refactored program  
- **1.2.0** – Added special weather tips data to warning information bracket; refactored to move functions into `main.py`  
- **1.2.1** – Fine-tuned fonts and layouts  

## Credits

- Weather data from [Hong Kong Observatory Open Data API](https://data.weather.gov.hk/weatherAPI/doc/)
- Supplemented by [OpenWeatherMap](https://openweathermap.org/)
- Display rendering using [Pillow](https://python-pillow.org)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

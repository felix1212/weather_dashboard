import configparser
import sys
import os
import time
import textwrap
import argparse
import logging
import requests
from textwrap import wrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

'''
Weather Dashboard
This application sends weather data to waveshare 7.3 inch e-ink display

Change log
1.0.0 - Initial working version
1.1.0 - Refactored program
1.2.0 - Added sepcial weather tips data to warning information bracket. Further refactor application to move required functions to main.
1.2.1 - Fine-tuned fonts and layouts
'''

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # You can adjust this later based on settings
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Constants
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
CONFIG_FILE = 'settings.ini'
FONT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts')
ICON_DIR_LARGE = './static/icon/large'
ICON_DIR_SMALL = './static/icon/small'

# Load Configuration
def load_config():
    config = configparser.ConfigParser()
    try:
        with open(CONFIG_FILE, 'r') as file:
            logger.info(f"Loading configuration from {CONFIG_FILE}…")
        config.read(CONFIG_FILE, encoding='utf-8')
        settings = {k: v for k, v in config.items('Settings')}
        settings['max_lines'] = int(settings['max_lines'])
        settings['refresh_seconds'] = int(settings['refresh_seconds'])
        logger.info("Configuration loaded successfully.")
        return settings
    except Exception as e:
        logger.exception("Config error:")
        sys.exit(1)

# Load Fonts
def load_fonts(settings):
    logger.info("Loading fonts…")
    fonts = {
        'bold': ImageFont.truetype(os.path.join(FONT_DIR, settings['bold_font']), 39),
        'normal': ImageFont.truetype(os.path.join(FONT_DIR, settings['normal_font']), 20),
        'large': ImageFont.truetype(os.path.join(FONT_DIR, settings['bold_font']), 30),
        'light': ImageFont.truetype(os.path.join(FONT_DIR, settings['light_font']), 15),
        'chinese_bold': ImageFont.truetype(os.path.join(FONT_DIR, settings['chinese_bold_font']), 14),
        'chinese_normal': ImageFont.truetype(os.path.join(FONT_DIR, settings['chinese_normal_font']), 14),
        'chinese_light': ImageFont.truetype(os.path.join(FONT_DIR, settings['chinese_light_font']), 14),
        'chinese_light_large': ImageFont.truetype(os.path.join(FONT_DIR, settings['chinese_light_font']), 17),
        'small_text': ImageFont.truetype(os.path.join(FONT_DIR, settings['normal_font']), 11),
        'top_right_value': ImageFont.truetype(os.path.join(FONT_DIR, settings['bold_font']), 20),
        'unit': ImageFont.truetype(os.path.join(FONT_DIR, settings['normal_font']), 11),
        'current_temp': ImageFont.truetype(os.path.join(FONT_DIR, settings['bold_font']), 87),
        'degree_celsius': ImageFont.truetype(os.path.join(FONT_DIR, settings['bold_font']), 40),
        'chinese_forecast': ImageFont.truetype(os.path.join(FONT_DIR, settings['chinese_bold_font']), 11),
        'forecast_text': ImageFont.truetype(os.path.join(FONT_DIR, settings['normal_font']), 11),
        'last_update': ImageFont.truetype(os.path.join(FONT_DIR, settings['chinese_normal_font']), 11)
    }
    logger.info("Fonts loaded successfully.")
    return fonts

# Fetch Data
def fetch_data(settings):
    logger.info('Fetching data from APIs…')
    data = {
        'local_forecast': get_hko('flw', settings['language']),
        'local_weather': get_hko('rhrread', settings['language']),
        'srs': get_hko('SRS', settings['language']),
        'nine_day_forecast': get_hko('fnd', settings['language']),
        'warning_summary': get_hko('warnsum', settings['language']),
        'warning_info': get_hko('warninginfo', settings['language']),
        'special_weather': get_hko('swt', settings['language']),
        'openweathermap': get_openweathermap(settings['openweathermap_apikey'], 'HongKong')
    }
    logger.info('Data fetched successfully.')
    return data

# Process Data
def process_data(raw, settings):
    logger.info('Processing data…')
    today = datetime.now().strftime("%Y-%m-%d")
    sunrise = sunset = ''
    for day in raw['srs'].get('data', []):
        if day[0] == today:
            sunrise, sunset = str(day[1]), str(day[3])

    warnsum_items, warninfo_items = process_warning_data(raw['warning_summary'], raw['warning_info'], raw['special_weather'])
    warnsum_items = warnsum_items or {'1': '沒有天氣警告'}
    warninfo_items = warninfo_items or {'1': ['沒有天氣警告']}
    logger.info('Data processed successfully.')
    return {
        'forecast_period': raw['local_forecast']['forecastPeriod'],
        'forecast_description': raw['local_forecast']['forecastDesc'] + " " + raw['local_forecast']['outlook'],
        'sunrise': sunrise,
        'sunset': sunset,
        'feels_like': round(raw['openweathermap']['main']['feels_like']),
        'wind_speed': round(raw['openweathermap']['wind']['speed'], 1),
        'wind_dir': deg_to_compass(raw['openweathermap']['wind']['deg']),
        'current_temp': next((d['value'] for d in raw['local_weather']['temperature']['data'] if d['place'] == settings['hko_location']), None),
        'current_humidity': raw['local_weather']['humidity']['data'][0]['value'],
        'current_weather_icon': raw['local_weather']['icon'][0],
        'max_temp': round(raw['openweathermap']['main']['temp_max']),
        'min_temp': round(raw['openweathermap']['main']['temp_min']),
        'seven_day_forecast': raw['nine_day_forecast'].get('weatherForecast', [])[:7],
        'warnsum_items': warnsum_items,
        'warninfo_items': warninfo_items
    }

# Draw Screen
def draw_screen(data, fonts, settings, fill_color):
    SHIFT_RIGHT = 17
    image = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), 'white')
    draw = ImageDraw.Draw(image)

    # Title
    today_title = datetime.now().strftime('%A, %B %d')
    title_w, title_h = fonts['bold'].getbbox(today_title)[2:]
    draw.text(((DISPLAY_WIDTH-title_w)/2, 18), today_title, font=fonts['bold'], fill=fill_color)

    # Current Weather
    weather_icon = Image.open(f"{ICON_DIR_LARGE}/{data['current_weather_icon']}.bmp")
    image.paste(weather_icon, (56, 54))
    draw.text((280, 68), str(data['current_temp']), font=fonts['current_temp'], fill=fill_color)
    draw.text((385, 78), '°C', font=fonts['degree_celsius'], fill=fill_color)
    draw.text((238, 174), f"{data['max_temp']}° / {data['min_temp']}°", font=fonts['normal'], fill=fill_color)
    draw.text((340, 173), "體感温度:", font=fonts['chinese_light_large'], fill=fill_color)
    draw.text((416, 170), f"{data['feels_like']}°", font=fonts['large'], fill=fill_color)

    # Sunrise/Sunset/Wind/Humidity
    static_info = [
        ('sunset.bmp', '日落', data['sunset'], (480, 70), (570, 81), 560 + SHIFT_RIGHT),
        ('sunrise.bmp', '日出', data['sunrise'], (630, 70), (720, 81), 710 + SHIFT_RIGHT),
    ]

    dynamic_info = [
        ('wind.bmp', '風速', f"{data['wind_dir']}@{data['wind_speed']}", 'm/s', (480, 145), (570, 156), 560 + SHIFT_RIGHT),
        ('humidity.bmp', '濕度', f"{data['current_humidity']}", '%', (630, 145), (720, 156), 710 + SHIFT_RIGHT)
    ]
    for icon_file, label, value, img_pos, label_pos, value_center_x in static_info:
        icon = Image.open(f"{ICON_DIR_SMALL}/{icon_file}")
        image.paste(icon, img_pos)

        # Center-align label
        label_width = draw.textlength(label, font=fonts['chinese_normal'])
        label_x = value_center_x - label_width // 2
        draw.text((label_x, label_pos[1]), label, font=fonts['chinese_normal'], fill=fill_color)

        # Center-align value
        text_width = draw.textlength(str(value), font=fonts['top_right_value'])
        draw.text((value_center_x - text_width // 2, img_pos[1] + 35), str(value), font=fonts['top_right_value'], fill=fill_color)

    for icon_file, label, value, unit, img_pos, label_pos, value_center_x in dynamic_info:
        icon = Image.open(f"{ICON_DIR_SMALL}/{icon_file}")
        image.paste(icon, img_pos)

        # Center-align label
        label_width = draw.textlength(label, font=fonts['chinese_normal'])
        label_x = value_center_x - label_width // 2
        draw.text((label_x, label_pos[1]), label, font=fonts['chinese_normal'], fill=fill_color)

        # Center-align value + unit
        value_text = str(value)
        value_bbox = draw.textbbox((0, 0), value_text, font=fonts['top_right_value'])
        unit_bbox = draw.textbbox((0, 0), unit, font=fonts['unit'])
        total_width = (value_bbox[2] - value_bbox[0]) + (unit_bbox[2] - unit_bbox[0]) + 2
        value_x = value_center_x - total_width // 2
        unit_x = value_x + (value_bbox[2] - value_bbox[0]) + 2
        value_y = img_pos[1] + 35
        unit_y = value_y + (fonts['top_right_value'].size - fonts['unit'].size)
        draw.text((value_x, value_y), value_text, font=fonts['top_right_value'], fill=fill_color)
        draw.text((unit_x, unit_y), unit, font=fonts['unit'], fill=fill_color)

    # Last update
    last_update_text = datetime.now().strftime("最後更新: %Y-%m-%d %H:%M")
    update_w = fonts['last_update'].getbbox(last_update_text)[2]
    draw.text((760 - update_w, 15), last_update_text, font=fonts['last_update'], fill=fill_color)

    # Forecast period description
    draw.text((480, 220), f"{data['forecast_period']}:", font=fonts['chinese_bold'], fill=fill_color)
    wrapped_forecast = wrap(data['forecast_description'], width=19)
    # Truncate to max_lines
    max_lines = settings['max_lines']
    truncated = len(wrapped_forecast) > max_lines
    wrapped_forecast = wrapped_forecast[:max_lines]
    # Add ellipsis if truncated
    if truncated:
        # Append ellipsis to the last line
        last_line = wrapped_forecast[-1]
        # Ensure ellipsis fits within the width
        if len(last_line) > 3:
            wrapped_warning[-1] = last_line[:-1] + '…'
        else:
            wrapped_forecast[-1] = '…'
    draw.multiline_text((480, 248), "\n".join(wrapped_forecast), font=fonts['chinese_normal'], fill=fill_color, spacing=3)

    # Warning Summary
    position_warning_items(draw, process_warning_items(data['warnsum_items']), fonts['chinese_bold'], fonts['chinese_light'], fill_color, start_x=56, y=220)

    # Warning Info
    wrapped_warning = []
    line_limit = settings['max_lines']
    line_count = 0
    truncated = False
    for line in data['warninfo_items']['1']:
        wrapped_lines = textwrap.wrap(line, width=27)
        if line_count + len(wrapped_lines) > line_limit:
            remaining = line_limit - line_count
            if remaining > 0:
                wrapped_warning.extend(wrapped_lines[:remaining])
                truncated = True
            break
        else:
            wrapped_warning.extend(wrapped_lines)
            line_count += len(wrapped_lines)
    # Add ellipsis if truncated
    if truncated and wrapped_warning:
        last_line = wrapped_warning[-1]
        if len(last_line) > 3:
            wrapped_warning[-1] = last_line[:-1] + '…'
        else:
            wrapped_warning[-1] = '…'
    draw.multiline_text((56, 248), "\n".join(wrapped_warning), font=fonts['chinese_normal'], fill=fill_color, spacing=3)

    # 7-day forecast
    BOX_WIDTH = 100
    BOX_HEIGHT = 160
    for i, day in enumerate(data['seven_day_forecast']):
        week = day['week']
        min_temp = day['forecastMintemp']['value']
        max_temp = day['forecastMaxtemp']['value']
        icon_code = day['ForecastIcon']
        day_img = Image.new('RGB', (BOX_WIDTH, BOX_HEIGHT), color='white')
        day_draw = ImageDraw.Draw(day_img)
        day_draw.text((BOX_WIDTH // 2, 5), week, fill=fill_color, anchor='ma', font=fonts['chinese_forecast'])
        icon = Image.open(f"{ICON_DIR_SMALL}/{icon_code}.bmp")
        day_img.paste(icon, (20, 30))
        temp_text = f"{max_temp}° / {min_temp}°"
        day_draw.text((BOX_WIDTH // 2, 105), temp_text, fill=fill_color, anchor='ma', font=fonts['forecast_text'])
        image.paste(day_img, (50 + i * BOX_WIDTH, 350))

    return image

# Helper funtions
def align_warnsum_items(warnsum_items, total_width=80):
    values = list(warnsum_items.values())

    if len(values) != 3:
        raise ValueError("Exactly 3 items are required.")

    left = values[0]
    center = values[1]
    right = values[2]

    # Calculate available space between them
    left_space = 0
    center_space = (total_width - len(left) - len(center) - len(right)) // 2
    right_space = total_width - len(left) - len(center) - len(right) - center_space

    # Build final aligned string
    line = f"{left}{' ' * center_space}{center}{' ' * right_space}{right}"
    return line

def process_warning_items(items):
    """Process warning items to ensure we have 1-3 properly formatted items"""
    if not items:
        return {1: 'No warnings'}
    
    # Convert to list of tuples sorted by timestamp (if available) or maintain order
    items_list = list(items.items())
    if len(items_list) > 3:
        items_list = items_list[-3:]  # Get last 3 items
    
    # Create new dictionary with numeric keys
    result = {}
    for i, (_, value) in enumerate(items_list, 1):
        result[i] = value
    
    return result

def position_warning_items(draw, items, bold_font, normal_font, fill_color, start_x=56, y=220, max_width=380):
    """Position warning items in left, center, and right positions"""
    num_items = len(items)
    
    if num_items == 1:
        # Single item - left align
        text = items[1]
        draw.text((start_x, y), text, font=bold_font, fill=fill_color)
    
    elif num_items == 2:
        # Two items - position at left and center
        left_text = items[1]
        center_text = items[2]
        # Left align first item
        draw.text((start_x, y), left_text, font=bold_font, fill=fill_color)
        # Center align second item
        center_width = draw.textlength(center_text, font=bold_font)
        center_x = start_x + (max_width - center_width) // 2
        draw.text((center_x, y), center_text, font=normal_font, fill=fill_color)
    
    elif num_items == 3:
        # Three items - position at left, center and right
        left_text = items[1]
        center_text = items[2]
        right_text = items[3]
        
        # Left align first item
        draw.text((start_x, y), left_text, font=bold_font, fill=fill_color)
        
        # Center the middle item
        center_width = draw.textlength(center_text, font=normal_font)
        center_x = start_x + (max_width - center_width) // 2
        draw.text((center_x, y), center_text, font=normal_font, fill=fill_color)
        
        # Right align last item
        right_width = draw.textlength(right_text, font=normal_font)
        right_x = start_x + max_width - right_width
        draw.text((right_x, y), right_text, font=normal_font, fill=fill_color)

def process_warning_data(warnsum_json, warninginfo_json, swt_json):
    # Step 1: Merge warnsum and swt entries
    combined_items = []

    # Prepare warnsum entries
    for code, val in warnsum_json.items():
        combined_items.append({
            'source': 'warnsum',
            'code': code,
            'updateTime': datetime.fromisoformat(val['updateTime'].replace(' ', '').replace('+08:00', '')),
            'data': val
        })

    # Prepare swt entries
    for idx, item in enumerate(swt_json.get('swt', [])):
        combined_items.append({
            'source': 'swt',
            'code': f"SWT_{idx}",  # Generate unique code for SWT items
            'updateTime': datetime.fromisoformat(item['updateTime'].replace(' ', '').replace('+08:00', '')),
            'data': item
        })

    # Step 2: Sort by updateTime (latest first), take latest 3
    combined_items.sort(key=lambda x: x['updateTime'], reverse=True)
    latest_items = combined_items[:3]

    # Step 3: Prepare warnsum_items
    warnsum_items = {}
    warninfo_items = {}

    details_list = warninginfo_json.get('details', [])

    for i, item in enumerate(latest_items, 1):
        if item['source'] == 'warnsum':
            code = item['code']
            val = item['data']

            # Build warnsum_items
            if code in ['WRAIN', 'WFIRE']:
                label = f"{val.get('type', '')}{val['name']}"
            elif code == 'WTCSGNL':
                label = val.get('type', '')
            else:
                label = val['name']
            warnsum_items[str(i)] = label

            # Build warninfo_items
            for detail in details_list:
                if detail.get('warningStatementCode') == code:
                    warninfo_items[str(i)] = detail.get('contents', [])
                    break
            else:
                warninfo_items[str(i)] = ["No detailed info found."]

        else:  # source == 'swt'
            warnsum_items[str(i)] = '特別天氣提示'
            desc_text = item['data'].get('desc', '')
            if desc_text:
                warninfo_items[str(i)] = [desc_text]
            else:
                warninfo_items[str(i)] = ["特別天氣提示"]

    return warnsum_items, warninfo_items

def get_hko(data_type,language):
    current_year = datetime.now().year
    if data_type == 'SRS':
        url = f"https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType={data_type}&year={current_year}&rformat=json"
    else:
        url = f"https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType={data_type}&lang={language}"
    response = requests.get(url)
    data = response.json()
    # print(data)
    if response.status_code == 200:
        return data
    else:
        raise Exception(f"Cannot get weather information: {data}")

def get_openweathermap(openweather_api_key,location):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={openweather_api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        return data
        # temperature = data["main"]["temp"]
        # condition = data["weather"][0]["description"]
        # print(f"Current temperature in {CITY}: {temperature}°C, {condition}")
    else:
        raise Exception(f"Cannot get weather information: {data}")

def deg_to_compass(deg):
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    idx = int((deg + 11.25) / 22.5) % 16
    return directions[idx]

# Main loop
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['DEV', 'PRD'], default='DEV', help='Run mode: DEV or PRD')
    args = parser.parse_args()
    mode = args.mode.upper()

    settings = load_config()
    fonts = load_fonts(settings)

    logger.info(f"Application started in {mode} mode.")

    if mode == 'PRD':
        from waveshare_epd import epd7in3e
        epd = epd7in3e.EPD()
        logger.info('Initializing e-Ink screen…')
        epd.init()
        logger.info('Clearing e-Ink screen…')
        epd.Clear()
        fill_color = epd.BLACK
    else:
        epd = None  # Not used in DEV
        fill_color = 'black'

    while True:
        try:
            logger.info('Starting refresh cycle…')
            raw_data = fetch_data(settings)
            processed_data = process_data(raw_data, settings)
            screen_image = draw_screen(processed_data, fonts, settings, fill_color)

            if mode == 'PRD':
                epd.display(epd.getbuffer(screen_image))
            else:
                screen_image.show()
            logger.info('Refresh cycle complete.')
            logger.info(f"Waiting {settings['refresh_seconds']} seconds…")
            time.sleep(settings['refresh_seconds'])

        except KeyboardInterrupt:
            logger.info("Graceful shutdown requested.")
            if mode == 'PRD' and epd:
                logger.info('Clearing e-Ink screen before exit…')
                epd.Clear()
                logger.info('Putting e-Ink screen to sleep…')
                epd.sleep()
            logger.info('Shutdown complete.')
            break

        except Exception as e:
            logger.exception("Unexpected error occurred:")
            time.sleep(60)

if __name__ == "__main__":
    main()
import configparser
import sys
import os
import time
import textwrap
import argparse
import logging
import requests
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
1.2.2 - Always display specific corresponding icons for special weather situation such as Typhoons
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
SMALL_ICON_SIZE = 56  # native assets are 65x65; scaled down a little for the new layout

# Colors - matches the epd7in3e 6-color e-ink panel's palette exactly, so the
# DEV preview (image.show()) renders identically to what the panel quantizes to.
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)

RANGE_BAR_COLOR = COLOR_YELLOW  # stands in for the mockup's orange (not in the 6-color palette)

# Keyword -> badge color for warning pills, checked in priority order (most severe first)
WARNING_BADGE_RED_KEYWORDS = ('黑色', '紅色', '十號', '九號', '八號', '海嘯', '霜凍')
WARNING_BADGE_YELLOW_KEYWORDS = ('黃色', '一號', '三號')

# Load Configuration
def load_config():
    config = configparser.ConfigParser()
    try:
        with open(CONFIG_FILE, 'r') as file:
            logger.info(f"Loading configuration from {CONFIG_FILE}...")
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
    logger.info("Loading fonts...")
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
    logger.info('Fetching data from APIs...')
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
    logger.info('Processing data...')
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
    LEFT_COL_X = 26
    LEFT_COL_WIDTH = 388
    DIVIDER_X = 430
    RIGHT_COL_X = 452
    RIGHT_COL_RIGHT = DISPLAY_WIDTH - 26  # 774
    image = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), 'white')
    draw = ImageDraw.Draw(image)

    # Title bar - colored by the most severe active warning (red > yellow > blue)
    title_bar_color = get_overall_warning_color(data['warnsum_items'])
    title_text_color = COLOR_BLACK if title_bar_color == COLOR_YELLOW else COLOR_WHITE
    draw.rectangle([0, 0, DISPLAY_WIDTH, 56], fill=title_bar_color)
    today_title = datetime.now().strftime('%A, %B %d')
    draw.text((LEFT_COL_X, 13), today_title, font=fonts['large'], fill=title_text_color)
    last_update_text = datetime.now().strftime("最後更新: %Y-%m-%d %H:%M")
    update_w = fonts['last_update'].getbbox(last_update_text)[2]
    draw.text((RIGHT_COL_RIGHT - update_w, 20), last_update_text, font=fonts['last_update'], fill=title_text_color)

    # Column divider
    draw.line([(DIVIDER_X, 74), (DIVIDER_X, 326)], fill=COLOR_BLACK, width=2)

    # Current Weather
    # Mapping of special weather warning names to icon filenames
    special_warning_map = {
        '一號戒備信號': 'T1.bmp',
        '三號強風信號': 'T3.bmp',
        '八號東北烈風或暴風信號': 'T8NE.bmp',
        '八號東南烈風或暴風信號': 'T8SE.bmp',
        '八號西南烈風或暴風信號': 'T8SW.bmp',
        '八號西北烈風或暴風信號': 'T8NW.bmp',
        '九號烈風或暴風風力增強信號': 'T9.bmp',
        '十號颶風信號': 'T10.bmp',
        '黃色暴雨警告信號': 'AmberRainstorm.bmp',
        '紅色暴雨警告信號': 'RedRainstorm.bmp',
        '黑色暴雨警告信號': 'BlackRainstorm.bmp',
    }
    # Check if any warnsum_items value matches a warning name
    warnsum_icon = None
    for value in data['warnsum_items'].values():
        if value in special_warning_map:
            warnsum_icon = special_warning_map[value]
            break
    if warnsum_icon:
        weather_icon = Image.open(f"{ICON_DIR_LARGE}/{warnsum_icon}")
    else:
        weather_icon = Image.open(f"{ICON_DIR_LARGE}/{data['current_weather_icon']}.bmp")
    # Icons are 150x150, but the alert-panel row only has 138px (74 to the divider at
    # 212) before it collides with the badges row below - scale down to fit.
    HERO_ICON_SIZE = 130
    weather_icon = weather_icon.resize((HERO_ICON_SIZE, HERO_ICON_SIZE), Image.LANCZOS)
    image.paste(weather_icon, (LEFT_COL_X, 74))

    # Vertically center the [number + info row] block as a unit within the icon's height,
    # rather than centering just the number on the icon's midpoint - that left a bigger
    # gap above the number than below the info row, since the row's own height wasn't
    # accounted for.
    ROW_GAP = 14
    temp_text = str(data['current_temp'])
    temp_bbox = draw.textbbox((0, 0), temp_text, font=fonts['current_temp'])
    temp_ink_height = temp_bbox[3] - temp_bbox[1]
    info_bbox = draw.textbbox((0, 0), "體感温度:", font=fonts['chinese_light_large'])
    info_ink_height = info_bbox[3] - info_bbox[1]
    block_height = temp_ink_height + ROW_GAP + info_ink_height
    temp_ink_top = 74 + (HERO_ICON_SIZE - block_height) / 2
    temp_y = temp_ink_top - temp_bbox[1]

    # The info row is wider than the number + degree sign (it also carries the feels-like
    # text), so left-aligning both at the same x leaves the number looking off-center.
    # Measure the info row's total width first and center the number over its span.
    INFO_ROW_X = 200
    info_row_segments = (
        (f"{data['max_temp']}°", fonts['normal'], COLOR_RED, 6),
        ("/", fonts['normal'], fill_color, 6),
        (f"{data['min_temp']}°", fonts['normal'], COLOR_BLUE, 20),
        ("體感温度:", fonts['chinese_light_large'], fill_color, 6),
        (f"{data['feels_like']}°", fonts['normal'], fill_color, 0),
    )
    info_row_width = sum(draw.textlength(text, font=font) + gap_after for text, font, _, gap_after in info_row_segments)

    temp_w = draw.textlength(temp_text, font=fonts['current_temp'])
    degree_w = draw.textlength('°C', font=fonts['degree_celsius'])
    temp_block_width = temp_w + 4 + degree_w
    temp_x = INFO_ROW_X + (info_row_width - temp_block_width) / 2
    draw.text((temp_x, temp_y), temp_text, font=fonts['current_temp'], fill=fill_color)
    draw.text((temp_x + temp_w + 4, temp_y + 10), '°C', font=fonts['degree_celsius'], fill=fill_color)

    # Cumulative x-positioning keeps this row inside the alert column regardless of
    # digit count, instead of the fixed offsets that used to overrun the divider.
    info_row_y = temp_ink_top + temp_ink_height + ROW_GAP - info_bbox[1]
    x = INFO_ROW_X
    for text, font, color, gap_after in info_row_segments:
        draw.text((x, info_row_y), text, font=font, fill=color)
        x += draw.textlength(text, font=font) + gap_after

    # Warning badges + detail (alert panel)
    warning_items = process_warning_items(data['warnsum_items'])
    draw.line([(LEFT_COL_X, 212), (LEFT_COL_X + LEFT_COL_WIDTH, 212)], fill=COLOR_BLACK, width=1)
    badges_bottom_y = draw_warning_badges(draw, warning_items, fonts['chinese_bold'], LEFT_COL_X, 224, LEFT_COL_WIDTH)

    detail_start_y = badges_bottom_y + 8
    detail_available_height = 326 - detail_start_y
    line_height = fonts['chinese_normal'].size + 6
    max_detail_lines = max(1, detail_available_height // line_height)
    wrapped_warning = wrap_and_truncate(data['warninfo_items']['1'], 27, min(settings['max_lines'], max_detail_lines))
    draw.multiline_text((LEFT_COL_X, detail_start_y), "\n".join(wrapped_warning), font=fonts['chinese_normal'], fill=fill_color, spacing=3)

    # Sunrise/Sunset/Wind/Humidity
    static_info = [
        ('sunset.bmp', '日落', data['sunset'], (RIGHT_COL_X, 82), (RIGHT_COL_X + 90, 93), RIGHT_COL_X + 80 + SHIFT_RIGHT),
        ('sunrise.bmp', '日出', data['sunrise'], (RIGHT_COL_X + 182, 82), (RIGHT_COL_X + 272, 93), RIGHT_COL_X + 262 + SHIFT_RIGHT),
    ]

    dynamic_info = [
        ('wind.bmp', '風速', f"{data['wind_dir']}@{data['wind_speed']}", 'm/s', (RIGHT_COL_X, 168), (RIGHT_COL_X + 90, 179), RIGHT_COL_X + 80 + SHIFT_RIGHT),
        ('humidity.bmp', '濕度', f"{data['current_humidity']}", '%', (RIGHT_COL_X + 182, 168), (RIGHT_COL_X + 272, 179), RIGHT_COL_X + 262 + SHIFT_RIGHT)
    ]
    for icon_file, label, value, img_pos, label_pos, value_center_x in static_info:
        icon = Image.open(f"{ICON_DIR_SMALL}/{icon_file}").resize((SMALL_ICON_SIZE, SMALL_ICON_SIZE), Image.LANCZOS)
        image.paste(icon, img_pos)

        # Center-align label
        label_width = draw.textlength(label, font=fonts['chinese_normal'])
        label_x = value_center_x - label_width // 2
        draw.text((label_x, label_pos[1]), label, font=fonts['chinese_normal'], fill=fill_color)

        # Center-align value
        text_width = draw.textlength(str(value), font=fonts['top_right_value'])
        draw.text((value_center_x - text_width // 2, img_pos[1] + 35), str(value), font=fonts['top_right_value'], fill=fill_color)

    for icon_file, label, value, unit, img_pos, label_pos, value_center_x in dynamic_info:
        icon = Image.open(f"{ICON_DIR_SMALL}/{icon_file}").resize((SMALL_ICON_SIZE, SMALL_ICON_SIZE), Image.LANCZOS)
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

    draw.line([(RIGHT_COL_X, 152), (RIGHT_COL_RIGHT, 152)], fill=COLOR_BLACK, width=1)
    draw.line([(RIGHT_COL_X, 238), (RIGHT_COL_RIGHT, 238)], fill=COLOR_BLACK, width=1)

    # Forecast period description - vertically centered as a block within its grid
    # cell (between the tiles divider and the 7-day divider), rather than pinned to top.
    FORECAST_SECTION_TOP, FORECAST_SECTION_BOTTOM = 238, 332
    LABEL_DESC_GAP = 10
    label_text = f"{data['forecast_period']}:"
    label_bbox = draw.textbbox((0, 0), label_text, font=fonts['chinese_bold'])
    label_height = label_bbox[3] - label_bbox[1]
    max_forecast_lines = max(1, (FORECAST_SECTION_BOTTOM - FORECAST_SECTION_TOP - label_height - LABEL_DESC_GAP) // line_height)
    wrapped_forecast = wrap_and_truncate([data['forecast_description']], 19, min(settings['max_lines'], max_forecast_lines))
    desc_text = "\n".join(wrapped_forecast)
    desc_bbox = draw.multiline_textbbox((0, 0), desc_text, font=fonts['chinese_normal'], spacing=3)
    desc_height = desc_bbox[3] - desc_bbox[1]
    block_top = FORECAST_SECTION_TOP + (FORECAST_SECTION_BOTTOM - FORECAST_SECTION_TOP - label_height - LABEL_DESC_GAP - desc_height) // 2

    label_y = block_top - label_bbox[1]
    draw.text((RIGHT_COL_X, label_y), label_text, font=fonts['chinese_bold'], fill=fill_color)
    desc_y = block_top + label_height + LABEL_DESC_GAP - desc_bbox[1]
    draw.multiline_text((RIGHT_COL_X, desc_y), desc_text, font=fonts['chinese_normal'], fill=fill_color, spacing=3)

    # 7-day forecast with range bars
    draw.line([(LEFT_COL_X, 332), (RIGHT_COL_RIGHT, 332)], fill=COLOR_BLACK, width=2)

    seven_day = data['seven_day_forecast']
    if seven_day:
        scale_min = min(day['forecastMintemp']['value'] for day in seven_day)
        scale_max = max(day['forecastMaxtemp']['value'] for day in seven_day)
    else:
        scale_min = scale_max = 0

    DAY_COL_WIDTH = (RIGHT_COL_RIGHT - LEFT_COL_X) / len(seven_day) if seven_day else 0
    BOX_WIDTH = int(DAY_COL_WIDTH)
    BOX_HEIGHT = 110
    BAR_WIDTH, BAR_HEIGHT = 80, 9
    for i, day in enumerate(seven_day):
        week = day['week']
        min_temp = day['forecastMintemp']['value']
        max_temp = day['forecastMaxtemp']['value']
        icon_code = day['ForecastIcon']
        day_img = Image.new('RGB', (BOX_WIDTH, BOX_HEIGHT), color='white')
        day_draw = ImageDraw.Draw(day_img)
        day_draw.text((BOX_WIDTH // 2, 1), week, fill=fill_color, anchor='ma', font=fonts['chinese_forecast'])
        icon = Image.open(f"{ICON_DIR_SMALL}/{icon_code}.bmp").resize((SMALL_ICON_SIZE, SMALL_ICON_SIZE), Image.LANCZOS)
        day_img.paste(icon, ((BOX_WIDTH - icon.width) // 2, 20))
        bar_x = (BOX_WIDTH - BAR_WIDTH) // 2
        draw_range_bar(day_draw, bar_x, 82, BAR_WIDTH, BAR_HEIGHT, min_temp, max_temp, scale_min, scale_max)
        max_str, min_str = f"{max_temp}°", f" {min_temp}°"
        max_tw = day_draw.textlength(max_str, font=fonts['forecast_text'])
        min_tw = day_draw.textlength(min_str, font=fonts['forecast_text'])
        temp_x = (BOX_WIDTH - max_tw - min_tw) // 2
        day_draw.text((temp_x, 95), max_str, fill=COLOR_RED, font=fonts['forecast_text'])
        day_draw.text((temp_x + max_tw, 95), min_str, fill=COLOR_BLUE, font=fonts['forecast_text'])
        image.paste(day_img, (LEFT_COL_X + round(i * DAY_COL_WIDTH), 340))

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

def wrap_and_truncate(lines, wrap_width, max_lines):
    """Wrap text lines and cap to max_lines, adding an ellipsis to a truncated last line."""
    wrapped = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=wrap_width))
    if len(wrapped) > max_lines:
        wrapped = wrapped[:max_lines]
        last_line = wrapped[-1]
        threshold = wrap_width - 3  # leave space for ellipsis
        if len(last_line) >= threshold:
            wrapped[-1] = last_line[:threshold] + '…'
    return wrapped

def get_badge_color(label):
    """Map a warning label to a badge color by severity keyword."""
    if any(keyword in label for keyword in WARNING_BADGE_RED_KEYWORDS):
        return COLOR_RED
    if any(keyword in label for keyword in WARNING_BADGE_YELLOW_KEYWORDS):
        return COLOR_YELLOW
    return COLOR_BLUE

def get_overall_warning_color(warnsum_items):
    """Title bar color: red if any warning is red, else yellow if any is yellow, else blue."""
    colors = [get_badge_color(label) for label in warnsum_items.values()]
    if COLOR_RED in colors:
        return COLOR_RED
    if COLOR_YELLOW in colors:
        return COLOR_YELLOW
    return COLOR_BLUE

def draw_pill_badge(draw, x, y, text, font, bg_color, pad_x=10, pad_y=4):
    """Draw a single rounded pill badge and return its (width, height)."""
    # Black text on yellow for contrast (matches HKO's own warning color convention); white elsewhere.
    text_color = COLOR_BLACK if bg_color == COLOR_YELLOW else COLOR_WHITE
    bbox = draw.textbbox((0, 0), text, font=font)
    width = (bbox[2] - bbox[0]) + pad_x * 2
    height = (bbox[3] - bbox[1]) + pad_y * 2
    draw.rounded_rectangle([x, y, x + width, y + height], radius=height // 2, fill=bg_color)
    draw.text((x + pad_x - bbox[0], y + pad_y - bbox[1]), text, font=font, fill=text_color)
    return width, height

def draw_warning_badges(draw, items, font, start_x, start_y, max_width, gap=6, line_gap=6):
    """Draw warning items as colored pill badges, wrapping to a new row if needed. Returns bottom y."""
    x, y, row_height = start_x, start_y, 0
    for key in sorted(items.keys()):
        text = items[key]
        bbox = draw.textbbox((0, 0), text, font=font)
        badge_width = (bbox[2] - bbox[0]) + 20
        if x != start_x and x + badge_width > start_x + max_width:
            x = start_x
            y += row_height + line_gap
            row_height = 0
        badge_w, badge_h = draw_pill_badge(draw, x, y, text, font, get_badge_color(text))
        x += badge_w + gap
        row_height = max(row_height, badge_h)
    return y + row_height

def draw_range_bar(draw, x, y, width, height, day_min, day_max, scale_min, scale_max):
    """Draw a min-max range bar track with a filled segment scaled to (scale_min, scale_max)."""
    draw.rounded_rectangle([x, y, x + width, y + height], radius=height // 2, outline=COLOR_BLACK, width=1, fill=COLOR_WHITE)
    span = max(scale_max - scale_min, 1)
    seg_left = x + 1 + (day_min - scale_min) / span * (width - 2)
    seg_right = x + 1 + (day_max - scale_min) / span * (width - 2)
    if seg_right - seg_left < 3:
        mid = (seg_left + seg_right) / 2
        seg_left, seg_right = mid - 1.5, mid + 1.5
    draw.rounded_rectangle([seg_left, y + 1, seg_right, y + height - 1], radius=(height - 2) // 2, fill=RANGE_BAR_COLOR)

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
        logger.info('Initializing e-Ink screen...')
        epd.init()
        logger.info('Clearing e-Ink screen...')
        epd.Clear()
        fill_color = epd.BLACK
    else:
        epd = None  # Not used in DEV
        fill_color = 'black'

    while True:
        try:
            logger.info('Starting refresh cycle...')
            raw_data = fetch_data(settings)
            processed_data = process_data(raw_data, settings)
            screen_image = draw_screen(processed_data, fonts, settings, fill_color)

            if mode == 'PRD':
                epd.display(epd.getbuffer(screen_image))
            else:
                screen_image.show()
            logger.info('Refresh cycle complete.')
            logger.info(f"Waiting {settings['refresh_seconds']} seconds...")
            time.sleep(settings['refresh_seconds'])

        except KeyboardInterrupt:
            logger.info("Graceful shutdown requested.")
            if mode == 'PRD' and epd:
                logger.info('Clearing e-Ink screen before exit...')
                epd.Clear()
                logger.info('Putting e-Ink screen to sleep...')
                epd.sleep()
            logger.info('Shutdown complete.')
            break

        except Exception as e:
            logger.exception("Unexpected error occurred:")
            time.sleep(60)

if __name__ == "__main__":
    main()
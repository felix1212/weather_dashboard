import configparser
import sys
import os
import textwrap
import time
# from dateutil.parser import parse
from datetime import datetime
from myutil import *
from waveshare_epd import epd7in3e
from PIL import Image,ImageDraw,ImageFont

# Verify and retrieve config
config_file = 'settings.ini'
try:
    with open(config_file, 'r') as file:
        print(f"Loading configuration from {config_file}...")
except FileNotFoundError as e:
    print(f"Config error: {e}")
    sys.exit(0)
try:
    config = configparser.ConfigParser()
    config.read('settings.ini', encoding='utf-8')
    config.read('settings.ini')
    log_level = config.get("Settings", "log_level")
    lang = config.get("Settings", "language")
    openweathermap_apikey = config.get("Settings","openweathermap_apikey")
    hko_location = config.get("Settings","hko_location")
    bold_font = config.get("Settings", "bold_font")
    normal_font = config.get("Settings", "normal_font")
    light_font = config.get("Settings", "light_font")
    chinese_bold_font = config.get("Settings", "chinese_bold_font")
    chinese_normal_font = config.get("Settings", "chinese_normal_font")
    chinese_light_font = config.get("Settings", "chinese_light_font")
    max_lines = int(config.get("Settings", "max_lines"))
    refresh_seconds = int(config.get("Settings", "refresh_seconds"))
except Exception as e:
    print(f"Config error: {e}")
    sys.exit(0)

## Create logger
logger = create_logger(log_level,__name__)

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

def position_warning_items(draw, items, font, start_x=56, y=220, max_width=380):
    """Position warning items in left, center, and right positions"""
    num_items = len(items)
    
    if num_items == 1:
        # Single item - left align
        text = items[1]
        draw.text((start_x, y), text, font=font, fill='BLACK')
    
    elif num_items == 2:
        # Two items - position at left and center
        left_text = items[1]
        center_text = items[2]
        # Left align first item
        draw.text((start_x, y), left_text, font=font, fill='BLACK')
        # Center align second item
        center_width = draw.textlength(center_text, font=font)
        center_x = start_x + (max_width - center_width) // 2
        draw.text((center_x, y), center_text, font=font, fill='BLACK')
    
    elif num_items == 3:
        # Three items - position at left, center and right
        left_text = items[1]
        center_text = items[2]
        right_text = items[3]
        
        # Left align first item
        draw.text((start_x, y), left_text, font=font, fill='BLACK')
        
        # Center the middle item
        center_width = draw.textlength(center_text, font=font)
        center_x = start_x + (max_width - center_width) // 2
        draw.text((center_x, y), center_text, font=font, fill='BLACK')
        
        # Right align last item
        right_width = draw.textlength(right_text, font=font)
        right_x = start_x + max_width - right_width
        draw.text((right_x, y), right_text, font=font, fill='BLACK')

if __name__ == "__main__":
    logger.info("Application started")

    # Create Screen Object
    epd = epd7in3e.EPD()
    logger.info('Initalizing e-lnk screen...')
    epd.init()
    logger.info('Clearing e-lnk screen...')
    epd.Clear()

    while True:
        try:
            # Date format for Title
            today_yyyy_mm_dd = datetime.now().strftime("%Y-%m-%d")
            '''
            Get Raw Data
            '''
            logger.info('Retriving data from HKO...')  
            raw_local_forecast = get_hko('flw',lang)
            raw_local_weather = get_hko('rhrread',lang)
            raw_SRS = get_hko('SRS',lang)
            raw_nine_day_forecast = get_hko('fnd',lang)
            raw_warning_summary = get_hko('warnsum',lang)
            raw_warning_info = get_hko('warninginfo',lang)
            logger.info('Retriving data from OpenWeatherMap...') 
            raw_openweathermap = get_openweathermap(openweathermap_apikey,'HongKong')
            last_update_text = datetime.now().strftime("最後更新: %Y-%m-%d %H:%M")

            '''
            Process data
            '''
            # Forecast - HKO
            forecast_period = raw_local_forecast['forecastPeriod']
            forecast_description = raw_local_forecast['forecastDesc'] + " " + raw_local_forecast['outlook']
            
            # Sunrise / Sunset - HKO
            for each_day in raw_SRS.get("data", []):
                if each_day[0] == today_yyyy_mm_dd: # Use title day to retrive corresponding data
                    sunrise = str(each_day[1])
                    sunset = str(each_day[3])
            
            # Feels like - Openweather
            feels_like = round(raw_openweathermap["main"]['feels_like'])

            # Wind information - Openweather
            wind_speed = round(raw_openweathermap["wind"]['speed'],1)
            wind_dir = deg_to_compass(raw_openweathermap["wind"]['deg'])
            
            # Temperature - HKO
            for each_data in raw_local_weather['temperature']['data']:
                if each_data['place'] == '沙田':
                    current_temperature = each_data['value']
            
            # Humidity - HKO
            current_humidity = raw_local_weather['humidity']['data'][0]['value']

            # Weather Icon - HKO
            current_weather_icon = raw_local_weather['icon'][0]
            
            # Max and Min temperature - Openweather
            max_temp = round(raw_openweathermap['main']['temp_max'])
            min_temp = round(raw_openweathermap['main']['temp_min'])
            
            # 7-Day Forecast - HKO
            seven_day_forecast = raw_nine_day_forecast.get('weatherForecast', [])[:7]

            # Warning Summary & Info
            warnsum_items, warninfo_items = process_warning_data(raw_warning_summary, raw_warning_info)
            if not warnsum_items:
                warnsum_items = {'1': '沒有天氣警告'}
            if not warninfo_items:
                warninfo_items = {'1': ['沒有天氣警告']}

            logger.debug(f'forecast_period: {forecast_period}')
            logger.debug(f'forecast_description: {forecast_description}')
            logger.debug(f'sunrise: {sunrise}')
            logger.debug(f'sunset: {sunset}')
            logger.debug(f'feels_like: {feels_like}')
            logger.debug(f'wind_speed: {wind_speed}')
            logger.debug(f'wind_dir: {wind_dir}')
            logger.debug(f'temperature: {current_temperature}')
            logger.debug(f'current weather icon: {current_weather_icon}')
            logger.debug(f'humidity: {current_humidity}')
            logger.debug(f'max_temp: {max_temp}')
            logger.debug(f'min_temp: {min_temp}')
            logger.debug(f'seven_day_forecast: {seven_day_forecast}')
            logger.debug(f'warning summary: {warnsum_items}')
            logger.debug(f'warning info: {warninfo_items}')

            '''
            Send to display
            '''
            logger.debug('Drawing Title...')
            title_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', bold_font), 35)
            # Create base image
            image = Image.new('RGB',(800,480),'white')
            draw = ImageDraw.Draw(image)
            # Create title
            today_title = datetime.now().strftime('%A, %B %d')
            # Calculate text width and height using getbbox
            bbox = title_font.getbbox(today_title)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # Center the text horizontally, position near top
            title_x = (800 - text_width) / 2
            title_y = 20  # top padding
            # Draw the title text
            draw.text((title_x, title_y), today_title, font=title_font, fill='black')

            # Add Current Weather Data
            logger.debug('Drawing current weather...')
            current_temperature_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', bold_font), 87)
            small_text_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', normal_font), 15)
            # chinese_small_text_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', chinese_light_font), 14)
            chinese_small_text_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', chinese_normal_font), 14)
            degree_celsius_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', bold_font), 40)
            current_weather_image = Image.open(f'./static/icon/large/{current_weather_icon}.bmp')
            image.paste(current_weather_image, (56, 54))
            draw.text((230,62), f'{current_temperature}', font = current_temperature_font, fill = epd.BLACK) #epd.BLACK)
            draw.text((335,72), '°C', font = degree_celsius_font, fill = epd.BLACK) #epd.BLACK)
            draw.text((238,170), f'{max_temp}° / {min_temp}°', font = small_text_font, fill = epd.BLACK) #epd.BLACK)
            draw.text((340,167), f'體感温度: ', font = chinese_small_text_font, fill = epd.BLACK) #epd.BLACK)
            draw.text((405,170), f'{feels_like}°', font = small_text_font, fill = epd.BLACK) #epd.BLACK)

            # Add Top Right sub information
            logger.debug('Drawing sub-information...')
            unit_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', normal_font), 11)
            top_right_value_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', bold_font), 20)
            # last_update_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', chinese_light_font), 11)
            last_update_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', chinese_normal_font), 11)
            sunset_image = Image.open(f'./static/icon/small/sunset.bmp')
            image.paste(sunset_image, (480, 70))
            draw.text((570,81), f'日落', font = chinese_small_text_font, fill = epd.BLACK) #epd.BLACK)
            draw.text((710,105), f'{sunset}', font = top_right_value_font, fill = epd.BLACK) #epd.BLACK)

            sunrise_image = Image.open(f'./static/icon/small/sunrise.bmp')
            image.paste(sunrise_image, (630, 70))
            draw.text((720,81), f'日出', font = chinese_small_text_font, fill = epd.BLACK) #epd.BLACK)
            draw.text((560,105), f'{sunrise}', font = top_right_value_font, fill = epd.BLACK) #epd.BLACK)

            wind_image = Image.open(f'./static/icon/small/wind.bmp')
            image.paste(wind_image, (480, 145))
            draw.text((570,156), f'風速', font = chinese_small_text_font, fill = epd.BLACK) #epd.BLACK)
            wind_right_x = 607
            wind_y = 180

            wind_text = f'{wind_dir}@{wind_speed}'
            unit_text = 'm/s' 
            wind_bbox = draw.textbbox((0, 0), wind_text, font=top_right_value_font) # Measure both parts
            wind_width = wind_bbox[2] - wind_bbox[0]
            unit_bbox = draw.textbbox((0, 0), unit_text, font=unit_font)
            unit_width = unit_bbox[2] - unit_bbox[0]
            unit_height = unit_bbox[3] - unit_bbox[1] # Calculate starting x position to align to wind_right_x
            wind_x = wind_right_x - (wind_width + unit_width + 0)  
            unit_x = wind_x + wind_width + 2 # small padding between number and unit
            unit_y = wind_y + (top_right_value_font.size - unit_font.size)
            draw.text((wind_x, wind_y), wind_text, font=top_right_value_font, fill='BLACK') # Draw wind value and unit
            draw.text((unit_x, unit_y), unit_text, font=unit_font, fill='BLACK')

            humidity_image = Image.open(f'./static/icon/small/humidity.bmp')
            image.paste(humidity_image, (630, 145))
            draw.text((720,156), f'濕度', font = chinese_small_text_font, fill = epd.BLACK) #epd.BLACK)
            humidity_right_x = 757
            humidity_y = 180
            humidity_text = f'{current_humidity}'
            unit_text = '%'
            humidity_bbox = draw.textbbox((0, 0), humidity_text, font=top_right_value_font) # Measure text widths
            humidity_width = humidity_bbox[2] - humidity_bbox[0]
            percent_bbox = draw.textbbox((0, 0), unit_text, font=unit_font)
            percent_width = percent_bbox[2] - percent_bbox[0]
            humidity_x = humidity_right_x - (humidity_width + percent_width + 0) # Calculate positions
            percent_x = humidity_x + humidity_width + 2
            percent_y = humidity_y + (top_right_value_font.size - unit_font.size)  # align bottom of % with number
            draw.text((humidity_x, humidity_y), humidity_text, font=top_right_value_font, fill='BLACK') # Draw humidity value and % sign
            draw.text((percent_x, percent_y), unit_text, font=unit_font, fill='BLACK')

            bbox = draw.textbbox((0, 0), last_update_text, font=last_update_font)
            text_width = bbox[2] - bbox[0]
            x = 760 - text_width
            y = 15
            draw.text((x, y), last_update_text, font=last_update_font, fill='black')

            # Add Weather forecast Period
            logger.debug('Drawing weather forecast...')
            chinese_normal_text_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', chinese_normal_font), 14)
            chinese_bold_text_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', chinese_bold_font), 14)
            draw.text((480,220), f'{forecast_period}:', font = chinese_bold_text_font, fill = epd.BLACK) #epd.BLACK)
            forecast_period_lines = []
            for line in forecast_description.split("\n"):
                wrapped = textwrap.wrap(line, width=19)  # Adjust width to control wrapping
                forecast_period_lines.extend(wrapped)
            forecast_period_lines_is_truncated = len(forecast_period_lines) > max_lines
            forecast_period_lines = forecast_period_lines[:max_lines]
            if forecast_period_lines_is_truncated:
                forecast_period_lines[-1] += "…" # Add ellipsis if lines exceed max lines
            forecast_period_wrapped_text = "\n".join(forecast_period_lines) # Join with newline to make it multiline
            draw.multiline_text((480, 248), forecast_period_wrapped_text, font = chinese_normal_text_font, fill = epd.BLACK, spacing=3)

            # Add Warning Summary
            logger.debug('Drawing warning summary...')
            warnsum_items = process_warning_items(warnsum_items) # Process warning items to ensure proper format
            position_warning_items(draw, warnsum_items, chinese_bold_text_font) # Display warning summary

            # Add Warning info
            logger.debug('Drawing warning info...')
            warninfo_items_lines = []
            for line in warninfo_items['1']:
                warninfo_items_lines.extend(textwrap.wrap(line, width=27))  # Adjust width to control wrapping
            warninfo_items_lines_is_truncated = len(warninfo_items_lines) > max_lines
            warninfo_items_lines = warninfo_items_lines[:max_lines]
            if warninfo_items_lines_is_truncated:
                warninfo_items_lines[-1] += "…" # Add ellipsis if lines exceed max lines
            warninfo_warpped_text = "\n".join(warninfo_items_lines)  # Join with newline to make it multiline
            draw.multiline_text((56, 248), warninfo_warpped_text, font = chinese_normal_text_font, fill = epd.BLACK, spacing=3)

            # Create and Display 7-Day forecast images
            logger.debug('Drawing 7-Day forecast...')
            chinese_forecast_text_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', chinese_bold_font), 11)
            forecast_text_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/fonts', normal_font), 11)
            BOX_WIDTH = 100
            BOX_HEIGHT = 160
            for i, day in enumerate(seven_day_forecast):
                week = day["week"]
                min_temp = day["forecastMintemp"]["value"]
                max_temp = day["forecastMaxtemp"]["value"]
                icon_code = day["ForecastIcon"]
                day_img = Image.new("RGB", (BOX_WIDTH, BOX_HEIGHT), color="white")
                day_draw = ImageDraw.Draw(day_img)
                day_draw.text((BOX_WIDTH // 2, 5), week, fill="black", anchor="ma", font=chinese_forecast_text_font)
                icon_file = f"./static/icon/small/{icon_code}.bmp"
                icon_img = Image.open(icon_file)
                day_img.paste(icon_img, (20, 30))
                temp_text = f"{max_temp}° / {min_temp}°"
                day_draw.text((BOX_WIDTH // 2, 105), temp_text, fill="black", anchor="ma", font=forecast_text_font)
                # Paste this day block into the final image
                image.paste(day_img, (50 + i * BOX_WIDTH, 350))

            # Send to e-Ink / screen
            epd.display(epd.getbuffer(image))
            # image.show()

            # Pause for refresh
            logger.info(f'Pause for {int(refresh_seconds / 60)} mins to refresh, or use Ctrl+C to quit')
            time.sleep(refresh_seconds)

        except KeyboardInterrupt:
            logger.info(f'Gracefully exit by CTRL-C')
            logger.debug(f'Clearing e-Ink screen before exiting...')
            epd.Clear()
            logger.debug(f'Putting e-Ink screen to sleep before exiting...')
            epd.sleep()
            logger.debug(f'epdconfig.module_exit(cleanup=True)...')
            epd7in3e.epdconfig.module_exit(cleanup=True)
            break




                

            


            

            ## Re-do after refresh period
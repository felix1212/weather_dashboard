import requests

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

# if __name__ == "__main__":
#     api_key = input("Enter your OpenWeatherMap API key: ").strip()
#     location = input("Enter location (e.g. city name): ").strip()

#     try:
#         data = get_openweathermap(api_key, location)
#         print(f"\nThe current temperature in {location} is {data["main"]["temp"]}°C.")
#         print(f"Feels like: {data["main"]['feels_like']}")
#         print(f"wind speed: {data["wind"]['speed']} meters per second (m/s)")
#         direction = deg_to_compass(data["wind"]['deg'])
#         print(f"wind direction: {direction}")
#     except Exception as e:
#         print(f"\nError: {e}")
    
import requests
from datetime import datetime

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

if __name__ == "__main__":
    print("start")
    local_forecast = get_hko('flw','tc')
    local_weather = get_hko('rhrread','tc')
    nine_day_data = get_hko('fnd','tc')
    special_weather_summary = get_hko('swt','tc')

    print('本港地區天氣預報')
    print(local_forecast['generalSituation'])

    print('本港地區天氣報告')
    for each_day_weather in local_weather['temperature']['data']:
        print(each_day_weather)

    print('九天天氣預報')
    print(nine_day_data['generalSituation'])
    for each_day_forecast in nine_day_data['weatherForecast']:
        print(each_day_forecast['forecastDate'])
        print(each_day_forecast['forecastWind'])
        print(each_day_forecast['forecastWeather'])
        print(each_day_forecast['forecastMaxtemp'])
        print(each_day_forecast['forecastMintemp'])
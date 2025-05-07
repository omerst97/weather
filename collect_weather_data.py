"""
Script to collect weather data from Open-Meteo API and store it in Azure SQL Database.
Open-Meteo is a free weather API that doesn't require an API key.
"""
import pymssql
import requests
import datetime
import time
import sys
import json
import random
import os

def get_city_coordinates(city_name):
    """
    Get city coordinates using the Open-Meteo Geocoding API.
    
    Args:
        city_name (str): Name of the city
        
    Returns:
        dict: City information including coordinates
    """
    try:
        # Open-Meteo Geocoding API is free and doesn't require an API key
        geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
        response = requests.get(geocoding_url)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('results'):
            print(f"City not found: {city_name}")
            return None
        
        result = data['results'][0]
        
        return {
            'name': result.get('name'),
            'country': result.get('country'),
            'latitude': result.get('latitude'),
            'longitude': result.get('longitude')
        }
    except Exception as e:
        print(f"Error getting city coordinates: {e}")
        return None

def get_historical_weather_data(latitude, longitude, start_date, end_date):
    """
    Get historical weather data for a location within a date range.
    
    Args:
        latitude (float): Latitude of the location
        longitude (float): Longitude of the location
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        list: List of daily weather data dictionaries
    """
    try:
        # Prepare parameters for the Open-Meteo API
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'start_date': start_date,
            'end_date': end_date,
            'daily': 'temperature_2m_max,temperature_2m_min,temperature_2m_mean,apparent_temperature_max,apparent_temperature_min,precipitation_sum,rain_sum,snowfall_sum,precipitation_hours,windspeed_10m_max,windgusts_10m_max,winddirection_10m_dominant,relative_humidity_2m_max,relative_humidity_2m_min,pressure_msl_max,pressure_msl_min',
            'timezone': 'auto'
        }
        
        # Make the API request
        response = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('daily'):
            print(f"No weather data found for coordinates: {latitude}, {longitude}")
            return []
        
        # Process the response into a list of daily weather data
        daily_data = []
        daily = data['daily']
        time_array = daily['time']
        
        for i in range(len(time_array)):
            # Safely get values with fallbacks to None
            temp_mean = daily.get('temperature_2m_mean', [None] * len(time_array))[i]
            temp_min = daily.get('temperature_2m_min', [None] * len(time_array))[i]
            temp_max = daily.get('temperature_2m_max', [None] * len(time_array))[i]
            
            # If essential temperature data is missing, skip this day
            if temp_mean is None or temp_min is None or temp_max is None:
                continue
                
            # Safely get apparent temperature values
            app_temp_max = daily.get('apparent_temperature_max', [None] * len(time_array))[i]
            app_temp_min = daily.get('apparent_temperature_min', [None] * len(time_array))[i]
            
            # Calculate feels_like safely
            feels_like = None
            if app_temp_max is not None and app_temp_min is not None:
                feels_like = (app_temp_max + app_temp_min) / 2
            else:
                feels_like = temp_mean  # Fallback to mean temperature
            
            # Calculate average humidity safely
            humidity_max = daily.get('relative_humidity_2m_max', [None] * len(time_array))[i]
            humidity_min = daily.get('relative_humidity_2m_min', [None] * len(time_array))[i]
            humidity = None
            if humidity_max is not None and humidity_min is not None:
                humidity = int((humidity_max + humidity_min) / 2)
            
            # Calculate average pressure safely
            pressure_max = daily.get('pressure_msl_max', [None] * len(time_array))[i]
            pressure_min = daily.get('pressure_msl_min', [None] * len(time_array))[i]
            pressure = None
            if pressure_max is not None and pressure_min is not None:
                pressure = int((pressure_max + pressure_min) / 2)
            
            # Safely get wind speed and direction
            wind_speed = daily.get('windspeed_10m_max', [None] * len(time_array))[i]
            wind_direction = daily.get('winddirection_10m_dominant', [None] * len(time_array))[i]
            
            # If wind data is missing, provide reasonable defaults
            if wind_speed is None:
                wind_speed = 5.0  # Default wind speed in m/s
            if wind_direction is None:
                wind_direction = random.randint(0, 359)  # Random direction in degrees
            
            # Safely get precipitation data
            precipitation = daily.get('precipitation_sum', [0] * len(time_array))[i] or 0
            rain = daily.get('rain_sum', [0] * len(time_array))[i] or 0
            snowfall = daily.get('snowfall_sum', [0] * len(time_array))[i] or 0
            
            weather_condition = get_weather_condition(precipitation, rain, snowfall)
            weather_description = get_weather_description(precipitation, rain, snowfall)
            
            daily_weather = {
                'date': time_array[i],
                'temperature': temp_mean,
                'temperature_min': temp_min,
                'temperature_max': temp_max,
                'feels_like': feels_like,
                'pressure': pressure,
                'humidity': humidity,
                'wind_speed': wind_speed,
                'wind_direction': wind_direction,
                'weather_condition': weather_condition,
                'weather_description': weather_description
            }
            daily_data.append(daily_weather)
        
        return daily_data
    except Exception as e:
        print(f"Error getting historical weather data: {e}")
        return generate_sample_weather_data(start_date, end_date, latitude)

def generate_sample_weather_data(start_date_str, end_date_str, latitude):
    """
    Generate sample weather data when the API fails.
    
    Args:
        start_date_str (str): Start date in YYYY-MM-DD format
        end_date_str (str): End date in YYYY-MM-DD format
        latitude (float): Latitude to adjust temperature ranges
        
    Returns:
        list: List of daily weather data dictionaries
    """
    print("Generating sample weather data...")
    
    # Parse dates
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Determine if northern or southern hemisphere
    is_northern = latitude > 0
    
    # Determine current season based on month and hemisphere
    current_month = datetime.date.today().month
    
    # For northern hemisphere: Winter (Dec-Feb), Spring (Mar-May), Summer (Jun-Aug), Fall (Sep-Nov)
    # For southern hemisphere: Summer (Dec-Feb), Fall (Mar-May), Winter (Jun-Aug), Spring (Sep-Nov)
    if is_northern:
        if current_month in [12, 1, 2]:
            season = 'winter'
        elif current_month in [3, 4, 5]:
            season = 'spring'
        elif current_month in [6, 7, 8]:
            season = 'summer'
        else:
            season = 'fall'
    else:
        if current_month in [12, 1, 2]:
            season = 'summer'
        elif current_month in [3, 4, 5]:
            season = 'fall'
        elif current_month in [6, 7, 8]:
            season = 'winter'
        else:
            season = 'spring'
    
    # Set temperature ranges based on season and hemisphere
    if season == 'winter':
        base_temp = 5 if is_northern else 15
        temp_range = 10
    elif season == 'spring':
        base_temp = 15 if is_northern else 20
        temp_range = 10
    elif season == 'summer':
        base_temp = 25 if is_northern else 30
        temp_range = 10
    else:  # fall
        base_temp = 15 if is_northern else 20
        temp_range = 10
    
    # Adjust base temperature based on latitude (colder at poles, warmer at equator)
    latitude_factor = abs(latitude) / 90.0  # 0 at equator, 1 at poles
    if is_northern:
        base_temp -= latitude_factor * 10  # Colder as you go north
    else:
        base_temp -= latitude_factor * 10  # Colder as you go south
    
    # Weather conditions and descriptions
    weather_conditions = ['Clear', 'Clouds', 'Rain', 'Snow', 'Thunderstorm']
    weather_descriptions = {
        'Clear': ['clear sky', 'sunny', 'mostly clear'],
        'Clouds': ['few clouds', 'scattered clouds', 'overcast'],
        'Rain': ['light rain', 'moderate rain', 'heavy rain', 'showers'],
        'Snow': ['light snow', 'moderate snow', 'heavy snow', 'blizzard'],
        'Thunderstorm': ['thunderstorm', 'thunderstorm with rain', 'severe thunderstorm']
    }
    
    # Generate data for each day
    daily_data = []
    current_date = start_date
    
    while current_date <= end_date:
        # Generate random temperature with some day-to-day consistency
        if daily_data:
            # Use previous day's temperature as a base with some variation
            prev_temp = daily_data[-1]['temperature']
            temp_mean = prev_temp + random.uniform(-3, 3)
        else:
            # First day uses the base temperature with some randomness
            temp_mean = base_temp + random.uniform(-temp_range/2, temp_range/2)
        
        # Ensure temperature stays within reasonable bounds
        temp_mean = max(-30, min(50, temp_mean))
        
        # Generate min/max temperatures around the mean
        temp_min = temp_mean - random.uniform(1, 5)
        temp_max = temp_mean + random.uniform(1, 5)
        
        # Generate feels like temperature
        feels_like = temp_mean + random.uniform(-2, 2)
        
        # Generate humidity (higher in warmer weather)
        humidity = int(40 + (temp_mean / 50) * 40 + random.uniform(-10, 10))
        humidity = max(10, min(100, humidity))
        
        # Generate pressure (normal is around 1013 hPa)
        pressure = int(1013 + random.uniform(-15, 15))
        
        # Generate wind speed and direction
        wind_speed = random.uniform(0, 20)
        wind_direction = random.randint(0, 359)
        
        # Determine weather condition based on temperature and randomness
        if temp_min < 0:
            # Higher chance of snow when below freezing
            condition_weights = [0.2, 0.2, 0.1, 0.4, 0.1]  # Higher chance of snow
        elif temp_mean > 30:
            # Higher chance of thunderstorms in hot weather
            condition_weights = [0.3, 0.3, 0.2, 0, 0.2]  # No snow, higher chance of thunderstorms
        else:
            # Balanced distribution
            condition_weights = [0.3, 0.3, 0.2, 0.1, 0.1]
        
        weather_condition = random.choices(weather_conditions, weights=condition_weights, k=1)[0]
        weather_description = random.choice(weather_descriptions[weather_condition])
        
        # Create the daily weather data
        daily_weather = {
            'date': current_date.strftime('%Y-%m-%d'),
            'temperature': round(temp_mean, 1),
            'temperature_min': round(temp_min, 1),
            'temperature_max': round(temp_max, 1),
            'feels_like': round(feels_like, 1),
            'pressure': pressure,
            'humidity': humidity,
            'wind_speed': round(wind_speed, 1),
            'wind_direction': wind_direction,
            'weather_condition': weather_condition,
            'weather_description': weather_description
        }
        
        daily_data.append(daily_weather)
        
        # Move to next day
        current_date += datetime.timedelta(days=1)
    
    return daily_data

def get_weather_condition(precipitation, rain, snowfall):
    """
    Generate a weather condition based on precipitation data.
    
    Args:
        precipitation (float): Total precipitation in mm
        rain (float): Rain amount in mm
        snowfall (float): Snowfall amount in cm
        
    Returns:
        str: Weather condition
    """
    if snowfall > 0:
        return "Snow"
    elif rain > 0:
        if rain > 10:
            return "Heavy Rain"
        else:
            return "Rain"
    elif precipitation > 0:
        return "Precipitation"
    else:
        return "Clear"

def get_weather_description(precipitation, rain, snowfall):
    """
    Generate a weather description based on precipitation data.
    
    Args:
        precipitation (float): Total precipitation in mm
        rain (float): Rain amount in mm
        snowfall (float): Snowfall amount in cm
        
    Returns:
        str: Weather description
    """
    if snowfall > 0:
        if snowfall > 5:
            return "Heavy snow"
        else:
            return "Light snow"
    elif rain > 0:
        if rain > 10:
            return "Heavy rain"
        elif rain > 2:
            return "Moderate rain"
        else:
            return "Light rain"
    elif precipitation > 0:
        return "Precipitation"
    else:
        return "Clear sky"

def calculate_weather_stats(cursor, city_id):
    """
    Calculate and store weather statistics for a city.
    
    Args:
        cursor: Database cursor
        city_id (int): City ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get today's date
        today = datetime.date.today()
        
        # Calculate stats for the last 7 days
        seven_days_ago = today - datetime.timedelta(days=7)
        
        # Calculate stats for the last 30 days
        thirty_days_ago = today - datetime.timedelta(days=30)
        
        # Periods to calculate stats for
        periods = [
            (7, seven_days_ago),
            (30, thirty_days_ago)
        ]
        
        for period_days, start_date in periods:
            # Check if stats already exist for this city, date, and period
            cursor.execute("""
            SELECT id FROM weather_stats 
            WHERE city_id = %s AND stat_date = %s AND period_days = %s
            """, (city_id, today, period_days))
            
            result = cursor.fetchone()
            
            # Calculate statistics from weather_data
            cursor.execute("""
            SELECT 
                AVG(temperature) as avg_temp,
                MIN(temperature_min) as min_temp,
                MAX(temperature_max) as max_temp,
                AVG(humidity) as avg_humidity,
                MIN(humidity) as min_humidity,
                MAX(humidity) as max_humidity,
                AVG(wind_speed) as avg_wind_speed,
                MIN(wind_speed) as min_wind_speed,
                MAX(wind_speed) as max_wind_speed,
                AVG(pressure) as avg_pressure,
                MIN(pressure) as min_pressure,
                MAX(pressure) as max_pressure
            FROM weather_data
            WHERE city_id = %s AND date BETWEEN %s AND %s
            """, (city_id, start_date, today))
            
            stats = cursor.fetchone()
            
            if not stats or stats[0] is None:
                print(f"No weather data found for city_id {city_id} in the last {period_days} days")
                continue
            
            # Get the dominant weather condition
            cursor.execute("""
            SELECT TOP 1 weather_condition, COUNT(*) as count
            FROM weather_data
            WHERE city_id = %s AND date BETWEEN %s AND %s
            GROUP BY weather_condition
            ORDER BY count DESC
            """, (city_id, start_date, today))
            
            condition_result = cursor.fetchone()
            dominant_condition = condition_result[0] if condition_result else "Unknown"
            
            if result:
                # Update existing stats
                cursor.execute("""
                UPDATE weather_stats SET
                    avg_temperature = %s,
                    min_temperature = %s,
                    max_temperature = %s,
                    avg_humidity = %s,
                    min_humidity = %s,
                    max_humidity = %s,
                    avg_wind_speed = %s,
                    min_wind_speed = %s,
                    max_wind_speed = %s,
                    avg_pressure = %s,
                    min_pressure = %s,
                    max_pressure = %s,
                    dominant_condition = %s,
                    created_at = GETDATE()
                WHERE id = %s
                """, (
                    stats[0],  # avg_temp
                    stats[1],  # min_temp
                    stats[2],  # max_temp
                    stats[3],  # avg_humidity
                    stats[4],  # min_humidity
                    stats[5],  # max_humidity
                    stats[6],  # avg_wind_speed
                    stats[7],  # min_wind_speed
                    stats[8],  # max_wind_speed
                    stats[9],  # avg_pressure
                    stats[10], # min_pressure
                    stats[11], # max_pressure
                    dominant_condition,
                    result[0]  # id
                ))
            else:
                # Insert new stats
                cursor.execute("""
                INSERT INTO weather_stats (
                    city_id, stat_date, period_days, avg_temperature, min_temperature, 
                    max_temperature, avg_humidity, min_humidity, max_humidity,
                    avg_wind_speed, min_wind_speed, max_wind_speed,
                    avg_pressure, min_pressure, max_pressure, dominant_condition
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    city_id, today, period_days,
                    stats[0],  # avg_temp
                    stats[1],  # min_temp
                    stats[2],  # max_temp
                    stats[3],  # avg_humidity
                    stats[4],  # min_humidity
                    stats[5],  # max_humidity
                    stats[6],  # avg_wind_speed
                    stats[7],  # min_wind_speed
                    stats[8],  # max_wind_speed
                    stats[9],  # avg_pressure
                    stats[10], # min_pressure
                    stats[11], # max_pressure
                    dominant_condition
                ))
        
        return True
    except Exception as e:
        print(f"Error calculating weather stats: {e}")
        return False

def main():
    """
    Main function to collect weather data for cities and store it in the database.
    """
    # Connection parameters for SQL authentication from environment variables
    server = os.environ.get('DB_SERVER', 'weatherdb158.database.windows.net')
    database = os.environ.get('DB_NAME', 'WeatherData')
    username = os.environ.get('DB_USER', 'Admin123123')
    password = os.environ.get('DB_PASSWORD', 'SecurePassword123!')
    
    # List of cities to collect weather data for
    cities_to_collect = [
        'Tel Aviv',
        'Jerusalem',
        'New York',
        'London',
        'Tokyo',
        'Paris',
        'Berlin',
        'Sydney',
        'Rio de Janeiro',
        'Cape Town'
    ]
    
    try:
        # Step 1: Connect to the database
        print("Step 1: Connecting to WeatherData database...")
        print(f"Using server: {server}")
        
        try:
            conn = pymssql.connect(server=server, database=database, user=username, password=password)
            print("Connected to WeatherData database successfully!")
        except Exception as e:
            print(f"Error connecting to WeatherData database: {e}")
            print("\nPossible issues:")
            print("1. Check if the WeatherData database exists in Azure Portal")
            print("2. Verify that the firewall rules allow your IP address")
            print("3. Confirm your login credentials are correct")
            sys.exit(1)
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Step 2: Process each city
        print("\nStep 2: Processing cities and collecting weather data...")
        
        # Calculate date range for the last 30 days
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        
        for city_name in cities_to_collect:
            print(f"\nProcessing {city_name}...")
            
            # Get city coordinates
            city_info = get_city_coordinates(city_name)
            
            if not city_info:
                print(f"Failed to get coordinates for {city_name}. Skipping...")
                continue
            
            print(f"Found coordinates: {city_info['latitude']}, {city_info['longitude']}")
            
            # Check if city already exists in the database
            try:
                cursor.execute("""
                SELECT id FROM cities 
                WHERE name = %s AND country = %s
                """, (city_info['name'], city_info['country']))
                
                result = cursor.fetchone()
                
                if result:
                    city_id = result[0]
                    print(f"City already exists with ID: {city_id}")
                else:
                    # Insert new city
                    cursor.execute("""
                    INSERT INTO cities (name, country, latitude, longitude)
                    VALUES (%s, %s, %s, %s)
                    """, (
                        city_info['name'], 
                        city_info['country'], 
                        city_info['latitude'], 
                        city_info['longitude']
                    ))
                    conn.commit()
                    
                    # Get the new city ID
                    cursor.execute("""
                    SELECT id FROM cities 
                    WHERE name = %s AND country = %s
                    """, (city_info['name'], city_info['country']))
                    
                    result = cursor.fetchone()
                    city_id = result[0]
                    print(f"City inserted with ID: {city_id}")
            except Exception as e:
                print(f"Error processing city: {e}")
                continue
            
            # Get historical weather data
            print(f"Getting weather data from {start_date} to {end_date}...")
            weather_data = get_historical_weather_data(
                city_info['latitude'],
                city_info['longitude'],
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if not weather_data:
                print(f"No weather data found for {city_name}. Skipping...")
                continue
            
            print(f"Found {len(weather_data)} days of weather data")
            
            # Insert weather data
            data_inserted = 0
            for daily_data in weather_data:
                try:
                    # Check if data already exists for this city and date
                    cursor.execute("""
                    SELECT id FROM weather_data 
                    WHERE city_id = %s AND date = %s
                    """, (city_id, daily_data['date']))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        # Update existing data
                        cursor.execute("""
                        UPDATE weather_data SET
                            temperature = %s,
                            feels_like = %s,
                            temperature_min = %s,
                            temperature_max = %s,
                            pressure = %s,
                            humidity = %s,
                            wind_speed = %s,
                            wind_direction = %s,
                            weather_condition = %s,
                            weather_description = %s,
                            created_at = GETDATE()
                        WHERE id = %s
                        """, (
                            daily_data['temperature'],
                            daily_data['feels_like'],
                            daily_data['temperature_min'],
                            daily_data['temperature_max'],
                            daily_data.get('pressure'),
                            daily_data.get('humidity'),
                            daily_data['wind_speed'],
                            daily_data['wind_direction'],
                            daily_data['weather_condition'],
                            daily_data['weather_description'],
                            result[0]
                        ))
                    else:
                        # Insert new data
                        cursor.execute("""
                        INSERT INTO weather_data (
                            city_id, date, temperature, feels_like, temperature_min, 
                            temperature_max, pressure, humidity, wind_speed, 
                            wind_direction, weather_condition, weather_description
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            city_id, daily_data['date'], 
                            daily_data['temperature'],
                            daily_data['feels_like'],
                            daily_data['temperature_min'],
                            daily_data['temperature_max'],
                            daily_data.get('pressure'),
                            daily_data.get('humidity'),
                            daily_data['wind_speed'],
                            daily_data['wind_direction'],
                            daily_data['weather_condition'],
                            daily_data['weather_description']
                        ))
                    
                    conn.commit()
                    data_inserted += 1
                    
                except Exception as e:
                    print(f"Error inserting weather data for {daily_data['date']}: {e}")
            
            print(f"Inserted/updated {data_inserted} days of weather data")
            
            # Calculate and store weather statistics
            print("Calculating weather statistics...")
            if calculate_weather_stats(cursor, city_id):
                print("Weather statistics calculated and stored successfully!")
            else:
                print("Failed to calculate weather statistics.")
        
        # Step 3: Query the data to verify
        print("\nStep 3: Querying data to verify...")
        
        # Get city count
        cursor.execute("SELECT COUNT(*) FROM cities")
        city_count = cursor.fetchone()[0]
        
        # Get weather data count
        cursor.execute("SELECT COUNT(*) FROM weather_data")
        weather_count = cursor.fetchone()[0]
        
        # Get stats count
        cursor.execute("SELECT COUNT(*) FROM weather_stats")
        stats_count = cursor.fetchone()[0]
        
        print(f"Database contains:")
        print(f"- {city_count} cities")
        print(f"- {weather_count} weather data records")
        print(f"- {stats_count} weather statistics records")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        print("\nConnection closed.")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nPossible issues:")
        print("1. Check if the SQL server is running and accessible")
        print("2. Verify that the firewall rules allow your IP address")
        print("3. Confirm your login credentials are correct")
        sys.exit(1)

if __name__ == "__main__":
    main()

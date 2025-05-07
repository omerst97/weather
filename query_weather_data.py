"""
Script to query and analyze weather data from Azure SQL Database.
"""
import pymssql
import sys
import datetime
import os

def main():
    """
    Main function to query and analyze weather data.
    """
    # Connection parameters for SQL authentication
    server = 'weatherdb.database.windows.net'
    database = 'WeatherData'
    username = '<your-username>'  # Replace with your actual username
    password = '<your-password>'     # Replace with your actual password
    
    try:
        # Step 1: Connect to the database
        print("Step 1: Connecting to WeatherData database...")
        
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
        
        # Step 2: Query the cities
        print("\nStep 2: Querying cities...")
        cursor.execute("""
        SELECT id, name, country, latitude, longitude
        FROM cities
        ORDER BY name
        """)
        
        cities = cursor.fetchall()
        print(f"Found {len(cities)} cities:")
        for city in cities:
            print(f"ID: {city[0]}, Name: {city[1]}, Country: {city[2]}, Coordinates: ({city[3]}, {city[4]})")
        
        # Step 3: Query weather statistics
        print("\nStep 3: Querying weather statistics...")
        cursor.execute("""
        SELECT 
            c.name as city_name,
            c.country,
            ws.period_days,
            ws.avg_temperature,
            ws.min_temperature,
            ws.max_temperature,
            ws.avg_humidity,
            ws.avg_wind_speed,
            ws.dominant_condition
        FROM weather_stats ws
        JOIN cities c ON ws.city_id = c.id
        ORDER BY c.name, ws.period_days
        """)
        
        stats = cursor.fetchall()
        print(f"Found {len(stats)} weather statistics records:")
        print("\nWeather Statistics by City:")
        print("City\t\tCountry\t\tPeriod\tAvg Temp\tMin Temp\tMax Temp\tAvg Humidity\tAvg Wind\tDominant Condition")
        print("-" * 120)
        
        for stat in stats:
            print(f"{stat[0]:<12}\t{stat[1]:<12}\t{stat[2]} days\t{stat[3]:.1f}°C\t\t{stat[4]:.1f}°C\t\t{stat[5]:.1f}°C\t\t{stat[6] or 'N/A'}%\t\t{stat[7]:.1f} m/s\t{stat[8]}")
        
        # Step 4: Find the hottest and coldest cities
        print("\nStep 4: Finding the hottest and coldest cities (last 30 days)...")
        cursor.execute("""
        SELECT 
            c.name as city_name,
            c.country,
            ws.avg_temperature
        FROM weather_stats ws
        JOIN cities c ON ws.city_id = c.id
        WHERE ws.period_days = 30
        ORDER BY ws.avg_temperature DESC
        """)
        
        temp_rankings = cursor.fetchall()
        if temp_rankings:
            hottest_city = temp_rankings[0]
            coldest_city = temp_rankings[-1]
            
            print(f"Hottest city: {hottest_city[0]}, {hottest_city[1]} with average temperature of {hottest_city[2]:.1f}°C")
            print(f"Coldest city: {coldest_city[0]}, {coldest_city[1]} with average temperature of {coldest_city[2]:.1f}°C")
        
        # Step 5: Query temperature trends for a specific city
        print("\nStep 5: Querying temperature trends for Tel Aviv...")
        cursor.execute("""
        SELECT 
            date,
            temperature,
            temperature_min,
            temperature_max,
            humidity,
            weather_condition
        FROM weather_data
        WHERE city_id = (SELECT id FROM cities WHERE name = 'Tel Aviv')
        ORDER BY date
        """)
        
        tel_aviv_data = cursor.fetchall()
        if tel_aviv_data:
            print(f"Found {len(tel_aviv_data)} days of weather data for Tel Aviv:")
            print("\nDate\t\tTemp\tMin\tMax\tHumidity\tCondition")
            print("-" * 80)
            
            for day in tel_aviv_data[:7]:  # Show only the first 7 days
                print(f"{day[0]}\t{day[1]:.1f}°C\t{day[2]:.1f}°C\t{day[3]:.1f}°C\t{day[4] or 'N/A'}%\t\t{day[5]}")
            
            if len(tel_aviv_data) > 7:
                print(f"... and {len(tel_aviv_data) - 7} more days")
        
        # Step 6: Query weather condition distribution
        print("\nStep 6: Querying weather condition distribution...")
        cursor.execute("""
        SELECT 
            weather_condition,
            COUNT(*) as count,
            COUNT(*) * 100.0 / (SELECT COUNT(*) FROM weather_data) as percentage
        FROM weather_data
        GROUP BY weather_condition
        ORDER BY count DESC
        """)
        
        conditions = cursor.fetchall()
        print(f"Weather condition distribution across all cities:")
        print("\nCondition\tCount\tPercentage")
        print("-" * 40)
        
        for condition in conditions:
            print(f"{condition[0]:<12}\t{condition[1]}\t{condition[2]:.1f}%")
        
        # Step 7: Find the windiest city
        print("\nStep 7: Finding the windiest city (last 30 days)...")
        cursor.execute("""
        SELECT 
            c.name as city_name,
            c.country,
            ws.avg_wind_speed
        FROM weather_stats ws
        JOIN cities c ON ws.city_id = c.id
        WHERE ws.period_days = 30
        ORDER BY ws.avg_wind_speed DESC
        """)
        
        wind_rankings = cursor.fetchall()
        if wind_rankings:
            windiest_city = wind_rankings[0]
            calmest_city = wind_rankings[-1]
            
            print(f"Windiest city: {windiest_city[0]}, {windiest_city[1]} with average wind speed of {windiest_city[2]:.1f} m/s")
            print(f"Calmest city: {calmest_city[0]}, {calmest_city[1]} with average wind speed of {calmest_city[2]:.1f} m/s")
        
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

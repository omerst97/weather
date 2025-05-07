"""
Script to create weather data tables in Azure SQL Database.
"""
import pymssql
import os
import sys

def main():
    """
    Main function to create tables for weather data.
    """
    # Connection parameters for SQL authentication from environment variables
    server = os.environ.get('DB_SERVER', 'weatherdb158.database.windows.net')
    database = os.environ.get('DB_NAME', 'WeatherData')
    username = os.environ.get('DB_USER', 'Admin123123')
    password = os.environ.get('DB_PASSWORD', 'SecurePassword123!')
    
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
        
        # Step 2: Create cities table
        print("\nStep 2: Creating cities table...")
        try:
            cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'cities')
            BEGIN
                CREATE TABLE cities (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    country VARCHAR(100) NOT NULL,
                    latitude DECIMAL(9,6) NOT NULL,
                    longitude DECIMAL(9,6) NOT NULL,
                    created_at DATETIME DEFAULT GETDATE(),
                    CONSTRAINT UC_name_country UNIQUE (name, country)
                )
            END
            """)
            conn.commit()
            print("Cities table created successfully!")
        except Exception as e:
            print(f"Error creating cities table: {e}")
            cursor.close()
            conn.close()
            sys.exit(1)
        
        # Step 3: Create weather_data table
        print("\nStep 3: Creating weather_data table...")
        try:
            cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'weather_data')
            BEGIN
                CREATE TABLE weather_data (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    city_id INT NOT NULL,
                    date DATE NOT NULL,
                    temperature DECIMAL(5,2),
                    feels_like DECIMAL(5,2),
                    temperature_min DECIMAL(5,2),
                    temperature_max DECIMAL(5,2),
                    pressure INT,
                    humidity INT,
                    wind_speed DECIMAL(5,2),
                    wind_direction INT,
                    weather_condition VARCHAR(100),
                    weather_description VARCHAR(255),
                    created_at DATETIME DEFAULT GETDATE(),
                    CONSTRAINT FK_weather_data_city FOREIGN KEY (city_id) REFERENCES cities(id),
                    CONSTRAINT UC_city_date UNIQUE (city_id, date)
                )
            END
            """)
            conn.commit()
            print("Weather data table created successfully!")
        except Exception as e:
            print(f"Error creating weather_data table: {e}")
            cursor.close()
            conn.close()
            sys.exit(1)
        
        # Step 4: Create weather_stats table for aggregated statistics
        print("\nStep 4: Creating weather_stats table...")
        try:
            cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'weather_stats')
            BEGIN
                CREATE TABLE weather_stats (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    city_id INT NOT NULL,
                    stat_date DATE NOT NULL,
                    period_days INT NOT NULL,
                    avg_temperature DECIMAL(5,2),
                    min_temperature DECIMAL(5,2),
                    max_temperature DECIMAL(5,2),
                    avg_humidity INT,
                    min_humidity INT,
                    max_humidity INT,
                    avg_wind_speed DECIMAL(5,2),
                    min_wind_speed DECIMAL(5,2),
                    max_wind_speed DECIMAL(5,2),
                    avg_pressure INT,
                    min_pressure INT,
                    max_pressure INT,
                    dominant_condition VARCHAR(100),
                    created_at DATETIME DEFAULT GETDATE(),
                    CONSTRAINT FK_weather_stats_city FOREIGN KEY (city_id) REFERENCES cities(id),
                    CONSTRAINT UC_city_date_period UNIQUE (city_id, stat_date, period_days)
                )
            END
            """)
            conn.commit()
            print("Weather stats table created successfully!")
        except Exception as e:
            print(f"Error creating weather_stats table: {e}")
            cursor.close()
            conn.close()
            sys.exit(1)
        
        # Step 5: Verify tables were created
        print("\nStep 5: Verifying tables were created...")
        cursor.execute("""
        SELECT table_name = t.name
        FROM sys.tables t
        WHERE t.name IN ('cities', 'weather_data', 'weather_stats')
        ORDER BY t.name
        """)
        
        tables = cursor.fetchall()
        if len(tables) == 3:
            print("All tables were created successfully:")
            for table in tables:
                print(f"- {table[0]}")
        else:
            print("Warning: Not all tables were created.")
            print("Tables found:")
            for table in tables:
                print(f"- {table[0]}")
        
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

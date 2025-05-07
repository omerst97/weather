-- SQL script to create weather data tables

-- Create cities table
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
END;

-- Create weather_data table
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
END;

-- Insert some sample cities
IF NOT EXISTS (SELECT * FROM cities WHERE name = 'Tel Aviv')
BEGIN
    INSERT INTO cities (name, country, latitude, longitude)
    VALUES ('Tel Aviv', 'Israel', 32.0853, 34.7818)
END;

IF NOT EXISTS (SELECT * FROM cities WHERE name = 'Jerusalem')
BEGIN
    INSERT INTO cities (name, country, latitude, longitude)
    VALUES ('Jerusalem', 'Israel', 31.7683, 35.2137)
END;

IF NOT EXISTS (SELECT * FROM cities WHERE name = 'Haifa')
BEGIN
    INSERT INTO cities (name, country, latitude, longitude)
    VALUES ('Haifa', 'Israel', 32.7940, 34.9896)
END;

-- Print confirmation
SELECT 'Database tables created successfully!' AS Status;

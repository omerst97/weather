"""
Flask web application for the Weather Data Service.
Provides API endpoints to access weather data stored in Azure SQL Database.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import pymssql
import os
import datetime
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database connection parameters
DB_SERVER = os.environ.get('DB_SERVER', 'weatherdb158.database.windows.net')
DB_NAME = os.environ.get('DB_NAME', 'WeatherData')
DB_USER = os.environ.get('DB_USER', 'Admin123123')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'SecurePassword123!')

def get_db_connection():
    """Create and return a database connection."""
    return pymssql.connect(server=DB_SERVER, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

@app.route('/')
def home():
    """Home page with API documentation."""
    return jsonify({
        "service": "Weather Data API",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "API documentation"},
            {"path": "/cities", "method": "GET", "description": "List all cities"},
            {"path": "/cities/<city_id>", "method": "GET", "description": "Get city details"},
            {"path": "/weather/<city_id>", "method": "GET", "description": "Get weather data for a city"},
            {"path": "/stats/<city_id>", "method": "GET", "description": "Get weather statistics for a city"},
            {"path": "/hottest", "method": "GET", "description": "Get the hottest city"},
            {"path": "/coldest", "method": "GET", "description": "Get the coldest city"},
            {"path": "/windiest", "method": "GET", "description": "Get the windiest city"}
        ]
    })

@app.route('/cities')
def get_cities():
    """Get all cities."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, name, country, latitude, longitude
        FROM cities
        ORDER BY name
        """)
        
        cities = []
        for row in cursor.fetchall():
            cities.append({
                "id": row[0],
                "name": row[1],
                "country": row[2],
                "latitude": float(row[3]),
                "longitude": float(row[4])
            })
        
        cursor.close()
        conn.close()
        
        # Return just the array for simpler client handling
        return jsonify(cities)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cities/<int:city_id>')
def get_city(city_id):
    """Get a specific city by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, name, country, latitude, longitude
        FROM cities
        WHERE id = %s
        """, (city_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "City not found"}), 404
        
        city = {
            "id": row[0],
            "name": row[1],
            "country": row[2],
            "latitude": float(row[3]),
            "longitude": float(row[4])
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(city)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/weather/<int:city_id>')
def get_weather(city_id):
    """Get weather data for a specific city."""
    try:
        # Get query parameters
        days = request.args.get('days', default=7, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First check if the city exists
        cursor.execute("SELECT name, country FROM cities WHERE id = %s", (city_id,))
        city_row = cursor.fetchone()
        if not city_row:
            return jsonify({"error": "City not found"}), 404
        
        city_name = city_row[0]
        country = city_row[1]
        
        # Get the weather data
        cursor.execute("""
        SELECT TOP (%s)
            date,
            temperature,
            temperature_min,
            temperature_max,
            feels_like,
            pressure,
            humidity,
            wind_speed,
            wind_direction,
            weather_condition,
            weather_description
        FROM weather_data
        WHERE city_id = %s
        ORDER BY date DESC
        """, (days, city_id))
        
        weather_data = []
        for row in cursor.fetchall():
            weather_data.append({
                "date": row[0].isoformat(),
                "temperature": float(row[1]),
                "temperature_min": float(row[2]),
                "temperature_max": float(row[3]),
                "feels_like": float(row[4]) if row[4] else None,
                "pressure": int(row[5]) if row[5] else None,
                "humidity": int(row[6]) if row[6] else None,
                "wind_speed": float(row[7]) if row[7] else None,
                "wind_direction": int(row[8]) if row[8] else None,
                "weather_condition": row[9],
                "weather_description": row[10]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "city": city_name,
            "country": country,
            "weather_data": weather_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats/<int:city_id>')
def get_stats(city_id):
    """Get weather statistics for a specific city."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First check if the city exists
        cursor.execute("SELECT name, country FROM cities WHERE id = %s", (city_id,))
        city_row = cursor.fetchone()
        if not city_row:
            return jsonify({"error": "City not found"}), 404
        
        city_name = city_row[0]
        country = city_row[1]
        
        # Get the weather statistics
        cursor.execute("""
        SELECT 
            period_days,
            avg_temperature,
            min_temperature,
            max_temperature,
            avg_humidity,
            min_humidity,
            max_humidity,
            avg_wind_speed,
            min_wind_speed,
            max_wind_speed,
            avg_pressure,
            min_pressure,
            max_pressure,
            dominant_condition,
            stat_date
        FROM weather_stats
        WHERE city_id = %s
        ORDER BY period_days
        """, (city_id,))
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                "period_days": row[0],
                "avg_temperature": float(row[1]) if row[1] else None,
                "min_temperature": float(row[2]) if row[2] else None,
                "max_temperature": float(row[3]) if row[3] else None,
                "avg_humidity": float(row[4]) if row[4] else None,
                "min_humidity": float(row[5]) if row[5] else None,
                "max_humidity": float(row[6]) if row[6] else None,
                "avg_wind_speed": float(row[7]) if row[7] else None,
                "min_wind_speed": float(row[8]) if row[8] else None,
                "max_wind_speed": float(row[9]) if row[9] else None,
                "avg_pressure": float(row[10]) if row[10] else None,
                "min_pressure": float(row[11]) if row[11] else None,
                "max_pressure": float(row[12]) if row[12] else None,
                "dominant_condition": row[13],
                "stat_date": row[14].isoformat() if row[14] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "city": city_name,
            "country": country,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/hottest')
def get_hottest():
    """Get the hottest city based on average temperature."""
    try:
        period = request.args.get('period', default=30, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT TOP 1
            c.id,
            c.name,
            c.country,
            ws.avg_temperature,
            ws.min_temperature,
            ws.max_temperature
        FROM weather_stats ws
        JOIN cities c ON ws.city_id = c.id
        WHERE ws.period_days = %s
        ORDER BY ws.avg_temperature DESC
        """, (period,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "No statistics found"}), 404
        
        hottest_city = {
            "id": row[0],
            "name": row[1],
            "country": row[2],
            "avg_temperature": float(row[3]) if row[3] else None,
            "min_temperature": float(row[4]) if row[4] else None,
            "max_temperature": float(row[5]) if row[5] else None
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(hottest_city)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/coldest')
def get_coldest():
    """Get the coldest city based on average temperature."""
    try:
        period = request.args.get('period', default=30, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT TOP 1
            c.id,
            c.name,
            c.country,
            ws.avg_temperature,
            ws.min_temperature,
            ws.max_temperature
        FROM weather_stats ws
        JOIN cities c ON ws.city_id = c.id
        WHERE ws.period_days = %s
        ORDER BY ws.avg_temperature ASC
        """, (period,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "No statistics found"}), 404
        
        coldest_city = {
            "id": row[0],
            "name": row[1],
            "country": row[2],
            "avg_temperature": float(row[3]) if row[3] else None,
            "min_temperature": float(row[4]) if row[4] else None,
            "max_temperature": float(row[5]) if row[5] else None
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(coldest_city)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/windiest')
def get_windiest():
    """Get the windiest city based on average wind speed."""
    try:
        period = request.args.get('period', default=30, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT TOP 1
            c.id,
            c.name,
            c.country,
            ws.avg_wind_speed,
            ws.dominant_condition
        FROM weather_stats ws
        JOIN cities c ON ws.city_id = c.id
        WHERE ws.period_days = %s
        ORDER BY ws.avg_wind_speed DESC
        """, (period,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "No statistics found"}), 404
        
        windiest_city = {
            "id": row[0],
            "name": row[1],
            "country": row[2],
            "avg_wind_speed": float(row[3]) if row[3] else None,
            "dominant_condition": row[4]
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(windiest_city)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get('PORT', 5000))
    # Run the app, binding to all interfaces
    app.run(host='0.0.0.0', port=port)

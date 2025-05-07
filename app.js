// Configuration
const API_BASE_URL = 'http://20.217.178.37'; // Connect to our deployed API service

// DOM elements
const citySelect = document.getElementById('citySelect');
const selectedCityElement = document.getElementById('selectedCity');
const cityCoordinatesElement = document.getElementById('cityCoordinates');
const loadingOverlay = document.getElementById('loadingOverlay');
const weatherConditionsContainer = document.getElementById('weatherConditions');

// Chart objects
let temperatureChart;
let humidityChart;
let windChart;
let pressureChart;

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initialized');
    initCharts();
    loadCities();
    
    // Add event listener for city selection
    citySelect.addEventListener('change', handleCityChange);
});

// Initialize chart objects
function initCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top'
            }
        },
        scales: {
            y: {
                beginAtZero: false
            }
        }
    };
    
    // Temperature chart
    temperatureChart = new Chart(
        document.getElementById('temperatureChart'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperature (ֲ°C)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: chartOptions
        }
    );
    
    // Humidity chart
    humidityChart = new Chart(
        document.getElementById('humidityChart'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Humidity (%)',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: chartOptions
        }
    );
    
    // Wind chart
    windChart = new Chart(
        document.getElementById('windChart'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Wind Speed (km/h)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: chartOptions
        }
    );
    
    // Pressure chart
    pressureChart = new Chart(
        document.getElementById('pressureChart'),
        {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Pressure (hPa)',
                    data: [],
                    borderColor: 'rgb(153, 102, 255)',
                    backgroundColor: 'rgba(153, 102, 255, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: chartOptions
        }
    );
}

// Show loading overlay
function showLoading() {
    loadingOverlay.classList.remove('d-none');
}

// Hide loading overlay
function hideLoading() {
    loadingOverlay.classList.add('d-none');
}

// Handle city selection change
async function handleCityChange() {
    const cityId = citySelect.value;
    if (!cityId) return;
    
    showLoading();
    
    try {
        // Get the selected city details
        const selectedOption = citySelect.options[citySelect.selectedIndex];
        const cityName = selectedOption.textContent;
        
        // Update UI with selected city
        selectedCityElement.textContent = cityName;
        
        // Load weather data and stats for the selected city
        await Promise.all([
            loadWeatherData(cityId),
            loadWeatherStats(cityId)
        ]);
    } catch (error) {
        console.error('Error handling city change:', error);
        alert('Failed to load data for the selected city. Please try again.');
    } finally {
        hideLoading();
    }
}

// Load cities into the dropdown
async function loadCities() {
    showLoading();
    
    try {
        console.log('Loading cities from API');
        const response = await fetch(`${API_BASE_URL}/cities`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch cities: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Cities data loaded:', data);
        
        // Handle both formats: array directly or {cities: [...]} object
        const cities = Array.isArray(data) ? data : (data.cities || []);
        
        if (!Array.isArray(cities) || cities.length === 0) {
            throw new Error('No cities found in data');
        }
        
        // Clear existing options except the first one
        while (citySelect.options.length > 1) {
            citySelect.remove(1);
        }
        
        // Sort cities alphabetically
        cities.sort((a, b) => a.name.localeCompare(b.name));
        
        // Add cities to dropdown
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.id;
            option.textContent = `${city.name}, ${city.country}`;
            option.dataset.latitude = city.latitude;
            option.dataset.longitude = city.longitude;
            citySelect.appendChild(option);
        });
        
        console.log(`Loaded ${cities.length} cities`);
    } catch (error) {
        console.error('Error loading cities:', error);
        alert('Failed to load cities. Please refresh the page to try again.');
    } finally {
        hideLoading();
    }
}

// Load weather data for a specific city
async function loadWeatherData(cityId) {
    try {
        if (!cityId) {
            console.error('No city ID provided for weather data');
            return;
        }
        
        console.log(`Loading weather data for city ID: ${cityId}`);
        const response = await fetch(`${API_BASE_URL}/weather/${cityId}`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch weather data: ${response.status}`);
        }
        
        const weatherData = await response.json();
        console.log('Weather data loaded:', weatherData);
        
        if (!weatherData) {
            throw new Error('Empty weather data received');
        }
        
        // Update city coordinates
        updateCityCoordinates(cityId);
        
        // Process data for charts and weather conditions
        updateCharts(weatherData);
        updateWeatherConditions(weatherData);
        
        // Calculate and display statistics
        calculateStatistics(weatherData);
    } catch (error) {
        console.error('Error loading weather data:', error);
        clearCharts();
        clearWeatherConditions();
    }
}

// Update city coordinates display
function updateCityCoordinates(cityId) {
    const selectedOption = [...citySelect.options].find(option => option.value === cityId.toString());
    
    if (selectedOption) {
        const latitude = selectedOption.dataset.latitude;
        const longitude = selectedOption.dataset.longitude;
        
        if (latitude && longitude) {
            cityCoordinatesElement.textContent = `Coordinates: ${latitude}, ${longitude}`;
        } else {
            cityCoordinatesElement.textContent = '';
        }
    } else {
        cityCoordinatesElement.textContent = '';
    }
}

// Update charts with weather data
function updateCharts(weatherData) {
    // Check if we have the expected data structure
    if (!weatherData || !weatherData.weather_data) {
        console.error('Invalid weather data format:', weatherData);
        clearCharts();
        return;
    }
    
    const data = weatherData.weather_data;
    
    if (!Array.isArray(data) || data.length === 0) {
        console.error('No weather data found:', weatherData);
        clearCharts();
        return;
    }
    
    // Sort data by date (oldest to newest)
    data.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Extract data for charts
    const labels = data.map(item => formatDate(item.date));
    const temperatures = data.map(item => item.temperature);
    const humidities = data.map(item => item.humidity);
    const windSpeeds = data.map(item => item.wind_speed);
    const pressures = data.map(item => item.pressure);
    
    // Update temperature chart
    temperatureChart.data.labels = labels;
    temperatureChart.data.datasets[0].data = temperatures;
    temperatureChart.update();
    
    // Update humidity chart
    humidityChart.data.labels = labels;
    humidityChart.data.datasets[0].data = humidities;
    humidityChart.update();
    
    // Update wind chart
    windChart.data.labels = labels;
    windChart.data.datasets[0].data = windSpeeds;
    windChart.update();
    
    // Update pressure chart
    pressureChart.data.labels = labels;
    pressureChart.data.datasets[0].data = pressures;
    pressureChart.update();
}

// Clear all charts
function clearCharts() {
    const charts = [temperatureChart, humidityChart, windChart, pressureChart];
    
    charts.forEach(chart => {
        chart.data.labels = [];
        chart.data.datasets[0].data = [];
        chart.update();
    });
}

// Format date to a more readable format
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Update weather conditions display
function updateWeatherConditions(weatherData) {
    // Clear previous weather conditions
    weatherConditionsContainer.innerHTML = '';
    
    if (!weatherData || !weatherData.weather_data || !Array.isArray(weatherData.weather_data)) {
        return;
    }
    
    const data = [...weatherData.weather_data];
    
    // Sort by date (newest first)
    data.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    // Take only the last 7 days
    const recentData = data.slice(0, 7);
    
    // Create weather condition cards
    recentData.forEach(item => {
        const date = new Date(item.date);
        const formattedDate = date.toLocaleDateString('en-US', { 
            weekday: 'short', 
            month: 'short', 
            day: 'numeric' 
        });
        
        const weatherIcon = getWeatherIcon(item.weather_condition);
        
        const card = document.createElement('div');
        card.className = 'col-md-3 col-sm-6';
        card.innerHTML = `
            <div class="weather-condition-card">
                <div class="weather-icon">${weatherIcon}</div>
                <div class="weather-date">${formattedDate}</div>
                <div class="weather-temp">${item.temperature.toFixed(1)}ֲ°C</div>
                <div class="weather-description">${item.weather_description}</div>
                <div class="weather-details mt-2">
                    <small>
                        <i class="bi bi-droplet-fill text-primary"></i> ${item.humidity}% | 
                        <i class="bi bi-wind text-success"></i> ${item.wind_speed} km/h
                    </small>
                </div>
            </div>
        `;
        
        weatherConditionsContainer.appendChild(card);
    });
}

// Clear weather conditions
function clearWeatherConditions() {
    weatherConditionsContainer.innerHTML = '';
}

// Get appropriate weather icon based on condition
function getWeatherIcon(condition) {
    const iconMap = {
        'Clear': '<i class="bi bi-sun-fill text-warning"></i>',
        'Clouds': '<i class="bi bi-cloud-fill text-secondary"></i>',
        'Rain': '<i class="bi bi-cloud-rain-fill text-primary"></i>',
        'Drizzle': '<i class="bi bi-cloud-drizzle-fill text-info"></i>',
        'Thunderstorm': '<i class="bi bi-cloud-lightning-fill text-danger"></i>',
        'Snow': '<i class="bi bi-snow text-light"></i>',
        'Mist': '<i class="bi bi-cloud-haze-fill text-secondary"></i>',
        'Fog': '<i class="bi bi-cloud-fog-fill text-secondary"></i>'
    };
    
    return iconMap[condition] || '<i class="bi bi-cloud-fill text-secondary"></i>';
}

// Calculate statistics from weather data
function calculateStatistics(weatherData) {
    if (!weatherData || !weatherData.weather_data || !Array.isArray(weatherData.weather_data) || weatherData.weather_data.length === 0) {
        clearStatistics();
        return;
    }
    
    const data = weatherData.weather_data;
    
    // Temperature statistics
    const temperatures = data.map(item => item.temperature).filter(val => val !== null && val !== undefined);
    if (temperatures.length > 0) {
        document.getElementById('minTemp').textContent = Math.min(...temperatures).toFixed(1);
        document.getElementById('maxTemp').textContent = Math.max(...temperatures).toFixed(1);
        document.getElementById('avgTemp').textContent = (temperatures.reduce((a, b) => a + b, 0) / temperatures.length).toFixed(1);
    }
    
    // Humidity statistics
    const humidities = data.map(item => item.humidity).filter(val => val !== null && val !== undefined);
    if (humidities.length > 0) {
        document.getElementById('minHumidity').textContent = Math.min(...humidities).toFixed(0);
        document.getElementById('maxHumidity').textContent = Math.max(...humidities).toFixed(0);
        document.getElementById('avgHumidity').textContent = (humidities.reduce((a, b) => a + b, 0) / humidities.length).toFixed(0);
    }
    
    // Wind speed statistics
    const windSpeeds = data.map(item => item.wind_speed).filter(val => val !== null && val !== undefined);
    if (windSpeeds.length > 0) {
        document.getElementById('minWind').textContent = Math.min(...windSpeeds).toFixed(1);
        document.getElementById('maxWind').textContent = Math.max(...windSpeeds).toFixed(1);
        document.getElementById('avgWind').textContent = (windSpeeds.reduce((a, b) => a + b, 0) / windSpeeds.length).toFixed(1);
    }
    
    // Pressure statistics
    const pressures = data.map(item => item.pressure).filter(val => val !== null && val !== undefined);
    if (pressures.length > 0) {
        document.getElementById('minPressure').textContent = Math.min(...pressures).toFixed(0);
        document.getElementById('maxPressure').textContent = Math.max(...pressures).toFixed(0);
        document.getElementById('avgPressure').textContent = (pressures.reduce((a, b) => a + b, 0) / pressures.length).toFixed(0);
    }
}

// Clear statistics
function clearStatistics() {
    const statElements = [
        'minTemp', 'maxTemp', 'avgTemp',
        'minHumidity', 'maxHumidity', 'avgHumidity',
        'minWind', 'maxWind', 'avgWind',
        'minPressure', 'maxPressure', 'avgPressure'
    ];
    
    statElements.forEach(id => {
        document.getElementById(id).textContent = '--';
    });
}

// Load weather statistics for a specific city
async function loadWeatherStats(cityId) {
    try {
        if (!cityId) {
            console.error('No city ID provided for weather stats');
            return;
        }
        
        console.log(`Loading weather stats for city ID: ${cityId}`);
        const response = await fetch(`${API_BASE_URL}/stats/${cityId}`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch weather stats: ${response.status}`);
        }
        
        const stats = await response.json();
        console.log('Weather stats loaded:', stats);
        
        // We'll use our calculated statistics from the weather data
        // This is just a fallback if we want to use pre-calculated stats from the API
        if (stats && stats.stats && stats.stats.length > 0) {
            const statData = stats.stats[0]; // Use the first stats entry
            
            // We could update our stats table with this data if needed
            console.log('Server-side stats available:', statData);
        }
    } catch (error) {
        console.error('Error loading weather stats:', error);
    }
}




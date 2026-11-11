#pragma once
#include <Arduino.h>

static const char* WIFI_SSID = "YOUR_WIFI_SSID";
static const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// Use PC LAN IP, e.g. http://192.168.1.10:5000/api/plant/analyze
static const char* API_ANALYZE_URL = "http://192.168.1.100:5000/api/plant/analyze";
static const char* DEVICE_ID = "plantsense-01";
static const char* PLANT_SPECIES = "unknown"; // set per plant; multiple species supported
static const char* GROWTH_STAGE = "unknown";

// GPIO placeholders: leave -1 until circuit and pin map are finalized.
static constexpr int PIN_DHT = -1;
static constexpr int PIN_I2C_SDA = -1;
static constexpr int PIN_I2C_SCL = -1;
static constexpr int PIN_PUMP_MOSFET = -1;
static constexpr int PIN_LIGHT_MOSFET = -1;
static constexpr uint8_t SOIL_ADC_CHANNEL = 0;

// Calibrate ADC counts in dry and wet soil; example values only.
static constexpr int16_t SOIL_ADC_DRY = 20000;
static constexpr int16_t SOIL_ADC_WET = 8000;

// Placeholder thresholds; create species-specific profiles after choosing plants.
static constexpr float SOIL_PUMP_ON_BELOW_PCT = 30.0f;
static constexpr float SOIL_PUMP_OFF_ABOVE_PCT = 42.0f;
static constexpr float LIGHT_ON_BELOW_LUX = 2000.0f;
static constexpr uint32_t MAX_PUMP_RUNTIME_MS = 8000;
static constexpr uint32_t PUMP_COOLDOWN_MS = 60000;
static constexpr uint32_t SENSOR_INTERVAL_MS = 5000;
static constexpr uint32_t IMAGE_INTERVAL_MS = 300000;
static constexpr uint32_t WIFI_RETRY_INTERVAL_MS = 10000;
static constexpr uint32_t HTTP_TIMEOUT_MS = 25000;
#define DHT_SENSOR_TYPE DHT22

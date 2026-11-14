#pragma once
#include <Arduino.h>

#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#else
// Copy wifi_secrets.example.h to wifi_secrets.h and fill it locally.
static const char* WIFI_SSID = "YOUR_WIFI_SSID";
static const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
#endif
// Use PC LAN IP, e.g. http://192.168.1.10:5000/api/plant/analyze
static const char* API_ANALYZE_URL = "http://192.168.0.103:5000/api/plant/analyze";
static const char* API_TELEMETRY_URL = "http://192.168.0.103:5000/api/plant/data";
// Match backend DEVICE_API_TOKEN when authentication is enabled.
static const char* DEVICE_API_TOKEN = "";
static const char* DEVICE_ID = "plantsense-01";
static const char* PLANT_SPECIES = "unknown"; // set per plant; multiple species supported
static const char* GROWTH_STAGE = "unknown";

// AI-Thinker wiring supplied by the user; numbers are GPIO labels, not header positions.
// GPIO2 must be low/floating for serial flashing; a DHT pull-up may prevent flashing.
static constexpr int PIN_DHT = 2;
static constexpr int PIN_I2C_SDA = 13;
static constexpr int PIN_I2C_SCL = 14;
// Pump and grow light are not connected. Keep their outputs disabled.
static constexpr int PIN_PUMP_MOSFET = -1;
static constexpr int PIN_LIGHT_MOSFET = -1;
static constexpr uint8_t SOIL_ADC_CHANNEL = 0;
static constexpr uint8_t SOIL_ADC_I2C_ADDRESS = 0x48; // ADS1115 ADDR -> GND
static constexpr uint8_t LIGHT_I2C_ADDRESS = 0x23; // Default; confirm BH1750 ADDR wiring

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
static constexpr uint32_t TELEMETRY_INTERVAL_MS = 5000;
static constexpr uint32_t IMAGE_INTERVAL_MS = 300000;
static constexpr uint32_t WIFI_RETRY_INTERVAL_MS = 10000;
static constexpr uint32_t HTTP_TIMEOUT_MS = 25000;
#define DHT_SENSOR_TYPE DHT22

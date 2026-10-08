// Project-wide includes and defines. Header only: do NOT define variables here,
// it will be included by several .cpp files (multiple definition at link time).
#pragma once

//USER INCLUDES
#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <esp_mac.h>

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "src/secrets.h missing: copy src/secrets.h.example to src/secrets.h and fill it in"
#endif

//USER DEFINES
#define H_PREFIX "iapet" //prefix of the device id, the last 3 bytes of the MAC are appended (e.g. iapet-a1b2c3)
#define VERSION "M5GRAY" //version of the hardware
#define FIRMWARE "0.1.0" //firmware version

#define DEBUG_SERIAL Serial //debug serial port
#define DEBUG_BAUDRATE 115200 //debug baudrate

#define WIFI_RETRY_INTERVAL_MS 5000 //interval between wireless reconnection attempts

#pragma once
#include <Wire.h>

// IP5306 PMIC — M5Stack Gray internal I2C (SDA=21, SCL=22, addr=0x75)

class IP5306 {
public:
    IP5306(TwoWire& wire = Wire, uint8_t addr = 0x75)
        : _wire(wire), _addr(addr) {}

    void begin(uint8_t sda = 21, uint8_t scl = 22, uint32_t freq = 400000) {
        _wire.begin(sda, scl, freq);
    }

    // Returns true while USB power is present and actively charging the battery.
    // REG_READ0 (0x70), bit 3.
    bool isCharging() {
        return (_readReg(0x70) & 0x08) != 0;
    }

    // Auto power-on when USB charger is connected, even if device was off.
    // REG_SYS_CTL1 (0x01), bit 0.
    bool setBootOnCharge(bool en) {
        uint8_t val = _readReg(0x01);
        return _writeReg(0x01, en ? (val | 0x01) : (val & ~0x01));
    }

    // Prevent auto-shutdown when the load current is low (e.g. idle ESP32).
    // REG_SYS_CTL0 (0x00), bit 1.
    bool setBoostKeepOn(bool en) {
        uint8_t val = _readReg(0x00);
        return _writeReg(0x00, en ? (val | 0x02) : (val & ~0x02));
    }

private:
    TwoWire& _wire;
    uint8_t  _addr;

    uint8_t _readReg(uint8_t reg) {
        _wire.beginTransmission(_addr);
        _wire.write(reg);
        if (_wire.endTransmission(false) != 0) return 0;
        _wire.requestFrom(_addr, (uint8_t)1);
        return _wire.available() ? _wire.read() : 0;
    }

    bool _writeReg(uint8_t reg, uint8_t val) {
        _wire.beginTransmission(_addr);
        _wire.write(reg);
        _wire.write(val);
        return _wire.endTransmission() == 0;
    }
};

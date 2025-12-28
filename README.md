# Chorus32 Timer Plugin for RotorHazard

A RotorHazard plugin that provides full integration with Chorus32 lap timing hardware. This plugin enables RotorHazard to use Chorus32 devices for lap timing, RSSI monitoring, and race control.

## Features

- **Multiple Device Support**: Connect multiple Chorus32 devices (up to 8 devices = 48 nodes total)
- **6 Nodes Per Device**: Each Chorus32 supports 6 receiver nodes
- **TCP and Serial Connections**: Support for both network (WiFi/Ethernet) and USB serial connections
- **RotorHazard-Side Lap Detection**: Chorus32 pushes RSSI values continuously, RotorHazard detects threshold crossings
- **RSSI Monitoring**: Real-time RSSI tracking with configurable push intervals (10ms default)
- **Full RSSI History**: Complete RSSI data available for advanced marshalling and analysis
- **Per-Node Control**: Enable/disable individual receiver nodes
- **Threshold-Based Detection**: Configurable RSSI threshold per node
- **Configuration Persistence**: All settings saved across restarts
- **Simple ASCII Protocol**: Easy to debug with human-readable messages

## Hardware Requirements

- One or more Chorus32 timing devices
- Chorus32 firmware with protocol support
- Network connection (WiFi/Ethernet) or USB serial connection

## Installation

### 1. Copy Plugin to RotorHazard

```bash
# Navigate to your RotorHazard data directory
cd /path/to/RotorHazard/data/plugins

# Copy the plugin
cp -r /path/to/chorus32-provider/custom_plugins/interface_chorus32 ./
```

### 2. Install Dependencies (if using serial)

If you plan to use USB serial connections, install pyserial:

```bash
pip install pyserial
```

### 3. Restart RotorHazard

Restart the RotorHazard server to load the plugin:

```bash
sudo systemctl restart rotorhazard
# or
./start.sh
```

## Configuration

### Basic Setup

1. Navigate to **Settings** in RotorHazard
2. Find the **Chorus32 General Setup** panel
3. Set **Device Count** (requires restart if changed)
4. Click **Connect** to connect to devices

### Connection Methods

#### TCP/Network (Default - Recommended)

For Chorus32 devices on your network:

```
192.168.4.1              # Uses default port 9000
192.168.4.1:9000         # Specify custom port
socket://192.168.4.1:9000/  # Full URL format
```

**Default Chorus32 WiFi Settings:**
- IP Address: `192.168.4.1`
- Port: `9000`
- Connect to Chorus32 WiFi network from RotorHazard server

#### Serial/USB

For direct USB connections:

```
/dev/ttyUSB0             # Linux
COM3                     # Windows
serial:/dev/ttyUSB0      # Full URL format
```

### Device Configuration

For each Chorus32 device, configure in the device detail panel:

#### Per-Device Settings

- **Device Address**: IP address or serial port
- **RSSI Push Interval**: How often device sends RSSI updates (milliseconds)
  - Recommended: `10` (10ms = 100Hz)
  - Range: `5-50ms` for racing, `0` to disable

#### Per-Node Settings (6 nodes per device)

For each receiver node:

- **Active**: Enable/disable this receiver

### Threshold Calibration

**Thresholds are managed by RotorHazard's standard calibration system**, not by the plugin:

- Use RotorHazard's **Calibration** feature to set enter-at and exit-at levels per pilot
- Calibration can be done manually or automatically
- Each pilot can have different threshold settings
- Supports advanced features like auto-calibration and dynamic thresholds

**Minimum lap time** is also a global RotorHazard setting, not per-device

## RSSI-Based Lap Detection

This plugin uses RotorHazard-side lap detection from RSSI values:

### How It Works

1. Chorus32 devices continuously push RSSI values at configurable intervals (default: 10ms)
2. RotorHazard receives RSSI stream and monitors for threshold crossings
3. When RSSI rises above threshold, a crossing is detected (entering gate)
4. Peak RSSI is tracked during the entire crossing
5. When RSSI falls below threshold, a lap is recorded (exiting gate)
6. Peak RSSI is saved with each lap for marshalling and analysis
7. Minimum lap time prevents false detections from signal bounce

### Benefits

- **Full RSSI History**: Every RSSI sample available for analysis and replay
- **Advanced Marshalling**: Review complete signal patterns, not just peaks
- **Flexible Thresholds**: Adjust detection sensitivity without device changes
- **RotorHazard Features**: Access to all RotorHazard crossing detection algorithms

### Recommended Settings

- **RSSI Push Interval**: `10ms` (good for racing, 4-8 samples per crossing)
- For slower racing or testing: `20ms`
- For very fast racing: `5ms` (higher network load)

### RSSI Interval Impact

At 100 mph through a 2-meter gate:
- **100ms**: 0-1 samples per crossing ⚠️ (too slow)
- **20ms**: 2-4 samples per crossing ✓ (acceptable)
- **10ms**: 4-8 samples per crossing ✓✓ (recommended)
- **5ms**: 9-15 samples per crossing ✓✓✓ (excellent, higher load)

## Usage

### How Racing Works

1. **Connect Devices**: Configure and connect Chorus32 devices in plugin settings
2. **Continuous RSSI**: Chorus32 continuously pushes RSSI values (default: every 10ms)
3. **Configure Race**: Set up pilots and heats in RotorHazard as normal
4. **Start Race**: Click **Stage Race** or **Start Race** in RotorHazard
5. **Automatic Detection**: RotorHazard detects laps from RSSI threshold crossings
6. **Real-Time Laps**: Laps appear immediately in RotorHazard UI
7. **Stop Race**: Click **Stop Race** - results saved to database

### Important Notes

- **No Chorus32 Race Mode**: Chorus32 just pushes RSSI continuously, RotorHazard handles all lap detection
- **Threshold Calibration**: Use RotorHazard's Calibration feature (not plugin settings)
- **Per-Pilot Thresholds**: Each pilot can have different enter-at/exit-at levels
- **Minimum Lap Time**: Global RotorHazard setting (Settings → Event & Classes)

### Viewing RSSI Data

All lap records include complete RSSI data:
- **Peak RSSI**: Maximum signal strength during crossing
- **Full History**: Complete RSSI timeline for analysis
- **Marshalling**: Use RotorHazard's marshalling features to review signal patterns
- **Export**: Available in lap data exports for external analysis

## Troubleshooting

### Cannot Connect to Device

**Network Connection:**
```bash
# Test connectivity
ping 192.168.4.1

# Check if port 9000 is accessible
nc -zv 192.168.4.1 9000

# Verify you're on the Chorus32 WiFi network
```

**Serial Connection:**
```bash
# List serial ports (Linux)
ls /dev/ttyUSB*
ls /dev/ttyACM*

# Check permissions (Linux)
sudo chmod 666 /dev/ttyUSB0

# Or add user to dialout group
sudo usermod -a -G dialout $USER
```

### No Laps Detected

1. **Check node is active**: Verify node Active checkbox is enabled in plugin settings
2. **Calibrate thresholds**: Use RotorHazard's Calibration feature to set enter-at/exit-at levels
3. **Check RSSI**: Verify RSSI updates are being received (check logs or RSSI graph)
4. **Check race started**: Ensure race was started (not just staged)
5. **Check frequency**: Verify node is on correct band/channel for the pilot's VTX
6. **Check enter-at level**: Make sure enter-at level is lower than the pilot's signal strength

### RSSI Not Updating

1. **Check RSSI interval**: Ensure interval > 0 (default: 10ms)
2. **Check node active**: RSSI only pushed for active nodes
3. **Check connection**: Verify device is connected
4. **Check logs**: Look for RSSI messages in RotorHazard logs

### Time Synchronization Issues

The plugin automatically synchronizes time between Chorus32 and RotorHazard server:

- Chorus32 uses millisecond precision
- Time offset calculated on connection
- Should be accurate within a few milliseconds

If lap times seem incorrect:
1. Reconnect devices (disconnect and connect)
2. Check RotorHazard system time is accurate
3. Check network latency (for TCP connections)

## Protocol Reference

The plugin uses the Chorus32 ASCII text protocol:

### Command Format

```
Request:  R{node}{command}{data}\n
Response: S{node}{command}{data}\n
```

### Key Commands Used by Plugin

| Command | Description | Example | Used By Plugin |
|---------|-------------|---------|----------------|
| `N` | Number of receivers | `N0` → `N6` | ✓ (on connect) |
| `B` | Band selection | `R0B0` (node 0, Raceband) | ✓ |
| `C` | Channel | `R0C0` (node 0, channel 1) | ✓ |
| `T` | Threshold | `R0T03E8` (node 0, 1000) | ✗ (RH calibration used) |
| `M` | Min lap time | `R*M05` (all nodes, 5 sec) | ✗ (RH global setting) |
| `R` | Race mode | `R*R2` (all nodes, start) | ✗ (not used - RH detects laps) |
| `A` | Active/inactive | `R0A1` (node 0, active) | ✓ |
| `I` | RSSI interval | `R0I000A` (node 0, 10ms) | ✓ (enables RSSI push) |
| `L` | Lap detected | `S0L0100000064` (response) | ✗ (ignored - RH detects from RSSI) |
| `r` | RSSI value | `S0r0ABC` (response) | ✓ (used for lap detection) |
| `t` | Time | `R0t` (request time) | ✓ (time sync) |

### Wildcard Commands

Use `*` for node to broadcast to all nodes:
```
R*R2\n    # Start race on all nodes
R*M05\n   # Set min lap 5 seconds on all nodes
```

## Known Limitations

1. **6 Receivers Per Device**: Chorus32 has 6 nodes, not 8 like some other timers
2. **No Gain Control**: Chorus32 hardware doesn't support gain adjustment
3. **Millisecond Time Precision**: Less precise than microsecond timers (sufficient for racing)
4. **No CRC Validation**: ASCII protocol has no error detection (less robust than binary protocols)
5. **No Save to Flash**: Settings must be reconfigured on device power cycle

## Comparison with LapRF

| Feature | LapRF | Chorus32 |
|---------|-------|----------|
| Receivers per device | 8 | 6 |
| Lap detection | Device-side | RotorHazard-side (from RSSI) |
| Full RSSI history | ✗ | ✓ |
| Gain control | ✓ | ✗ |
| Threshold | ✓ | ✓ |
| Min lap time | ✓ | ✓ |
| RSSI monitoring | Auto | Push (configurable) |
| Time precision | Microsecond | Millisecond |
| Protocol | Binary | ASCII |
| Per-node enable | ✗ | ✓ |
| Marshalling support | ✓ | ✓ (enhanced with full RSSI) |
| Price | $$$ | $ |

## Development

### File Structure

```
interface_chorus32/
├── __init__.py              # Main plugin (Node, Device, Interface, Provider)
├── chorus32_protocol.py     # Protocol encoder/decoder
└── manifest.json            # Plugin metadata
```

### Logging

Enable debug logging in RotorHazard config:

```python
LOGGING_LEVEL = 'DEBUG'
```

View logs:
```bash
tail -f /path/to/rotorhazard/log/rh.log
```

### Testing

Test protocol encoding/decoding:

```python
from interface_chorus32 import chorus32_protocol as chorus32

# Encode command
cmd = chorus32.Chorus32Encoder.encode_set_threshold(0, 1000)
print(cmd)  # "R0T03E8\n"

# Decode response
msg = chorus32.Chorus32Decoder.parse_message("S0T03E8")
print(msg.command, msg.data)  # T 03E8
```

## Support

For issues, questions, or contributions:

- Plugin Repository: https://github.com/bob9/Chorus32-RH-Plugin
- Chorus32 Firmware: https://github.com/Chorus32-LapTimer
- RotorHazard: https://github.com/RotorHazard/RotorHazard
- Report plugin issues: https://github.com/bob9/Chorus32-RH-Plugin/issues

## License

GPL-3.0 License - See LICENSE file for details

## Credits

- Based on the LapRF provider plugin architecture
- Chorus32 firmware and protocol by the Chorus32 development team
- RotorHazard timing system by the RotorHazard development team

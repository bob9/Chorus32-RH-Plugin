# Chorus32 Timer Plugin for RotorHazard

A RotorHazard plugin that provides full integration with Chorus32 lap timing hardware. This plugin enables RotorHazard to use Chorus32 devices for lap timing, RSSI monitoring, and race control.

## Features

- **Multiple Device Support**: Connect multiple Chorus32 devices (up to 8 devices = 48 nodes total)
- **6 Nodes Per Device**: Each Chorus32 supports 6 receiver nodes
- **TCP and Serial Connections**: Support for both network (WiFi/Ethernet) and USB serial connections
- **RSSI Monitoring**: Real-time RSSI tracking with configurable push intervals (10ms default)
- **Marshalling Support**: Peak RSSI values captured per lap for marshalling decisions
- **Per-Node Control**: Enable/disable individual receiver nodes
- **Race State Control**: Start/stop races from RotorHazard
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
- **Minimum Lap Time**: Minimum time between laps (seconds)
- **RSSI Push Interval**: How often device sends RSSI updates (milliseconds)
  - Recommended: `10` (10ms = 100Hz)
  - Range: `5-50ms` for racing, `0` to disable

#### Per-Node Settings (6 nodes per device)

For each receiver node:

- **Threshold**: Detection threshold (0-3000, typical: 800)
- **Active**: Enable/disable this receiver

### Combined Controls

Use these to configure all devices/nodes at once:

- **Set All Thresholds**: Apply same threshold to all 6 nodes on all devices
- **Set All Min Lap Times**: Apply same minimum lap time to all devices

## RSSI Monitoring for Marshalling

The plugin automatically captures RSSI (signal strength) data for marshalling:

### How It Works

1. Plugin enables automatic RSSI push from Chorus32 (configurable interval)
2. Device sends RSSI updates continuously (e.g., every 10ms)
3. Plugin tracks peak RSSI during each lap crossing
4. Peak RSSI is saved with each lap in RotorHazard
5. Marshals can review RSSI values to validate lap detections

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

### Starting a Race

1. Configure pilots and heats in RotorHazard as normal
2. Click **Stage Race** or **Start Race**
3. Plugin automatically tells Chorus32 to start detecting laps
4. Laps appear in real-time in RotorHazard UI

### Stopping a Race

1. Click **Stop Race** in RotorHazard
2. Plugin tells Chorus32 to stop lap detection
3. Results are saved in RotorHazard database

### Viewing RSSI Data

Lap records in RotorHazard include `peak_rssi` values:
- Available in lap data exports
- Used by RotorHazard's marshalling features
- Helps validate lap detection quality

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

1. **Check node is active**: Verify node Active checkbox is enabled
2. **Check threshold**: Try lowering threshold (e.g., 500-800)
3. **Check RSSI**: Verify RSSI updates are being received (check logs)
4. **Check race mode**: Ensure race was started (not just staged)
5. **Check frequency**: Verify node is on correct band/channel

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

### Key Commands

| Command | Description | Example |
|---------|-------------|---------|
| `N` | Number of receivers | `N0` → `N6` |
| `B` | Band selection | `R0B0` (node 0, Raceband) |
| `C` | Channel | `R0C0` (node 0, channel 1) |
| `T` | Threshold | `R0T03E8` (node 0, 1000) |
| `M` | Min lap time | `R*M05` (all nodes, 5 sec) |
| `R` | Race mode | `R*R2` (all nodes, start) |
| `A` | Active/inactive | `R0A1` (node 0, active) |
| `I` | RSSI interval | `R0I000A` (node 0, 10ms) |
| `L` | Lap detected | `S0L0100000064` (response) |
| `r` | RSSI value | `S0r0ABC` (response) |
| `t` | Time | `R0t` (request time) |

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
| Gain control | ✓ | ✗ |
| Threshold | ✓ | ✓ |
| Min lap time | ✓ | ✓ |
| RSSI monitoring | Auto | Push (configurable) |
| Time precision | Microsecond | Millisecond |
| Protocol | Binary | ASCII |
| Per-node enable | ✗ | ✓ |
| Marshalling support | ✓ | ✓ |
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

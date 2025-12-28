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

## How This Enhances Chorus32

**For Chorus32 Developers:** This plugin integrates Chorus32 hardware into RotorHazard's comprehensive race management ecosystem while leveraging Chorus32's strengths.

### Architecture Overview

**Chorus32's Role:**
- **RSSI Sensor Network**: Chorus32 devices act as distributed RSSI sensors
- **Configurable Receivers**: Each RX5808 module can be tuned via ASCII commands
- **Push-Based Updates**: Continuous RSSI streaming at configurable intervals (5-50ms)
- **Simple Protocol**: The Chorus32 ASCII text protocol makes integration straightforward

**RotorHazard's Role:**
- **Race Management**: Heats, classes, pilots, event coordination
- **Lap Detection**: Crossing detection from RSSI threshold analysis
- **Per-Pilot Calibration**: Dynamic enter-at/exit-at levels per pilot
- **Data Management**: Complete RSSI history, marshalling, exports, analytics
- **Web Interface**: Real-time race display, announcer view, LED control

### Division of Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│                        RotorHazard                          │
│  • Race control & timing                                    │
│  • Lap detection algorithm (from RSSI stream)               │
│  • Per-pilot threshold calibration                          │
│  • Data storage & marshalling                               │
│  • Web UI, LED, announcer features                          │
└────────────────────┬────────────────────────────────────────┘
                     │ ASCII Protocol (WiFi/Serial)
                     │ Commands: B/C/F, A, I, t
                     │ Responses: r (RSSI stream), t (time)
┌────────────────────┴────────────────────────────────────────┐
│                        Chorus32                             │
│  • RX5808 receiver control (band/channel)                   │
│  • ADC sampling (RSSI from 6 receivers)                     │
│  • Automatic RSSI push (every 5-50ms)                       │
│  • Time synchronization                                     │
│  • Per-node active/inactive control                         │
└─────────────────────────────────────────────────────────────┘
```

### Protocol Usage

This plugin uses a **minimal command set** from the Chorus32 protocol, focusing on sensor operation:

**Commands Sent to Chorus32:**
- `N` - Query receiver count (initialization only)
- `B{n}` - Set receiver band (when pilot assigned)
- `C{n}` - Set receiver channel (when pilot assigned)
- `A{0/1}` - Enable/disable receiver node
- `I{hex}` - Set RSSI push interval (connection setup)
- `t` - Request time for synchronization

**Responses Used:**
- `r{hex}` - RSSI value (continuous stream, 100-200Hz typical)
- `t{hex}` - Device time in milliseconds

**Commands NOT Used:**
- `T` (Threshold) - RotorHazard manages thresholds via calibration system
- `M` (Min lap time) - RotorHazard global setting
- `R` (Race mode) - Lap detection handled by RotorHazard
- `L` (Lap detected) - Ignored, RH detects from RSSI stream

### Why This Approach?

**1. Leverages Chorus32's Strengths:**
- Fast, lightweight RSSI sampling from ESP32
- Proven RX5808 receiver modules
- Flexible network connectivity (WiFi AP or client mode)
- Simple, debuggable ASCII protocol

**2. Adds Enterprise Race Features:**
- **Database-backed race management** with complete history
- **Advanced marshalling** - review every RSSI sample, not just peaks
- **Per-pilot calibration** - each pilot can have different threshold settings
- **Multi-device coordination** - up to 8 Chorus32 devices (48 nodes) synchronized
- **Professional race display** - web-based real-time leaderboard
- **Integration ecosystem** - LED control, announcer features, data exports

**3. Simplifies Chorus32 Firmware:**
- No complex lap detection logic needed in firmware
- No race state management required
- No database or web server needed
- Focus on what ESP32 does best: fast ADC sampling and networking

### Benefits to Chorus32 Ecosystem

**For Users:**
- **Lower cost scaling** - $30 Chorus32 devices vs $300+ commercial timers
- **Professional features** - enterprise race management with affordable hardware
- **Proven software** - RotorHazard is the most popular open-source race timing system
- **Community support** - large RotorHazard user base and active development

**For Developers:**
- **Firmware simplification** - delegate complex features to RotorHazard
- **Protocol validation** - real-world usage of your ASCII protocol
- **Feature expansion** - new capabilities without firmware changes
- **Ecosystem growth** - more users → more contributors → better hardware/firmware

**For the Community:**
- **Open source end-to-end** - both Chorus32 and RotorHazard are GPL-licensed
- **Interoperability** - your protocol enables third-party integrations
- **Knowledge sharing** - techniques developed here benefit both projects
- **Cost accessibility** - competitive racing without expensive proprietary hardware

### Technical Highlights

**Why RSSI Streaming Works:**
- ESP32 can sample all 6 ADCs and push updates every 5ms with minimal CPU load
- Network bandwidth is negligible: 6 nodes × 200Hz × 8 bytes = 9.6 KB/s
- RotorHazard's Python-based detection handles complex algorithms (LPF, hysteresis, auto-calibration)
- Full RSSI history enables post-race analysis impossible with on-device lap detection

**Why Automatic Frequency Configuration Matters:**
- Eliminates manual receiver tuning (major pain point in races)
- Supports dynamic heat changes (pilots can swap frequencies mid-event)
- Enables advanced features (split classes, practice mode auto-switching)
- Chorus32's band/channel commands make this possible with simple ASCII messages

### Development Considerations

**If you're a Chorus32 firmware developer:**

This integration demonstrates the value of the Chorus32 protocol's flexibility. Consider:

1. **RSSI timing accuracy** - Current millisecond timestamps are sufficient, but adding microsecond precision would enable even better analysis
2. **Protocol extensions** - The ASCII format makes adding new commands easy while maintaining backward compatibility
3. **Performance optimization** - Current RSSI push implementation handles 5ms intervals well; could potentially go faster
4. **Additional sensors** - Temperature, voltage monitoring already in the Chorus32 protocol - RotorHazard could display these

**The plugin is designed to be:**
- **Non-invasive** - doesn't require firmware changes
- **Forward compatible** - will work with protocol enhancements
- **Feedback channel** - real-world usage informs firmware priorities

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

### Frequency Configuration (Automatic)

**Node frequencies are automatically configured by RotorHazard** when you assign pilots to heats - no manual frequency setup needed!

#### How It Works

1. **Configure Pilot VTX Frequencies** in RotorHazard
   - Go to **Settings → Pilots**
   - Set each pilot's VTX band and channel (e.g., "R1" for Raceband Channel 1)
   - This is a one-time setup per pilot

2. **Assign Pilots to Heat Slots**
   - When creating a heat, assign pilots to slots (1-6 for single device, 1-12 for two devices, etc.)
   - RotorHazard knows which pilot is in which slot

3. **Automatic Node Configuration**
   - RotorHazard automatically maps: Heat Slot → Node → Chorus32 Device & Receiver
   - Plugin sends frequency commands to the correct Chorus32 receiver
   - Each receiver tunes to match its assigned pilot's VTX

#### Example: 12-Pilot Race with 2 Chorus32 Devices

```
Heat 1 Assignments:
  Slot 1: Alice (R1 - 5658 MHz) → Device 0, Node 0 → Chorus32 auto-tunes to R1
  Slot 2: Bob   (R3 - 5732 MHz) → Device 0, Node 1 → Chorus32 auto-tunes to R3
  Slot 3: Carol (F2 - 5760 MHz) → Device 0, Node 2 → Chorus32 auto-tunes to F2
  ...
  Slot 7: Greg  (R5 - 5806 MHz) → Device 1, Node 0 → Chorus32 auto-tunes to R5
  ...
```

#### Behind the Scenes

When you assign a pilot to a heat slot, RotorHazard:

1. Looks up pilot's VTX frequency from pilot database
2. Calculates which Chorus32 device and receiver (0-5) handles that slot
3. Calls plugin's `set_frequency()` method
4. Plugin converts band letter to Chorus32 band index:
   - 'R' → Raceband (0)
   - 'A' → Band A (1)
   - 'B' → Band B (2)
   - 'E' → Band E (3)
   - 'F' → Band F (4)
   - 'D' → Band D (5)
5. Plugin sends ASCII commands to Chorus32:
   - `R0B0\n` - Set node 0 to Raceband
   - `R0C0\n` - Set node 0 to channel 1

#### Supported Bands

- **Raceband** (R): 5658-5917 MHz (8 channels)
- **Band A**: 5865-5905 MHz (8 channels)
- **Band B**: 5733-5866 MHz (8 channels)
- **Band E**: 5705-5945 MHz (8 channels)
- **Band F**: 5740-5880 MHz (8 channels)
- **Band D**: 5362-5399 MHz (8 channels - Lowband)

#### Important Notes

- **No Manual Tuning**: You never manually set frequencies in the plugin - RotorHazard handles it all
- **Heat Changes**: Frequencies reconfigure automatically when you change heat assignments
- **Mix and Match**: Each pilot can be on any band/channel - no restrictions
- **Verification**: Check RotorHazard logs to confirm frequency commands were sent
- **Node Active**: Make sure nodes are marked "Active" in plugin settings to receive frequencies

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

1. **One-Time Setup**:
   - Configure pilot VTX frequencies in **Settings → Pilots** (e.g., "R1", "F4", etc.)
   - Connect Chorus32 devices in plugin settings
   - Mark nodes as "Active" in plugin settings

2. **Before Each Race**:
   - Assign pilots to heat slots - **Frequencies auto-configure!**
   - Calibrate thresholds using RotorHazard's Calibration feature (if needed)

3. **During Race**:
   - Chorus32 continuously pushes RSSI values (default: every 10ms)
   - Click **Stage Race** or **Start Race** in RotorHazard
   - RotorHazard detects laps from RSSI threshold crossings
   - Laps appear immediately in RotorHazard UI with peak RSSI data

4. **After Race**:
   - Click **Stop Race** - results saved to database
   - Review lap times and RSSI data in Marshalling

### Important Notes

- **Automatic Frequency Setup**: Node frequencies configure automatically when you assign pilots to heats - no manual tuning!
- **No Chorus32 Race Mode**: Chorus32 just pushes RSSI continuously, RotorHazard handles all lap detection
- **Threshold Calibration**: Use RotorHazard's Calibration feature (not plugin settings)
- **Per-Pilot Thresholds**: Each pilot can have different enter-at/exit-at levels
- **Minimum Lap Time**: Global RotorHazard setting (Settings → Event & Classes)
- **RSSI Interval**: Default 10ms is excellent for racing; use 5ms for maximum data capture

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
2. **Check pilot VTX frequency configured**: Go to Settings → Pilots and verify each pilot has a band/channel set (e.g., "R1")
3. **Check pilot assigned to heat**: Verify pilot is assigned to a heat slot (frequencies only auto-configure when assigned)
4. **Calibrate thresholds**: Use RotorHazard's Calibration feature to set enter-at/exit-at levels
5. **Check RSSI**: Verify RSSI updates are being received (check logs or RSSI graph)
6. **Check race started**: Ensure race was started (not just staged)
7. **Check frequency in logs**: Look for frequency command messages like "R0B0" in RotorHazard logs
8. **Check enter-at level**: Make sure enter-at level is lower than the pilot's signal strength

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

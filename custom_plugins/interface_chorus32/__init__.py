"""Chorus32 Provider Plugin for RotorHazard"""

import logging
import socket
import time
import gevent
import json

try:
    import serial
except ImportError:
    serial = None

from . import chorus32_protocol as chorus32

from eventmanager import Evt
from RHUI import UIField, UIFieldType, UIFieldSelectOption
from BaseHardwareInterface import BaseHardwareInterface
from Node import Node
from Database import LapSource

logger = logging.getLogger(__name__)

SERIAL_SCHEME = 'serial:'
SOCKET_SCHEME = 'socket://'
FILE_SCHEME = 'file:'
CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 0.25
WRITE_CHILL_TIME_S = 0.01
READ_POLL_RATE = 0.05  # 20Hz
DEFAULT_RSSI_INTERVAL_MS = 10  # 10ms RSSI push interval
DEFAULT_CHORUS32_PORT = 9000


def serial_url(port):
    """Convert serial port to URL format"""
    if port.startswith('/'):
        # Linux
        return f"file:{port}"
    else:
        # Windows
        return f"serial:{port}"


def socket_url(ip, port=DEFAULT_CHORUS32_PORT):
    """Convert IP/port to URL format"""
    return f"socket://{ip}:{port}/"


class SocketStream:
    """Socket stream wrapper for network connections"""
    def __init__(self, sock):
        self.socket = sock

    def write(self, data):
        self.socket.sendall(data)

    def read(self, max_size):
        return self.socket.recv(max_size)

    def close(self):
        self.socket.close()


class Chorus32Node(Node):
    """Represents a single Chorus32 receiver node (1 of 6 per device)"""
    def __init__(self, device, local_index):
        super().__init__()
        self.local_index = local_index  # 0-5
        self.device = device
        self.is_configured = False
        self.threshold = 0
        self.band_idx = None
        self.channel_idx = None
        self.is_active = True  # Chorus32-specific: per-node enable/disable
        self.pass_peak_rssi = 0  # Track peak RSSI for current lap


class Chorus32Device:
    """Manages a single Chorus32 device with 6 nodes"""
    def __init__(self, addr, device_name_str):
        self.name = device_name_str
        self.addr = addr
        self.stream_buffer = ""  # String buffer for ASCII protocol
        self.io_stream = None
        self.connected = False
        self.nodes = []

        # Time synchronization
        self._time_offset = 0  # device_ms - server_ms
        self._last_time_sync = 0

        # Configuration
        self.min_lap_time = None
        self.rssi_interval_ms = DEFAULT_RSSI_INTERVAL_MS

        # Create 6 nodes (not 8 like LapRF!)
        for index in range(6):
            node = Chorus32Node(self, index)
            node.api_valid_flag = True
            node.node_peak_rssi = 0
            node.node_nadir_rssi = 9999
            node.enter_at_level = 999
            node.exit_at_level = 999
            self.nodes.append(node)

        self._last_write_timestamp = 0

    @property
    def is_configured(self):
        """Check if all nodes are configured"""
        for node in self.nodes:
            if not node.is_configured:
                return False
        return True

    def connect(self):
        """Connect to Chorus32 device"""
        if not self.connected:
            try:
                self.io_stream = self._create_stream()
                self.connected = True
                return True
            except Exception as e:
                logger.warning(f"Unable to connect to Chorus32 at {self.name}: {e}")
                self.io_stream = None
                return False
        return None

    def _create_stream(self):
        """Create I/O stream for serial or socket connection"""
        if self.addr.startswith(SERIAL_SCHEME):
            port = self.addr[len(SERIAL_SCHEME):]
            if serial is None:
                raise ImportError("pyserial not installed")
            io_stream = serial.Serial(port=port, baudrate=115200, timeout=READ_TIMEOUT_S)
        elif self.addr.startswith(FILE_SCHEME):
            port = self.addr[len(FILE_SCHEME):]
            if serial is None:
                raise ImportError("pyserial not installed")
            io_stream = serial.Serial(port=port, baudrate=115200, timeout=READ_TIMEOUT_S)
        elif self.addr.startswith(SOCKET_SCHEME):
            # Strip trailing /
            end_pos = -1 if self.addr[-1] == '/' else len(self.addr)
            socket_addr = self.addr[len(SOCKET_SCHEME):end_pos]
            host_port = socket_addr.split(':')
            if len(host_port) == 1:
                host_port = (host_port[0], DEFAULT_CHORUS32_PORT)
            else:
                host_port = (host_port[0], int(host_port[1]))
            io_stream = SocketStream(socket.create_connection(host_port, timeout=CONNECT_TIMEOUT_S))
        else:
            raise ValueError(f"Unsupported address: {self.addr}")
        return io_stream

    def write(self, data):
        """Write ASCII string to device"""
        if self.connected:
            # Rate limiting
            chill_remaining_s = self._last_write_timestamp + WRITE_CHILL_TIME_S - time.monotonic()
            if chill_remaining_s > 0:
                gevent.sleep(chill_remaining_s)

            # Encode to bytes
            if isinstance(data, str):
                data = data.encode('utf-8')

            self.io_stream.write(data)
            self._last_write_timestamp = time.monotonic()

    def read(self):
        """Read ASCII data from device"""
        if self.connected:
            try:
                data = self.io_stream.read(512)
                if data:
                    return data.decode('utf-8', errors='ignore')
                return ""
            except TimeoutError:
                logger.info(f"Chorus32 device {self.name} timed out")
                self.close()
                raise
        return ""

    def close(self):
        """Close connection to device"""
        if self.connected:
            self.io_stream.close()
            self.io_stream = None
        self.connected = False
        self.close_callback()

    def request_time_sync(self):
        """Request device time for synchronization"""
        # Request time from node 0
        self.write(chorus32.Chorus32Encoder.encode_get_time(0))

    def calc_time_offset(self, device_time_ms):
        """Calculate offset between device and server time

        Args:
            device_time_ms: Device time in milliseconds
        """
        server_time_ms = time.monotonic() * 1000
        self._time_offset = device_time_ms - server_time_ms
        self._last_time_sync = time.monotonic()
        logger.debug(f"Chorus32 {self.name} time offset: {self._time_offset:.1f}ms")

    def server_timestamp_from_device(self, device_time_ms):
        """Convert device time to server timestamp

        Args:
            device_time_ms: Device time in milliseconds

        Returns:
            Server timestamp in seconds
        """
        return (device_time_ms - self._time_offset) / 1000.0

    def sync_callback(self):
        """Called when time sync completes"""
        pass

    def close_callback(self):
        """Called when device disconnects"""
        pass


class Chorus32Interface(BaseHardwareInterface):
    """Hardware interface for Chorus32 timing system"""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update_loop_enabled = False
        self.update_thread = None
        self.devices = kwargs.get('devices', [])

    @property
    def nodes(self):
        """Get all nodes from all devices"""
        all_nodes = []
        for device in self.devices:
            for node in device.nodes:
                all_nodes.append(node)
        return all_nodes

    @nodes.setter
    def nodes(self, value):
        pass

    def init_devices(self):
        """Initialize all devices"""
        for device in self.devices:
            device.connect()
            if device.connected:
                self.configure_device(device)

    def configure_device(self, device):
        """Query device configuration

        Args:
            device: Chorus32Device instance
        """
        try:
            # Get number of receivers
            device.write(chorus32.Chorus32Encoder.encode_get_num_receivers())
            gevent.sleep(0.1)

            # Query each node's configuration
            for node_idx in range(6):
                # These will be echoed back by the device
                # Note: Not all Chorus32 firmware versions support all get commands
                pass

            gevent.sleep(0.2)
            logger.info(f"Configured Chorus32 device {device.name}")
        except Exception as e:
            logger.warning(f"Failed to configure Chorus32 device {device.name}: {e}")

    def start(self):
        """Start the interface"""
        if self.update_thread is None:
            # Connect all devices
            for device in self.devices:
                device.connect()

            any_device_connected = False
            for device in self.devices:
                if device.connected:
                    any_device_connected = True
                    break

            if any_device_connected:
                self.update_thread = gevent.spawn(self.update_loop)

                # Configure devices and enable RSSI push
                for device in self.devices:
                    if device.connected:
                        self.configure_device(device)

                        # Enable RSSI push for all active nodes
                        for node_idx, node in enumerate(device.nodes):
                            if node.is_active:
                                device.write(
                                    chorus32.Chorus32Encoder.encode_set_rssi_interval(
                                        node_idx,
                                        device.rssi_interval_ms
                                    )
                                )

                        # Request time sync
                        device.request_time_sync()

                return True
            return False
        return None

    def stop(self):
        """Stop the interface"""
        self.log('Stopping Chorus32 background thread')
        self.update_loop_enabled = False

    def update_loop(self):
        """Main update loop - reads and processes messages"""
        self.log('Starting Chorus32 background thread')
        self.update_loop_enabled = True
        try:
            while self.update_loop_enabled:
                self._update()
                gevent.sleep(READ_POLL_RATE)
        except KeyboardInterrupt:
            logger.info("Update thread terminated by keyboard interrupt")
            raise
        self.log('Chorus32 background thread ended')
        self.update_thread = None
        for device in self.devices:
            device.close()

    def _update(self):
        """Read and process messages from all devices"""
        for device in self.devices:
            if not device.connected:
                continue

            try:
                data = device.read()
            except TimeoutError:
                self.handle_timeout(device)
                data = None

            if data:
                # Append to buffer
                device.stream_buffer += data

                # Process complete lines (newline-terminated)
                while '\n' in device.stream_buffer:
                    line, device.stream_buffer = device.stream_buffer.split('\n', 1)
                    message = chorus32.Chorus32Decoder.parse_message(line)
                    if message:
                        self._process_message(device, message)

    def _process_message(self, device, message):
        """Process a single parsed message

        Args:
            device: Chorus32Device instance
            message: Chorus32Message instance
        """
        cmd = message.command

        if cmd == chorus32.Chorus32Commands.RESPONSE_LAPTIME:  # 'L' - Lap detection
            lap_num, lap_time_ms = chorus32.Chorus32Decoder.decode_lap_message(message.data)
            if lap_num is not None and lap_time_ms is not None:
                node = device.nodes[message.node]
                # Convert device time to server timestamp
                server_timestamp = device.server_timestamp_from_device(lap_time_ms)

                # Record the lap with peak RSSI for marshalling
                if callable(self.pass_record_callback):
                    self.pass_record_callback(
                        node,
                        server_timestamp,
                        BaseHardwareInterface.LAP_SOURCE_REALTIME,
                        peak=node.pass_peak_rssi
                    )

                # Reset peak RSSI for next lap
                node.pass_peak_rssi = 0
                logger.info(f"Lap detected: Node {message.node}, Lap {lap_num}, Time {lap_time_ms}ms")

        elif cmd == chorus32.Chorus32Commands.GET_RSSI:  # 'r' - RSSI value
            rssi = chorus32.Chorus32Decoder.decode_hex_value(message.data, 4)
            if rssi is not None and message.node is not None:
                node = device.nodes[message.node]
                node.current_rssi = rssi

                # Track peak RSSI for lap detection
                if rssi > node.pass_peak_rssi:
                    node.pass_peak_rssi = rssi
                if rssi > node.node_peak_rssi:
                    node.node_peak_rssi = rssi
                if rssi < node.node_nadir_rssi:
                    node.node_nadir_rssi = rssi

        elif cmd == chorus32.Chorus32Commands.THRESHOLD:  # 'T' - Threshold
            threshold = chorus32.Chorus32Decoder.decode_hex_value(message.data, 4)
            if threshold is not None and message.node is not None:
                node = device.nodes[message.node]
                node.threshold = threshold
                node.is_configured = True

        elif cmd == chorus32.Chorus32Commands.BAND:  # 'B' - Band
            band = chorus32.Chorus32Decoder.decode_hex_value(message.data, 1)
            if band is not None and message.node is not None:
                node = device.nodes[message.node]
                node.band_idx = band

        elif cmd == chorus32.Chorus32Commands.CHANNEL:  # 'C' - Channel
            channel = chorus32.Chorus32Decoder.decode_hex_value(message.data, 1)
            if channel is not None and message.node is not None:
                node = device.nodes[message.node]
                node.channel_idx = channel

        elif cmd == chorus32.Chorus32Commands.FREQUENCY:  # 'F' - Frequency
            freq = chorus32.Chorus32Decoder.decode_hex_value(message.data, 4)
            if freq is not None and message.node is not None:
                node = device.nodes[message.node]
                node.frequency = freq

        elif cmd == chorus32.Chorus32Commands.MIN_LAP_TIME:  # 'M' - Min lap time
            min_lap = chorus32.Chorus32Decoder.decode_hex_value(message.data, 2)
            if min_lap is not None:
                device.min_lap_time = min_lap * 1000  # Convert seconds to ms

        elif cmd == chorus32.Chorus32Commands.GET_TIME:  # 't' - Time
            device_time = chorus32.Chorus32Decoder.decode_hex_value(message.data, 8)
            if device_time is not None:
                device.calc_time_offset(device_time)

        elif cmd == chorus32.Chorus32Commands.NUM_RECEIVERS:  # 'N' - Number of receivers
            if message.data:
                num_receivers = int(message.data)
                logger.info(f"Chorus32 device {device.name} has {num_receivers} receivers")

        elif cmd == chorus32.Chorus32Commands.PILOT_ACTIVE:  # 'A' - Active status
            active = chorus32.Chorus32Decoder.decode_hex_value(message.data, 1)
            if active is not None and message.node is not None:
                node = device.nodes[message.node]
                node.is_active = (active == 1)

    def handle_timeout(self, device):
        """Handle device timeout"""
        logger.warning(f"Chorus32 device {device.name} timeout")

    def set_frequency(self, node_index, frequency, band=0, channel=0):
        """Set node frequency

        Args:
            node_index: Global node index
            frequency: Frequency in MHz
            band: Band index or letter (R, A, B, E, F, D)
            channel: Channel index (0-7)
        """
        # Find device and local node index
        device_idx = node_index // 6
        local_idx = node_index % 6

        if device_idx < len(self.devices):
            device = self.devices[device_idx]
            node = device.nodes[local_idx]

            # Map band letter to index
            if isinstance(band, str):
                band_idx = chorus32.Chorus32Bands.BAND_MAP.get(band.upper(), 0)
            else:
                band_idx = band

            device.write(chorus32.Chorus32Encoder.encode_set_band(local_idx, band_idx))
            device.write(chorus32.Chorus32Encoder.encode_set_channel(local_idx, channel))

            node.is_configured = False

    def set_threshold(self, device_idx, node_index, threshold):
        """Set node threshold

        Args:
            device_idx: Device index
            node_index: Local node index (0-5)
            threshold: Threshold value (0-3000)
        """
        if 0 <= threshold <= 3000 and device_idx < len(self.devices):
            device = self.devices[device_idx]
            device.write(chorus32.Chorus32Encoder.encode_set_threshold(node_index, threshold))

    def set_min_lap(self, device_idx, min_lap_ms):
        """Set minimum lap time

        Args:
            device_idx: Device index
            min_lap_ms: Minimum lap time in milliseconds
        """
        min_lap_sec = min_lap_ms // 1000
        if 0 <= min_lap_sec <= 120 and device_idx < len(self.devices):
            device = self.devices[device_idx]
            # Use wildcard to set all nodes
            device.write(chorus32.Chorus32Encoder.encode_set_min_lap_time('*', min_lap_sec))

    def set_rssi_interval(self, device_idx, interval_ms):
        """Set RSSI push interval

        Args:
            device_idx: Device index
            interval_ms: Interval in milliseconds (0 = off, 5-50ms recommended)
        """
        if device_idx < len(self.devices):
            device = self.devices[device_idx]
            device.rssi_interval_ms = interval_ms

            # Update all active nodes
            for node_idx, node in enumerate(device.nodes):
                if node.is_active:
                    device.write(
                        chorus32.Chorus32Encoder.encode_set_rssi_interval(node_idx, interval_ms)
                    )

    def set_node_active(self, device_idx, node_index, active):
        """Set node active/inactive

        Args:
            device_idx: Device index
            node_index: Local node index (0-5)
            active: True to activate, False to deactivate
        """
        if device_idx < len(self.devices):
            device = self.devices[device_idx]
            node = device.nodes[node_index]

            device.write(chorus32.Chorus32Encoder.encode_set_pilot_active(node_index, active))
            node.is_active = active

            # Enable/disable RSSI push accordingly
            if active:
                device.write(
                    chorus32.Chorus32Encoder.encode_set_rssi_interval(
                        node_index,
                        device.rssi_interval_ms
                    )
                )
            else:
                device.write(chorus32.Chorus32Encoder.encode_set_rssi_interval(node_index, 0))

    def set_state(self, state):
        """Set race state

        Args:
            state: Race state (START_RACE or other)
        """
        # Map to Chorus32 race mode
        if state == 1:  # Racing
            race_mode = chorus32.Chorus32RaceModes.ABSOLUTE_TIMING  # Mode 2
        else:
            race_mode = chorus32.Chorus32RaceModes.OFF  # Mode 0

        for device in self.devices:
            if device.connected:
                # Use wildcard to set all nodes
                device.write(chorus32.Chorus32Encoder.encode_set_race_mode('*', race_mode))

    # Stub methods required by BaseHardwareInterface
    def set_enter_at_level(self, node_index, level):
        pass

    def set_exit_at_level(self, node_index, level):
        pass

    def force_end_crossing(self, node_index):
        pass


class Chorus32Provider:
    """Main plugin class for Chorus32 integration"""

    def __init__(self, rhapi):
        self._rhapi = rhapi
        self.startup_device_total = 0
        self.devices = []
        self.interface = None

        # Register events
        rhapi.events.on(Evt.STARTUP, self.startup)
        rhapi.events.on(Evt.SHUTDOWN, self.shutdown)
        rhapi.events.on(Evt.RACE_STAGE, self.race_stage)
        rhapi.events.on(Evt.RACE_STOP, self.race_stop)
        rhapi.events.on(Evt.LAPS_CLEAR, self.laps_clear)

        # Register config section
        rhapi.config.register_section('Chorus32')

        # Register main panel
        rhapi.ui.register_panel('provider_chorus32', 'Chorus32 General Setup', 'settings')

        # Register device count field
        rhapi.fields.register_option(
            field=UIField(
                name='device_count',
                label="Device Count",
                field_type=UIFieldType.BASIC_INT,
                value=1,
                desc="Number of Chorus32 devices (requires restart)",
                persistent_section="Chorus32",
                persistent_restart=True
            ),
            panel='provider_chorus32'
        )

        self.process_config()
        self.init_vars()
        self.init_interface()
        rhapi.interface.add(self.interface)

        # Register per-device UI fields
        if len(self.devices):
            for dev_idx, device in enumerate(self.devices):
                self.register_device_ui(dev_idx)

            # Register combined controls
            self.register_combined_controls()

    def process_config(self):
        """Load configuration from persistent storage"""
        device_count = self._rhapi.config.get_item_int('Chorus32', 'device_count', 1)
        self.startup_device_total = device_count

        addresses = self.load_addresses()

        # Create devices
        self.devices = []
        for idx in range(device_count):
            addr = addresses[idx] if idx < len(addresses) else f"192.168.4.{idx + 1}"
            addr = self._normalize_addr(addr)
            device = Chorus32Device(addr, f"Chorus32 {idx + 1}")
            device.sync_callback = self.sync_callback
            device.close_callback = self.close_callback
            self.devices.append(device)

    def load_addresses(self):
        """Load device addresses from config"""
        addresses_json = self._rhapi.config.get_item('Chorus32', 'address')
        if addresses_json:
            try:
                return json.loads(addresses_json)
            except:
                pass
        return []

    def save_addresses(self):
        """Save device addresses to config"""
        addresses = [device.addr for device in self.devices]
        self._rhapi.config.set_item('Chorus32', 'address', json.dumps(addresses))

    def _normalize_addr(self, addr):
        """Normalize address to URL format"""
        if not addr:
            return f"socket://192.168.4.1:{DEFAULT_CHORUS32_PORT}/"

        if addr.startswith('serial:') or addr.startswith('file:') or addr.startswith('socket://'):
            return addr

        if addr.startswith('/dev/') or addr.startswith('COM'):
            return serial_url(addr)

        # Assume IP address
        if ':' in addr:
            return f"socket://{addr}/"
        else:
            return f"socket://{addr}:{DEFAULT_CHORUS32_PORT}/"

    def init_vars(self):
        """Initialize internal variables"""
        # Arrays for UI field values
        self.thresholds = [[0] * 6 for _ in range(len(self.devices))]
        self.min_laps = [0] * len(self.devices)
        self.rssi_intervals = [DEFAULT_RSSI_INTERVAL_MS] * len(self.devices)

    def init_interface(self):
        """Initialize the hardware interface"""
        self.interface = Chorus32Interface(devices=self.devices)

    def register_device_ui(self, dev_idx):
        """Register UI fields for a device"""
        device = self.devices[dev_idx]

        # Device detail panel
        self._rhapi.ui.register_panel(
            f'provider_chorus32_detail_{dev_idx}',
            f'Chorus32 Device {dev_idx + 1}',
            'settings'
        )

        # Device address field
        self._rhapi.fields.register_function_binding(
            field=UIField(
                name=f'chorus32_address_{dev_idx}',
                label="Device Address",
                field_type=UIFieldType.TEXT,
                value=device.addr,
                desc="IP address, serial port, or URL (socket://IP:9000/ or serial:/dev/ttyUSB0)"
            ),
            getter_fn=self.get_device_address,
            setter_fn=self.set_device_address,
            args={'device': dev_idx},
            panel='provider_chorus32'
        )

        # Min lap time field
        self._rhapi.fields.register_function_binding(
            field=UIField(
                name=f'chorus32_min_lap_{dev_idx}',
                label="Minimum Lap Time (seconds)",
                field_type=UIFieldType.BASIC_INT,
                desc="Minimum lap time in seconds (0-120)"
            ),
            getter_fn=self.get_min_lap,
            setter_fn=self.set_min_lap,
            args={'device': dev_idx},
            panel=f'provider_chorus32_detail_{dev_idx}'
        )

        # RSSI push interval field
        self._rhapi.fields.register_function_binding(
            field=UIField(
                name=f'chorus32_rssi_interval_{dev_idx}',
                label="RSSI Push Interval (ms)",
                field_type=UIFieldType.BASIC_INT,
                value=DEFAULT_RSSI_INTERVAL_MS,
                desc="RSSI update interval in milliseconds (5-50ms recommended, 0=off)"
            ),
            getter_fn=self.get_rssi_interval,
            setter_fn=self.set_rssi_interval,
            args={'device': dev_idx},
            panel=f'provider_chorus32_detail_{dev_idx}'
        )

        # Per-node threshold and active fields (6 nodes)
        for node_idx in range(6):
            # Threshold field
            self._rhapi.fields.register_function_binding(
                field=UIField(
                    name=f'chorus32_{dev_idx}_threshold_{node_idx}',
                    label=f"Node {node_idx + 1} Threshold",
                    field_type=UIFieldType.BASIC_INT,
                    desc="Threshold value (0-3000, typical: 800)"
                ),
                getter_fn=self.get_threshold,
                setter_fn=self.set_threshold,
                args={'device': dev_idx, 'index': node_idx},
                panel=f'provider_chorus32_detail_{dev_idx}'
            )

            # Active checkbox
            self._rhapi.fields.register_function_binding(
                field=UIField(
                    name=f'chorus32_{dev_idx}_active_{node_idx}',
                    label=f"Node {node_idx + 1} Active",
                    field_type=UIFieldType.CHECKBOX,
                    desc="Enable/disable this receiver node"
                ),
                getter_fn=self.get_node_active,
                setter_fn=self.set_node_active,
                args={'device': dev_idx, 'index': node_idx},
                panel=f'provider_chorus32_detail_{dev_idx}'
            )

    def register_combined_controls(self):
        """Register combined control fields"""
        # Set all thresholds
        self._rhapi.fields.register_function_binding(
            field=UIField(
                name='chorus32_combined_threshold',
                label="Set All Thresholds",
                field_type=UIFieldType.BASIC_INT,
                desc="Set threshold for all nodes on all devices (0-3000)"
            ),
            getter_fn=self.get_combined_threshold,
            setter_fn=self.set_combined_threshold,
            panel='provider_chorus32'
        )

        # Set all min lap times
        self._rhapi.fields.register_function_binding(
            field=UIField(
                name='chorus32_combined_min_lap',
                label="Set All Min Lap Times",
                field_type=UIFieldType.BASIC_INT,
                desc="Set minimum lap time for all devices (seconds)"
            ),
            getter_fn=self.get_combined_min_lap,
            setter_fn=self.set_combined_min_lap,
            panel='provider_chorus32'
        )

    # Getter/setter functions for UI fields
    def get_device_address(self, args):
        return self.devices[args['device']].addr

    def set_device_address(self, value, args):
        device_idx = args['device']
        self.devices[device_idx].addr = self._normalize_addr(value)
        self.save_addresses()

    def get_threshold(self, args):
        device = self.devices[args['device']]
        node = device.nodes[args['index']]
        return node.threshold

    def set_threshold(self, value, args):
        if self.interface:
            self.interface.set_threshold(args['device'], args['index'], int(value))

    def get_min_lap(self, args):
        device = self.devices[args['device']]
        return (device.min_lap_time // 1000) if device.min_lap_time else 0

    def set_min_lap(self, value, args):
        if self.interface:
            self.interface.set_min_lap(args['device'], int(value) * 1000)

    def get_rssi_interval(self, args):
        device = self.devices[args['device']]
        return device.rssi_interval_ms

    def set_rssi_interval(self, value, args):
        if self.interface:
            self.interface.set_rssi_interval(args['device'], int(value))

    def get_node_active(self, args):
        device = self.devices[args['device']]
        node = device.nodes[args['index']]
        return node.is_active

    def set_node_active(self, value, args):
        if self.interface:
            self.interface.set_node_active(args['device'], args['index'], bool(value))

    def get_combined_threshold(self, args):
        return ""

    def set_combined_threshold(self, value, args):
        threshold = int(value)
        if self.interface:
            for dev_idx in range(len(self.devices)):
                for node_idx in range(6):
                    self.interface.set_threshold(dev_idx, node_idx, threshold)

    def get_combined_min_lap(self, args):
        return ""

    def set_combined_min_lap(self, value, args):
        min_lap_ms = int(value) * 1000
        if self.interface:
            for dev_idx in range(len(self.devices)):
                self.interface.set_min_lap(dev_idx, min_lap_ms)

    # Event handlers
    def startup(self, args):
        """Register UI buttons on startup"""
        self._rhapi.ui.register_quickbutton(
            panel='provider_chorus32',
            name="chorus32-btn-connect",
            label="Connect",
            function=self.ui_enable
        )
        self._rhapi.ui.register_quickbutton(
            panel='provider_chorus32',
            name="chorus32-btn-disconnect",
            label="Disconnect",
            function=self.ui_disable
        )

    def shutdown(self, args):
        """Stop interface on shutdown"""
        if self.interface:
            self.interface.stop()

    def race_stage(self, args):
        """Start race"""
        if self.interface:
            self.interface.set_state(1)  # Racing

    def race_stop(self, args):
        """Stop race"""
        if self.interface:
            self.interface.set_state(0)  # Stopped

    def laps_clear(self, args):
        """Clear laps"""
        if self.interface:
            self.interface.set_state(0)  # Stopped

    def ui_enable(self, args):
        """Connect button handler"""
        if self.interface:
            result = self.interface.start()
            if result:
                self._rhapi.ui.message_notify("Chorus32 devices connected")
            else:
                self._rhapi.ui.message_alert("Failed to connect to Chorus32 devices")

    def ui_disable(self, args):
        """Disconnect button handler"""
        if self.interface:
            self.interface.stop()
            self._rhapi.ui.message_notify("Chorus32 devices disconnected")

    def sync_callback(self):
        """Called when device time sync completes"""
        pass

    def close_callback(self):
        """Called when device disconnects"""
        pass


def initialize(rhapi):
    """Plugin entry point"""
    Chorus32Provider(rhapi)

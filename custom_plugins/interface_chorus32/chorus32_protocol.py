"""
Chorus32 Protocol Implementation

ASCII text-based protocol for Chorus32 lap timing hardware.
Based on the Chorus32 firmware protocol specification.
"""

from dataclasses import dataclass
from typing import Optional


class Chorus32Commands:
    """Command constants for Chorus32 protocol"""
    # Get/Set commands
    NUM_RECEIVERS = 'N'
    BAND = 'B'
    CHANNEL = 'C'
    FREQUENCY = 'F'
    THRESHOLD = 'T'
    MIN_LAP_TIME = 'M'
    RACE_MODE = 'R'
    PILOT_ACTIVE = 'A'
    RSSI_MON_INTERVAL = 'I'
    SOUND = 'S'
    WAIT_FIRST_LAP = '1'

    # Get-only commands
    GET_RSSI = 'r'
    GET_TIME = 't'
    GET_VOLTAGE = 'v'
    GET_API_VERSION = '#'
    GET_ALL_DATA = 'a'
    GET_IS_CONFIGURED = 'y'
    PING = '%'
    GET_LAPTIMES = 'l'

    # Response-only commands
    RESPONSE_LAPTIME = 'L'
    RESPONSE_END_SEQUENCE = 'x'

    # Wildcard indicator
    WILDCARD = '*'


class Chorus32Bands:
    """Band index mapping"""
    RACEBAND = 0
    BAND_A = 1
    BAND_B = 2
    BAND_E = 3
    BAND_F = 4
    BAND_D = 5
    CONNEX = 6
    CONNEX2 = 7

    # Map from RotorHazard band letters to Chorus32 indices
    BAND_MAP = {
        'R': RACEBAND,
        'A': BAND_A,
        'B': BAND_B,
        'E': BAND_E,
        'F': BAND_F,
        'D': BAND_D,
    }


class Chorus32RaceModes:
    """Race mode constants"""
    OFF = 0
    RELATIVE_TO_LAST_LAP = 1
    ABSOLUTE_TIMING = 2


@dataclass
class Chorus32Message:
    """Parsed Chorus32 message"""
    node: Optional[int]  # None for global commands
    command: str
    data: Optional[str] = None
    is_response: bool = False

    def __repr__(self):
        prefix = "S" if self.is_response else "R"
        node_str = str(self.node) if self.node is not None else ""
        data_str = self.data if self.data else ""
        return f"{prefix}{node_str}{self.command}{data_str}"


class Chorus32Encoder:
    """Encode commands to Chorus32 ASCII format"""

    @staticmethod
    def encode_get_num_receivers():
        """Get number of receivers: N0\n"""
        return "N0\n"

    @staticmethod
    def encode_set_band(node, band):
        """Set band: R{node}B{band}\n

        Args:
            node: Node index (0-5) or '*' for all
            band: Band index (0-7)
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        return f"R{node_char}B{hex_digit(band)}\n"

    @staticmethod
    def encode_set_channel(node, channel):
        """Set channel: R{node}C{channel}\n

        Args:
            node: Node index (0-5) or '*' for all
            channel: Channel index (0-7)
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        return f"R{node_char}C{hex_digit(channel)}\n"

    @staticmethod
    def encode_set_frequency(node, frequency):
        """Set frequency: R{node}F{freq}\n

        Args:
            node: Node index (0-5) or '*' for all
            frequency: Frequency in MHz (4 hex digits)
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        freq_hex = format(frequency, '04X')
        return f"R{node_char}F{freq_hex}\n"

    @staticmethod
    def encode_set_threshold(node, threshold):
        """Set threshold: R{node}T{threshold}\n

        Args:
            node: Node index (0-5) or '*' for all
            threshold: Threshold value 0-3000 (4 hex digits)
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        threshold_hex = format(threshold, '04X')
        return f"R{node_char}T{threshold_hex}\n"

    @staticmethod
    def encode_set_min_lap_time(node, seconds):
        """Set minimum lap time: R{node}M{seconds}\n

        Args:
            node: Node index (0-5) or '*' for all
            seconds: Time in seconds 0-255 (2 hex digits)
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        seconds_hex = format(seconds, '02X')
        return f"R{node_char}M{seconds_hex}\n"

    @staticmethod
    def encode_set_race_mode(node, mode):
        """Set race mode: R{node}R{mode}\n

        Args:
            node: Node index (0-5) or '*' for all
            mode: 0=off, 1=relative to last, 2=absolute timing
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        return f"R{node_char}R{hex_digit(mode)}\n"

    @staticmethod
    def encode_set_pilot_active(node, active):
        """Set pilot active/inactive: R{node}A{active}\n

        Args:
            node: Node index (0-5) or '*' for all
            active: True/False or 1/0
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        active_val = 1 if active else 0
        return f"R{node_char}A{hex_digit(active_val)}\n"

    @staticmethod
    def encode_set_rssi_interval(node, interval_ms):
        """Set RSSI monitor interval: R{node}I{interval}\n

        Args:
            node: Node index (0-5) or '*' for all
            interval_ms: Interval in milliseconds (4 hex digits), 0=off
        """
        node_char = hex_digit(node) if isinstance(node, int) else node
        interval_hex = format(interval_ms, '04X')
        return f"R{node_char}I{interval_hex}\n"

    @staticmethod
    def encode_get_rssi(node):
        """Get RSSI value: R{node}r\n"""
        return f"R{hex_digit(node)}r\n"

    @staticmethod
    def encode_get_time(node):
        """Get device time: R{node}t\n"""
        return f"R{hex_digit(node)}t\n"

    @staticmethod
    def encode_get_voltage(node):
        """Get voltage: R{node}v\n"""
        return f"R{hex_digit(node)}v\n"

    @staticmethod
    def encode_ping(node):
        """Send ping: R{node}%\n"""
        return f"R{hex_digit(node)}%\n"


class Chorus32Decoder:
    """Decode ASCII messages from Chorus32"""

    @staticmethod
    def parse_message(line):
        """Parse a single newline-terminated message

        Format examples:
            "N8\n" - 8 nodes available
            "S0L0100000064\n" - Lap on node 0, lap#1, time 100ms
            "S0r0ABC\n" - RSSI from node 0
            "S0T03E8\n" - Threshold response: 1000

        Returns:
            Chorus32Message or None if invalid
        """
        if not line or len(line) < 2:
            return None

        line = line.strip()
        if not line:
            return None

        # Special case: number of receivers (N{count})
        if line[0] == 'N':
            try:
                count = int(line[1:], 16) if len(line) > 1 else 0
                return Chorus32Message(
                    node=None,
                    command=Chorus32Commands.NUM_RECEIVERS,
                    data=str(count)
                )
            except ValueError:
                return None

        # Standard response format: S{node}{command}{data}
        if line[0] == 'S':
            if len(line) < 3:
                return None
            try:
                node = int(line[1], 16)
                command = line[2]
                data = line[3:] if len(line) > 3 else None

                msg = Chorus32Message(
                    node=node,
                    command=command,
                    data=data,
                    is_response=True
                )
                return msg
            except (ValueError, IndexError):
                return None

        return None

    @staticmethod
    def decode_lap_message(data):
        """Decode lap data: {LAP_HEX}{TIME_HEX}

        Example: "0100000064" = lap 1, time 100ms

        Returns:
            (lap_num, lap_time_ms) or (None, None) if invalid
        """
        if not data or len(data) < 10:
            return None, None

        try:
            lap_num = int(data[0:2], 16)
            lap_time_ms = int(data[2:10], 16)
            return lap_num, lap_time_ms
        except ValueError:
            return None, None

    @staticmethod
    def decode_hex_value(data, num_digits=4):
        """Decode hex value from string

        Args:
            data: Hex string
            num_digits: Expected number of hex digits

        Returns:
            Integer value or None if invalid
        """
        if not data or len(data) < num_digits:
            return None

        try:
            return int(data[:num_digits], 16)
        except ValueError:
            return None


def hex_digit(value):
    """Convert value to single hex digit (0-F)

    Args:
        value: Integer 0-15

    Returns:
        Single hex character
    """
    return format(value & 0xF, 'X')


def is_valid_hex(s, expected_len):
    """Validate hex string

    Args:
        s: String to validate
        expected_len: Expected length

    Returns:
        True if valid hex string of expected length
    """
    if not s or len(s) < expected_len:
        return False
    try:
        int(s[:expected_len], 16)
        return True
    except ValueError:
        return False

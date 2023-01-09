from dataclasses import dataclass

from serial import Serial, PARITY_NONE, STOPBITS_ONE, EIGHTBITS
from serial.threaded import ReaderThread, FramedPacket

# SERIAL_PORT = "/dev/TTYS3"
SERIAL_PORT = "COM4"


@dataclass
class NHSProtocol:
    rms_in_volts: int
    battery_volts: int
    consumption_percent: int
    min_rms_in_volts: int
    max_rms_in_volts: int
    rms_out_volts: int
    temp_celsius: int
    charger_amperes: float
    battery_on: bool
    low_battery: bool
    network_down: bool
    network_down_fast: bool
    rms_in_220: bool
    rms_out_220: bool
    bypass_on: bool
    charging: bool


class NHSSerialReader(FramedPacket):
    LENGTH = 19
    START = b'\xff'
    STOP = b'\xfe'

    def handle_packet(self, packet: bytearray):
        if self._is_packet_incomplete(packet):
            return

        status_raw = format(packet[16], '08b')
        status_raw = [int(item) for item in status_raw]
        return NHSProtocol(
            rms_in_volts=packet[2] + packet[3],
            battery_volts=packet[4] + packet[5],
            consumption_percent=packet[6],
            min_rms_in_volts=packet[7] + packet[8],
            max_rms_in_volts=packet[9] + packet[10],
            rms_out_volts=packet[11] + packet[12],
            temp_celsius=packet[13] + packet[14],
            charger_amperes=packet[15] * 750 / 25,
            battery_on=bool(status_raw[7]),
            low_battery=bool(status_raw[6]),
            network_down=bool(status_raw[5]),
            network_down_fast=bool(status_raw[4]),
            rms_in_220=bool(status_raw[3]),
            rms_out_220=bool(status_raw[2]),
            bypass_on=bool(status_raw[1]),
            charging=bool(status_raw[0])
        )

    def _is_packet_incomplete(self, packet: bytearray):
        return len(packet) != self.LENGTH


def main():
    listener = Serial(port=SERIAL_PORT, baudrate=2400, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE,
                      xonxoff=False, rtscts=False, dsrdtr=False)
    reader = ReaderThread(listener, NHSSerialReader)
    reader.run()


if __name__ == '__main__':
    main()

from __future__ import annotations

from serial import Serial, PARITY_NONE, STOPBITS_ONE, EIGHTBITS
from serial.threaded import ReaderThread, FramedPacket

from nhs import NHSProtocol


class NHSSerialListener:
    def __init__(self, *, callback, port='/dev/TTYS0', baud_rate=2400, byte_size=EIGHTBITS, parity=PARITY_NONE,
                 stop_bits=STOPBITS_ONE, xonxoff=False, rtscts=False, dsrdtr=False):
        listener = Serial(port=port, baudrate=baud_rate, bytesize=byte_size, parity=parity, stopbits=stop_bits,
                          xonxoff=xonxoff, rtscts=rtscts, dsrdtr=dsrdtr)
        self._reader = ReaderThread(listener, _NHSSerialReader.get_factory(callback=callback))

    def start(self) -> None:
        self._reader.run()


class _NHSSerialReader(FramedPacket):
    LENGTH = 19
    START = b'\xff'
    STOP = b'\xfe'

    def __init__(self, *, callback):
        super().__init__()
        self._callback = callback

    def handle_packet(self, packet: bytearray) -> None:
        if self._is_packet_incomplete(packet=packet):
            return

        status_raw = format(packet[16], '08b')
        status_raw = [int(item) for item in status_raw]
        self._callback(
            NHSProtocol(
                rms_in_volts=packet[2] + packet[3],
                battery_volts=packet[4] + packet[5],
                load_percent=packet[6],
                min_rms_in_volts=packet[7] + packet[8],
                max_rms_in_volts=packet[9] + packet[10],
                rms_out_volts=packet[11] + packet[12],
                temp_celsius=packet[13] + packet[14],
                charger_amperes=packet[15] * 750 / 25,
                battery_on=bool(status_raw[7]),
                low_battery=bool(status_raw[6]),
                grid_down=bool(status_raw[5]),
                grid_short_outage=bool(status_raw[4]),
                rms_in_220=bool(status_raw[3]),
                rms_out_220=bool(status_raw[2]),
                bypass_on=bool(status_raw[1]),
                charging=bool(status_raw[0])
            )
        )

    def _is_packet_incomplete(self, *, packet: bytearray) -> bool:
        return len(packet) != self.LENGTH

    @staticmethod
    def get_factory(*, callback):
        def func():
            return _NHSSerialReader(callback=callback)

        return func

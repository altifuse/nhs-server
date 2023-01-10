from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NHSProtocol:
    rms_in_volts: int
    battery_volts: int
    load_percent: int
    min_rms_in_volts: int
    max_rms_in_volts: int
    rms_out_volts: int
    temp_celsius: int
    charger_amperes: float
    battery_on: int
    low_battery: int
    grid_down: int
    grid_short_outage: int
    rms_in_220: int
    rms_out_220: int
    bypass_on: int
    charging: int

    def __eq__(self, other: NHSProtocol) -> bool:
        return not other or self.grid_down == other.grid_down

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
    battery_on: bool
    low_battery: bool
    grid_down: bool
    grid_short_outage: bool
    rms_in_220: bool
    rms_out_220: bool
    bypass_on: bool
    charging: bool

    def __eq__(self, other: NHSProtocol) -> bool:
        return not other or self.grid_down == other.grid_down

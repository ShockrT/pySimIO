"""Core simulation components for pySIMIO.

Every component implements a small, deterministic API:
    update(dt: float) -> None
    current_value() -> float

Input wiring is performed externally by the simulation orchestrator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
import random
from typing import Callable


class SimComponent(ABC):
    """Common interface for all simulation components."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def update(self, dt: float) -> None:
        """Advance component state by ``dt`` seconds."""

    @abstractmethod
    def current_value(self) -> float:
        """Return the component's primary process value."""


class FirstOrderTargetComponent(SimComponent):
    """Base for components that move toward a supplied target."""

    def __init__(self, name: str, *, tau: float, initial: float) -> None:
        super().__init__(name)
        self.tau = max(float(tau), 1e-6)
        self._target = float(initial)
        self._value = float(initial)

    def set_target(self, target: float) -> None:
        self._target = float(target)

    def update(self, dt: float) -> None:
        dt = max(float(dt), 0.0)
        alpha = min(1.0, dt / self.tau)
        self._value += (self._target - self._value) * alpha

    def current_value(self) -> float:
        return float(self._value)


class Sensor(SimComponent):
    """Holding or mirrored sensor with optional noise and sample lag."""

    def __init__(
        self,
        name: str,
        source_getter: Callable[[], float] | None = None,
        *,
        noise_std: float = 0.0,
        lag_samples: int = 0,
        initial: float = 0.0,
    ) -> None:
        super().__init__(name)
        self._source_getter = source_getter
        self._noise_std = max(float(noise_std), 0.0)
        self._history: deque[float] = deque(maxlen=max(int(lag_samples), 0) + 1)
        self._lag_samples = max(int(lag_samples), 0)
        self._value = float(initial)

    def set_source(self, getter: Callable[[], float] | None) -> None:
        self._source_getter = getter
        self._history.clear()

    def write(self, value: float) -> None:
        self._value = float(value)

    def read(self) -> float:
        return self.current_value()

    def update(self, dt: float) -> None:
        del dt
        if self._source_getter is None:
            return
        value = float(self._source_getter())
        if self._noise_std:
            value += random.gauss(0.0, self._noise_std)
        if self._lag_samples:
            self._history.append(value)
            if len(self._history) <= self._lag_samples:
                return
            value = self._history[0]
        self._value = value

    def current_value(self) -> float:
        return float(self._value)


class FlowComponent(FirstOrderTargetComponent):
    """First-order flow response toward a target flow value."""


class PressureComponent(FirstOrderTargetComponent):
    """First-order pressure response toward a target pressure value."""


class TemperatureComponent(FirstOrderTargetComponent):
    """First-order temperature response toward a target temperature value."""


class LevelComponent(SimComponent):
    """Tank level integrator using cubic metres and cubic metres per second internally."""

    _M_PER_FT = 0.3048
    _M_PER_IN = 0.0254

    def __init__(
        self,
        name: str,
        *,
        area_m2: float,
        height_m: float,
        level_unit: str = "percent",
        initial_output: float | None = None,
        gain: float = 1.0,
    ) -> None:
        super().__init__(name)
        if area_m2 <= 0.0:
            raise ValueError("Level area must be greater than zero")
        if height_m <= 0.0:
            raise ValueError("Level height must be greater than zero")
        self.area_m2 = float(area_m2)
        self.height_m = float(height_m)
        self.capacity_m3 = self.area_m2 * self.height_m
        self.level_unit = (level_unit or "percent").lower()
        if self.level_unit not in {"percent", "m", "ft", "in"}:
            raise ValueError(f"Unsupported level unit: {level_unit}")
        self.gain = float(gain)
        initial_height = self._height_from_output(0.0 if initial_output is None else float(initial_output))
        self._volume_m3 = self.area_m2 * min(max(initial_height, 0.0), self.height_m)
        self._qin_m3s = 0.0
        self._qout_m3s = 0.0

    def set_flows(self, q_in_m3s: float, q_out_m3s: float) -> None:
        self._qin_m3s = float(q_in_m3s or 0.0)
        self._qout_m3s = float(q_out_m3s or 0.0)

    def update(self, dt: float) -> None:
        dt = max(float(dt), 0.0)
        self._volume_m3 += (self._qin_m3s - self._qout_m3s) * self.gain * dt
        self._volume_m3 = min(max(self._volume_m3, 0.0), self.capacity_m3)

    def current_value(self) -> float:
        height_m = self._volume_m3 / self.area_m2
        if self.level_unit == "percent":
            return 100.0 * height_m / self.height_m
        if self.level_unit == "ft":
            return height_m / self._M_PER_FT
        if self.level_unit == "in":
            return height_m / self._M_PER_IN
        return height_m

    def _height_from_output(self, value: float) -> float:
        if self.level_unit == "percent":
            return min(max(value, 0.0), 100.0) / 100.0 * self.height_m
        if self.level_unit == "ft":
            return value * self._M_PER_FT
        if self.level_unit == "in":
            return value * self._M_PER_IN
        return value

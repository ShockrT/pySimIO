"""
simulator.py
Milestones 1–2: unified component API + concrete PV components.

Components implement:
    update(dt: float) -> None
    current_value() -> float
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
import random


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class SimComponent(ABC):
    """Common base for all simulation components."""
    name: str

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def update(self, dt: float) -> None:
        """Advance component state by dt seconds."""
        ...

    @abstractmethod
    def current_value(self) -> float:
        """Return the current primary process value."""
        ...


# ---------------------------------------------------------------------------
# Sensor
# ---------------------------------------------------------------------------

class Sensor(SimComponent):
    """
    Flexible sensor:
    - If source_component + attribute are supplied, mirrors that attribute with optional noise/lag.
    - Otherwise acts like a holding PV you can write() and bind to a PLC tag.

    Public API:
        bind_tag(tag: str)
        write(value: float)
        read() -> float
        update(dt: float)
        current_value() -> float
    """
    def __init__(
        self,
        name: str,
        source_component: Optional[object] = None,
        attribute: Optional[str] = None,
        noise_std: float = 0.0,
        lag_samples: int = 0,
        initial: float = 0.0,
    ):
        super().__init__(name)
        self._tag: Optional[str] = None
        self._value: float = float(initial)
        self._src = source_component
        self._attr = attribute
        self._noise_std = float(noise_std)
        self._lag = int(lag_samples)
        self._history: list[float] = []

    # PLC helpers
    def bind_tag(self, tag: str) -> None:
        self._tag = tag

    def write(self, value: float) -> None:
        self._value = float(value)

    def read(self) -> float:
        return float(self.current_value())

    # SimComponent
    def update(self, dt: float) -> None:
        if self._src is None or self._attr is None:
            # Holding sensor: nothing to update unless write() is called.
            return

        val = getattr(self._src, self._attr, None)
        if val is None:
            val = 0.0

        if self._noise_std > 0.0:
            val = float(val) + random.gauss(0.0, self._noise_std)

        if self._lag > 0:
            self._history.append(float(val))
            if len(self._history) > self._lag:
                val = self._history.pop(0)
            else:
                val = 0.0

        self._value = float(val)

    def current_value(self) -> float:
        return float(self._value)


# ---------------------------------------------------------------------------
# Concrete PV components
# ---------------------------------------------------------------------------

class FlowComponent(SimComponent):
    """
    First-order flow response toward k * input.
    Call set_input(u) externally (e.g., pump speed or valve-derived input).

    params:
        k:       proportional gain (default 1.0)
        tau:     time constant seconds (default 1.0)
        initial: initial flow value
    """
    def __init__(self, name: str, k: float = 1.0, tau: float = 1.0, initial: float = 0.0):
        super().__init__(name)
        self.k = float(k)
        self.tau = max(float(tau), 1e-6)
        self._u = 0.0
        self._y = float(initial)

    def set_input(self, u: float) -> None:
        self._u = float(u)

    def update(self, dt: float) -> None:
        target = self.k * self._u
        alpha = min(1.0, float(dt) / self.tau)
        self._y += (target - self._y) * alpha

    def current_value(self) -> float:
        return float(self._y)


class PressureComponent(SimComponent):
    """
    Pressure mass-balance style:
        dP/dt = (k_in * q_in - k_out * q_out - leak * P) / tau

    You must set flows with set_flows(q_in, q_out).

    params:
        k_in:    multiplier on inlet flow (default 1.0)
        k_out:   multiplier on outlet flow (default 1.0)
        leak:    leakage coefficient (default 0.0)
        tau:     time constant seconds (default 2.0)
        initial: initial pressure value
    """
    def __init__(self, name: str, k_in: float = 1.0, k_out: float = 1.0, tau: float = 2.0, leak: float = 0.0, initial: float = 0.0):
        super().__init__(name)
        self.k_in = float(k_in)
        self.k_out = float(k_out)
        self.tau = max(float(tau), 1e-6)
        self.leak = float(leak)
        self._p = float(initial)
        self._qin = 0.0
        self._qout = 0.0

    def set_flows(self, qin: float, qout: float) -> None:
        self._qin = float(qin)
        self._qout = float(qout)

    def update(self, dt: float) -> None:
        dp = (self.k_in * self._qin - self.k_out * self._qout - self.leak * self._p) / self.tau
        self._p += dp * float(dt)

    def current_value(self) -> float:
        return float(self._p)


class LevelComponent(SimComponent):
    """
    Tank level:
        dH/dt = (q_in - q_out) / area

    Set with set_flows(q_in, q_out).

    params:
        area:    tank cross-sectional area (default 1.0)
        initial: initial level
    """
    def __init__(self, name: str, area: float = 1.0, initial: float = 0.0):
        super().__init__(name)
        self.area = max(float(area), 1e-6)
        self._h = float(initial)
        self._qin = 0.0
        self._qout = 0.0

    def set_flows(self, qin: float, qout: float) -> None:
        self._qin = float(qin)
        self._qout = float(qout)

    def update(self, dt: float) -> None:
        self._h += ((self._qin - self._qout) / self.area) * float(dt)

    def current_value(self) -> float:
        return float(self._h)


class TemperatureComponent(SimComponent):
    """
    First-order temperature toward ambient + k * input.

    params:
        tau:     time constant (default 5.0)
        ambient: ambient temperature (default 25.0)
        k:       proportional gain (default 1.0)
        initial: initial temperature (default ambient if None)
    """
    def __init__(self, name: str, tau: float = 5.0, ambient: float = 25.0, k: float = 1.0, initial: Optional[float] = None):
        super().__init__(name)
        self.tau = max(float(tau), 1e-6)
        self.ambient = float(ambient)
        self.k = float(k)
        self._u = 0.0
        self._t = float(self.ambient if initial is None else initial)

    def set_input(self, u: float) -> None:
        self._u = float(u)

    def update(self, dt: float) -> None:
        target = self.ambient + self.k * self._u
        alpha = min(1.0, float(dt) / self.tau)
        self._t += (target - self._t) * alpha

    def current_value(self) -> float:
        return float(self._t)

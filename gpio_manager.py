from typing import Dict, List
from constants import VALID_GPIO_PINS

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    ON_RPI = True
    print("[GPIO] RPi.GPIO geladen – hardware modus actief")
except (ImportError, RuntimeError):
    ON_RPI = False

    class _MockGPIO:
        BCM = "BCM"; OUT = "OUT"; IN = "IN"
        HIGH = True; LOW = False; PUD_DOWN = "PUD_DOWN"

        def __init__(self):
            self._pin_state: Dict[int, bool] = {}
            self._pin_mode:  Dict[int, str]  = {}

        def setmode(self, m): pass
        def setwarnings(self, w): pass
        def cleanup(self):
            self._pin_state.clear(); self._pin_mode.clear()
        def setup(self, pin, mode, pull_up_down=None, initial=None):
            self._pin_mode[pin] = mode
            self._pin_state[pin] = bool(initial) if initial is not None else False
        def output(self, pin, state):
            self._pin_state[pin] = bool(state)
        def input(self, pin) -> bool:
            return self._pin_state.get(pin, False)
        def mock_set_input(self, pin: int, state: bool):
            self._pin_state[pin] = state

    GPIO = _MockGPIO()
    print("[GPIO] MockGPIO actief – geen hardware nodig (Windows/Mac/Linux)")


def gpio_init_startup():
    """Zet alle GPIO-pins als OUTPUT LOW bij opstarten (voorkomt floating)."""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in VALID_GPIO_PINS:
            try:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            except Exception as e:
                print(f"[GPIO] Pin {pin}: {e}")
        print(f"[GPIO] {len(VALID_GPIO_PINS)} pins → OUTPUT LOW")
    except Exception as e:
        print(f"[GPIO] Opstartinitialisatie mislukt: {e}")


class GPIOManager:
    """
    Koppelt circuit-componenten aan Raspberry Pi GPIO-pins.
    INPUT  (gpio_dir="IN"):  GPIO hoog → schakelaar sluit in simulator.
    OUTPUT (gpio_dir="OUT"): component actief → GPIO hoog.
    """

    def __init__(self):
        self._configured: Dict[int, str] = {}
        self._initialized = False

    def configure_pins(self, components):
        if self._initialized:
            try: GPIO.cleanup()
            except Exception: pass
        self._configured.clear()
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
        except Exception as e:
            print(f"[GPIO] setmode fout: {e}")
        for pin in VALID_GPIO_PINS:
            try: GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            except Exception: pass
        for comp in components:
            pin = comp.gpio_pin
            if pin < 0 or pin not in VALID_GPIO_PINS:
                continue
            try:
                if comp.gpio_dir == "IN":
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    self._configured[pin] = "IN"
                else:
                    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                    self._configured[pin] = "OUT"
                print(f"[GPIO] Pin {pin} → {comp.gpio_dir} ({comp.label})")
            except Exception as e:
                print(f"[GPIO] Pin {pin} fout: {e}")
        self._initialized = True
        print(f"[GPIO] {len(self._configured)} pin(s): {list(self._configured.keys())}")

    def read_inputs(self, components) -> Dict[int, bool]:
        result = {}
        for i, comp in enumerate(components):
            pin = comp.gpio_pin
            if pin < 0 or comp.gpio_dir != "IN" or pin not in self._configured:
                continue
            try: result[i] = bool(GPIO.input(pin))
            except Exception: result[i] = False
        return result

    def write_outputs(self, components, active_states: Dict[int, bool]):
        for i, comp in enumerate(components):
            pin = comp.gpio_pin
            if pin < 0 or comp.gpio_dir != "OUT" or pin not in self._configured:
                continue
            try: GPIO.output(pin, GPIO.HIGH if active_states.get(i, False) else GPIO.LOW)
            except Exception as e: print(f"[GPIO] Schrijf fout pin {pin}: {e}")

    def get_all_states(self, components) -> List[dict]:
        result = []
        for comp in components:
            pin = comp.gpio_pin
            if pin < 0: continue
            try: state = bool(GPIO.input(pin))
            except Exception: state = False
            result.append({"pin": pin, "label": comp.label or comp.type,
                           "dir": comp.gpio_dir, "state": state,
                           "comp_type": comp.type, "configured": pin in self._configured})
        return result

    def mock_toggle(self, pin: int) -> bool:
        if not ON_RPI and pin in self._configured and self._configured[pin] == "IN":
            GPIO.mock_set_input(pin, not GPIO.input(pin))
            return True
        return False

    def cleanup(self):
        for pin, d in self._configured.items():
            if d == "OUT":
                try: GPIO.output(pin, GPIO.LOW)
                except Exception: pass
        try: GPIO.cleanup()
        except Exception: pass
        try:
            GPIO.setmode(GPIO.BCM); GPIO.setwarnings(False)
            for pin in VALID_GPIO_PINS:
                try: GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                except Exception: pass
        except Exception: pass
        self._configured.clear()
        self._initialized = False
        print("[GPIO] Cleanup voltooid – alle pins LOW")

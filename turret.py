from adafruit_servokit import ServoKit
from gpiozero import OutputDevice

# ---------- Wiring ----------
PAN_CHANNEL = 0          # PCA9685 channel for the side-to-side servo
TILT_CHANNEL = 1         # PCA9685 channel for the up-down servo
PUMP_PIN = 17            # Pi GPIO pin wired to the MOSFET module


# ---------- Safety limits (degrees) ----------
# The servos can NEVER go past these, no matter what the camera sees.
# Start narrow, widen carefully once mounted on the roof.
PAN_MIN, PAN_MAX = 45, 135
TILT_MIN, TILT_MAX = 70, 110


FRAME_W, FRAME_H = 1280, 720   # camera resolution


def clamp(value, low, high):
    return max(low, min(high, value))

class Turret:
    def __init__(self):
        self.kit = ServoKit(channels=16)
        for ch in (PAN_CHANNEL, TILT_CHANNEL):
            self.kit.servo[ch].set_pulse_width_range(500, 2500)   # DS3225 range
        self.pump = OutputDevice(PUMP_PIN, active_high=True, initial_value=False)
        self.center()

    def _move(self, pan, tilt):
        pan = clamp(pan, PAN_MIN, PAN_MAX)
        tilt = clamp(tilt, TILT_MIN, TILT_MAX)
        self.kit.servo[PAN_CHANNEL].angle = pan
        self.kit.servo[TILT_CHANNEL].angle = tilt

    def center(self):
        self._move(90, 90)

    def pixel_to_angles(self, cx, cy):
        # PLACEHOLDER: straight-line mapping until we calibrate with real water.
        pan = PAN_MAX - (cx / FRAME_W) * (PAN_MAX - PAN_MIN)
        tilt = TILT_MAX - (cy / FRAME_H) * (TILT_MAX - TILT_MIN)
        return pan, tilt

    def aim(self, cx, cy):
        pan, tilt = self.pixel_to_angles(cx, cy)
        self._move(pan, tilt)
        print(f"AIM pixel ({cx}, {cy}) -> pan {pan:.0f}, tilt {tilt:.0f}")

    def fire(self, on):
        if on:
            self.pump.on()
        else:
            self.pump.off()
        print("PUMP ON" if on else "PUMP OFF")

    def shutdown(self):
        self.pump.off()       # pump ALWAYS off on exit
        self.center()
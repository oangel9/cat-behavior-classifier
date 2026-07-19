from gpiozero import MotionSensor
from signal import pause

zones = {4: 'litter', 17: 'food', 27: 'water'}
sensors = {pin: MotionSensor(pin) for pin in zones}

for pin, sensor in sensors.items():
    zone = zones[pin]
    sensor.when_motion = lambda z=zone: print(f'Motion: {z}')
    sensor.when_no_motion = lambda z=zone: print(f'Clear: {z}')

print("Watching zones:", list(zones.values()))
pause()

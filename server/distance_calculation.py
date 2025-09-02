import math

def calculate_distance(rssi: int, tx_power: int = -59, factor: float = 2.5) -> float:
    if rssi > 0 or rssi < -120:
        raise Exception("illegal rssi value!!!")
    if rssi == 0:
        return -1.0
    # Formula: distance = 10^((txPower - RSSI) / (10 * n))
    exponent = (tx_power - rssi) / (10 * factor)
    if exponent > 10:
        return 10000.0
    distance = math.pow(10, exponent)
    return distance


"""
-63: 1.4454397707459274
-73: 1.9054607179632472

"""
print(calculate_distance(rssi=-66, factor=2.5))
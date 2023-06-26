def compute_r(c, m, d, b):
    if m < -10 or m > 10:
        raise ValueError("Multiplier should be between -10 and +10")
    return c * m * (10 ** d) * (2 ** b)


def deserialize_voltage(data: bytearray):
    value = int.from_bytes(data, byteorder='little', signed=False)
    return compute_r(value, 1, 0, -6)


def deserialize_int(data: bytearray):
    return int.from_bytes(data, byteorder='little', signed=False)


def deserialize_temperature(data: bytearray):
    value = int.from_bytes(data, byteorder='little', signed=True)
    value = compute_r(value, 1, -2, 0)

    return value


def deserialize_pressure(data: bytearray):
    #  M = 1, d = -1, b = 0
    value = int.from_bytes(data, byteorder='little', signed=True)
    value = compute_r(value, 1, -1, 0)

    return value


def deserialize_humidity(data: bytearray):
    # M = 1, d = -2, b = 0
    value = int.from_bytes(data, byteorder='little', signed=True)
    value = compute_r(value, 1, -2, 0)

    return value

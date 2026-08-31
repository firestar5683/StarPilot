import os

SHM_PARAMS_PATH = "/dev/shm/params/d"

def get_shm_param(name, default):
    p = os.path.join(SHM_PARAMS_PATH, name)
    if os.path.exists(p):
        try:
            with open(p, "r") as f:
                val = f.read().strip()
                if isinstance(default, bool):
                    return val == "1" or val.lower() == "true"
                elif isinstance(default, int):
                    return int(val)
                elif isinstance(default, float):
                    return float(val)
                return val
        except Exception:
            return default
    return default

def set_shm_param(name, value):
    try:
        os.makedirs(SHM_PARAMS_PATH, exist_ok=True)
        p = os.path.join(SHM_PARAMS_PATH, name)
        with open(p, "w") as f:
            if isinstance(value, bool):
                f.write("1" if value else "0")
            else:
                f.write(str(value))
        return True
    except Exception:
        return False

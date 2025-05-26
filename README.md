## Overview
2 lightweight Python scripts—a **publisher** and a **consumer**—that communicate over a Unix-domain socket. The publisher simulates an IMU by generating readings at a configurable rate; the consumer listens, unpacks the data, and optionally computes basic roll/pitch/yaw angles. Tested on Ubuntu 20.04

## Requirements
OS: Debian/Ubuntu

Python: 3.6 or newer

## Setup
1. Clone or download this repository.
2. Make both scripts executable:
   ```bash
   chmod +x publisher.py consumer.py
   ```
3. Verify Python 3 is available:
   ```bash
   python3 --version
   ```

## Usage

### Start the consumer
```
./consumer.py --socket-path /tmp/imu.sock --log-level INFO --timeout-ms 100 [--compute-euler]
```

`--timeout-ms` sets the receive timeout in milliseconds.

Add `--compute-euler` to log roll/pitch/yaw alongside raw sensor data.

### Start the publisher
```
./publisher.py --socket-path /tmp/imu.sock --log-level DEBUG --frequency-hz 500 [--retries 5] [--retry-delay-ms 200]
```

`--frequency-hz` controls the publish rate in Hz like in document.

`--retries` and `--retry-delay-ms` to handle transient send errors.

Can launch them in any order. The publisher waits for the socket file before sending, and the consumer logs timeouts at DEBUG not on INFO. This means that the INFO-level output stays focused on real data.

## Working

Data format matches the packed C struct shown in the document:

Serialization uses Python's `struct.pack("<fffIiiiIfffI", …)`

Euler angles computed via tilt-compensated “eCompass” method, something I found on STMicroelectronics guies and [mathworks](https://www.mathworks.com/help/nav/ref/ecompass.html).

## Error Handling & Robustness
**Argument validation:** ensures required flags and valid values

**Retries:** publisher retries on `FileNotFoundError`/`ConnectionRefusedError`

**Timeouts:** consumer uses configurable socket timeout and logs retries

**Logging:** timestamped, leveled logs (DEBUG for verbose, INFO for key events)

## Future Improvements
- Replace simple tilt-compensation with a quaternion-based filter to avoid gimbal lock
- Add real-time scheduling hints (e.g., `chrt`, `nice`) for deterministic timing
- Implement a clean shutdown handshake beyond Ctrl+C

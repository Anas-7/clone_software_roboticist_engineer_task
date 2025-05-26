#!/usr/bin/env python3
import argparse
import logging
import socket
import struct
import time
import random
import sys
import os

PAYLOAD_FMT = "<fffIiiiIfffI"  # 3×float, uint32, 3×int32, uint32, 3×float, uint32
PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FMT)

def parse_args():
    p = argparse.ArgumentParser(
        description="IMU data publisher over Unix-domain socket"
    )
    p.add_argument(
        "--socket-path", required=True,
        help="Path to Unix-domain socket file (e.g. /tmp/imu.sock)"
    )
    p.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"]
    )
    p.add_argument(
        "--frequency-hz", type=float, required=True,
        help="Publish frequency in Hz (must be > 0)"
    )
    p.add_argument(
        "--retries", type=int, default=3,
        help="Number of retries if send fails"
    )
    p.add_argument(
        "--retry-delay-ms", type=int, default=100,
        help="Delay between retries in milliseconds"
    )
    return p.parse_args()

def make_payload():
    ts = int(time.time())
    # accel [g]
    xAcc, yAcc, zAcc = (random.uniform(-1,1) for _ in range(3))
    # gyro [mDeg/s]
    xGyro, yGyro, zGyro = (random.randint(-250000,250000) for _ in range(3))
    # mag [mGauss]
    xMag, yMag, zMag = (random.uniform(-100,100) for _ in range(3))
    return struct.pack(
        PAYLOAD_FMT,
        xAcc, yAcc, zAcc, ts,
        xGyro, yGyro, zGyro, ts,
        xMag, yMag, zMag, ts
    )

def main():
    args = parse_args()
    lvl = getattr(logging, args.log_level)
    logging.basicConfig(
        level=lvl,
        format="[%(asctime)s] %(levelname)s: %(message)s"
    )

    if args.frequency_hz <= 0:
        logging.error("frequency-hz must be > 0")
        sys.exit(1)

    # wait for consumer to bind the socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.setblocking(False)

    logging.info(f"Publishing to {args.socket_path} @ {args.frequency_hz:.1f} Hz")
    # no bind() — we just sendto the consumer's socket
    period = 1.0 / args.frequency_hz

    try:
        while True:
            payload = make_payload()
            for attempt in range(1, args.retries+1):
                try:
                    sock.sendto(payload, args.socket_path)
                    break
                except (FileNotFoundError, ConnectionRefusedError) as e:
                    logging.warning(f"Send attempt {attempt}/{args.retries} failed: {e}")
                    time.sleep(args.retry_delay_ms / 1000.0)
                except Exception as e:
                    logging.error(f"Unexpected error on send: {e}", exc_info=True)
                    break
            else:
                logging.error("All send retries failed; skipping this sample")

            time.sleep(period)
    except KeyboardInterrupt:
        logging.info("Interrupted—shutting down")
    finally:
        sock.close()

if __name__ == "__main__":
    main()

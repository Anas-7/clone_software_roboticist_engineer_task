#!/usr/bin/env python3
import argparse
import logging
import socket
import struct
import sys
import os
import math

# 3×float, uint32, 3×int32, uint32, 3×float, uint32
PAYLOAD_FMT = "<fffIiiiIfffI"
PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FMT)

def parse_args():
    p = argparse.ArgumentParser(description="IMU data consumer over Unix-domain socket")
    p.add_argument(
        "--socket-path", required=True,
        help="Path to Unix-domain socket file (e.g. /tmp/imu.sock)"
    )
    p.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"]
    )
    p.add_argument(
        "--timeout-ms", type=int, required=True,
        help="Receive timeout in milliseconds"
    )
    p.add_argument(
        "--compute-euler", action="store_true",
        help="Compute roll/pitch/yaw from accel+mag"
    )
    return p.parse_args()

# Compute roll, pitch, yaw from accelerometer and magnetometer data
def compute_euler(xAcc, yAcc, zAcc, xMag, yMag, zMag):
    roll  = math.atan2(yAcc, zAcc) # Roll around X-axis
    pitch = math.atan2(-xAcc, math.hypot(yAcc, zAcc)) # Pitch around Y-axis
    mx = xMag * math.cos(pitch) + zMag * math.sin(pitch) # Project magnetometer onto horizontal plane
    my = (xMag * math.sin(roll)*math.sin(pitch)
          + yMag * math.cos(roll)
          - zMag * math.sin(roll)*math.cos(pitch))
    yaw = math.atan2(-my, mx) 
    return tuple(math.degrees(v) for v in (roll, pitch, yaw))

def main():
    args = parse_args()
    lvl = getattr(logging, args.log_level)
    logging.basicConfig(
        level=lvl,
        format="[%(asctime)s] %(levelname)s: %(message)s"
    )

    # Remove any stale socket file
    if os.path.exists(args.socket_path):
        try:
            os.remove(args.socket_path)
            logging.debug(f"Removed stale socket file: {args.socket_path}")
        except OSError as e:
            logging.error(f"Failed to remove stale socket: {e!r}", exc_info=True)
            sys.exit(1)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.bind(args.socket_path)
        sock.settimeout(args.timeout_ms / 1000.0)
    except Exception as e:
        logging.error(f"Socket bind failed: {e!r}", exc_info=True)
        sys.exit(1)

    logging.info("Consumer starting")
    logging.info(
        f"Config → socket_path={args.socket_path}, "
        f"timeout={args.timeout_ms}ms, compute_euler={args.compute_euler}"
    )

    try:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
            except socket.timeout:
                logging.debug("Receive operation timed out; retrying")
                continue
            except Exception as e:
                logging.error(f"Receive error: {e!r}", exc_info=True)
                continue

            logging.info(f"Received payload ({len(data)} bytes)")

            if len(data) != PAYLOAD_SIZE:
                logging.warning(
                    f"Ignoring packet: size {len(data)} ≠ expected {PAYLOAD_SIZE}"
                )
                continue

            try:
                (xAcc, yAcc, zAcc, tsAcc,
                 xGyro, yGyro, zGyro, tsGyro,
                 xMag, yMag, zMag, tsMag) = struct.unpack(PAYLOAD_FMT, data)

                logging.debug(
                    f"Acc=({xAcc:.3f},{yAcc:.3f},{zAcc:.3f})@{tsAcc}  "
                    f"Gyro=({xGyro},{yGyro},{zGyro})@{tsGyro}  "
                    f"Mag=({xMag:.3f},{yMag:.3f},{zMag:.3f})@{tsMag}"
                )

                if args.compute_euler:
                    roll, pitch, yaw = compute_euler(xAcc, yAcc, zAcc, xMag, yMag, zMag)
                    logging.info(
                        f"Euler angles (deg): roll={roll:.1f}, "
                        f"pitch={pitch:.1f}, yaw={yaw:.1f}"
                    )
            except struct.error as e:
                logging.error(f"Unpack failed: {e!r}", exc_info=True)
            except Exception as e:
                logging.error(f"Processing error: {e!r}", exc_info=True)

    except KeyboardInterrupt:
        logging.info("Consumer interrupted; shutting down")
    finally:
        sock.close()
        try:
            os.remove(args.socket_path)
        except OSError:
            logging.error(f"Failed to remove socket file: {args.socket_path}", exc_info=True)

if __name__ == "__main__":
    main()

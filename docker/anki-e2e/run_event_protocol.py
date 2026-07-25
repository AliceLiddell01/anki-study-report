#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))
from run_event_runtime import *


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema-validated live run event protocol")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("initialize")
    initialize.add_argument("--output", required=True, type=Path)
    initialize.add_argument("--producer", required=True, choices=sorted(PRODUCERS))
    initialize.add_argument("--message")
    initialize.add_argument("--schema-version", type=int, choices=sorted(SUPPORTED_SCHEMA_VERSIONS), default=SCHEMA_VERSION)
    emit_parser = commands.add_parser("emit")
    emit_parser.add_argument("--output", required=True, type=Path)
    emit_parser.add_argument("--producer", required=True, choices=sorted(PRODUCERS))
    emit_parser.add_argument("--phase-id", required=True)
    emit_parser.add_argument("--event-kind", required=True, choices=sorted(EVENT_KINDS))
    emit_parser.add_argument("--status", required=True, choices=sorted(STATUSES))
    emit_parser.add_argument("--duration-ms", type=int)
    emit_parser.add_argument("--current", type=int)
    emit_parser.add_argument("--total", type=int)
    emit_parser.add_argument("--message")
    emit_parser.add_argument("--failure-code", choices=sorted(failure_protocol.REGISTRY))
    emit_parser.add_argument("--original-exit-code", type=int)
    emit_parser.add_argument("--original-signal", choices=sorted(item for item in failure_protocol.ALLOWED_SIGNALS if item))
    finish = commands.add_parser("finish-run")
    finish.add_argument("--output", required=True, type=Path)
    finish.add_argument("--producer", required=True, choices=sorted(PRODUCERS))
    finish.add_argument("--status", required=True, choices=("pass", "fail", "cancel"))
    finish.add_argument("--duration-ms", type=int)
    finish.add_argument("--message")
    finish.add_argument("--failure-code", choices=sorted(failure_protocol.REGISTRY))
    finish.add_argument("--original-exit-code", type=int)
    finish.add_argument("--original-signal", choices=sorted(item for item in failure_protocol.ALLOWED_SIGNALS if item))
    cancel = commands.add_parser("cancel-run")
    cancel.add_argument("--output", required=True, type=Path)
    cancel.add_argument("--producer", required=True, choices=sorted(PRODUCERS))
    cancel.add_argument("--duration-ms", type=int)
    cancel.add_argument("--original-exit-code", type=int, choices=(130, 143), required=True)
    cancel.add_argument("--original-signal", choices=("SIGINT", "SIGTERM"))
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--output", required=True, type=Path)
    validate_parser.add_argument("--producer", choices=sorted(PRODUCERS))
    validate_parser.add_argument("--allow-running", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "initialize":
            initialize_stream(args.output, args.producer, message=args.message, schema_version=args.schema_version)
        elif args.command == "emit":
            emit(
                args.output,
                args.producer,
                args.phase_id,
                args.event_kind,
                args.status,
                duration_ms=args.duration_ms,
                current=args.current,
                total=args.total,
                message=args.message,
                failure_code=args.failure_code,
                original_exit_code=args.original_exit_code,
                original_signal=args.original_signal,
            )
        elif args.command == "finish-run":
            finish_run(
                args.output,
                args.producer,
                args.status,
                duration_ms=args.duration_ms,
                message=args.message,
                failure_code=args.failure_code,
                original_exit_code=args.original_exit_code,
                original_signal=args.original_signal,
            )
        elif args.command == "cancel-run":
            cancel_run(
                args.output,
                args.producer,
                duration_ms=args.duration_ms,
                original_exit_code=args.original_exit_code,
                original_signal=args.original_signal,
            )
        else:
            validate_stream(args.output, expected_producer=args.producer, require_final=not args.allow_running)
        return 0
    except (
        RunEventError,
        failure_protocol.FailureProtocolError,
        cancellation_protocol.CancellationProtocolError,
        RuntimeError,
    ) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

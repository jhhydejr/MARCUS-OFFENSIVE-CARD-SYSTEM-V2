from __future__ import annotations

import argparse
import json
from pathlib import Path

from .batch import compile_batch, load_batch_calls
from .certification import CertificationEngine
from .database_health import DatabaseHealthEngine
from .pipeline import PipelineController
from .system import MarcusError, MarcusSystem


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(prog="marcus-cad")
    sub = parser.add_subparsers(dest="command", required=True)

    draw = sub.add_parser("draw", help="Retrieve/export an exact approved stored drawing")
    draw.add_argument("call")
    draw.add_argument("--out", default="output/card")
    draw.add_argument("--card-type", choices=["FORMATION_CARD", "SCOUT_CARD", "PLAY_CARD"], default="SCOUT_CARD")
    draw.add_argument(
        "--require-assignments",
        action="store_true",
        help="Block export unless every offensive player has an approved assignment object",
    )

    run = sub.add_parser("run", help="Run the complete call-to-card pipeline")
    run.add_argument("call")
    run.add_argument("--out", default="output/pipeline")
    run.add_argument("--card-type", choices=["FORMATION_CARD", "SCOUT_CARD", "PLAY_CARD"], default="SCOUT_CARD")
    run.add_argument("--require-assignments", action="store_true")

    compile_cmd = sub.add_parser("compile", help="Resolve a full play call and report missing objects")
    compile_cmd.add_argument("call")
    compile_cmd.add_argument("--report", default="output/compile_report.json")

    batch = sub.add_parser("batch", help="Compile/draw calls from a text file")
    batch.add_argument("input")
    batch.add_argument("--out", default="output/batch")
    batch.add_argument("--card-type", choices=["FORMATION_CARD", "SCOUT_CARD", "PLAY_CARD"], default="SCOUT_CARD")
    batch.add_argument("--require-assignments", action="store_true")

    certify = sub.add_parser("certify", help="Run release certification checks")
    certify.add_argument("--out", default="output/certification")

    health = sub.add_parser("database-health", help="Audit football database references and identity")
    health.add_argument("--report", default="reports/database_health.json")

    args = parser.parse_args()
    system = MarcusSystem(project_root())

    try:
        if args.command == "run":
            result = PipelineController(system).compile_play(
                args.call, Path(args.out), card_type=args.card_type, require_assignments=args.require_assignments
            )
            print(json.dumps(result.__dict__ | {"stages": [stage.__dict__ for stage in result.stages]}, indent=2))
            return 0 if result.success else 2
        if args.command == "draw":
            manifest = system.draw(
                args.call,
                Path(args.out),
                card_type=args.card_type,
                require_assignments=args.require_assignments,
            )
            print(json.dumps(manifest, indent=2))
            return 0
        if args.command == "compile":
            result = system.compile_report(args.call, Path(args.report))
            print(json.dumps(result.__dict__, indent=2))
            return 0 if result.renderable else 2
        if args.command == "database-health":
            report = DatabaseHealthEngine(system.root).write_report(Path(args.report))
            print(json.dumps(report.to_dict(), indent=2))
            return 0 if report.valid else 2
        if args.command == "certify":
            report = CertificationEngine(system, "2.4.4").run(Path(args.out))
            print(json.dumps({**report.__dict__, "checks": [check.__dict__ for check in report.checks]}, indent=2))
            return 0 if report.status == "CERTIFIED" else 2
        if args.command == "batch":
            calls = load_batch_calls(Path(args.input))
            summary = compile_batch(
                system, calls, Path(args.out), card_type=args.card_type, require_assignments=args.require_assignments
            )
            payload = {
                "schema": summary.schema,
                "total": summary.total,
                "rendered": summary.rendered,
                "blocked": summary.blocked,
                "all_rendered": summary.all_rendered,
                "card_type": summary.card_type,
                "items": [item.__dict__ for item in summary.items],
            }
            print(json.dumps(payload, indent=2))
            return 0 if summary.all_rendered else 2
    except MarcusError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

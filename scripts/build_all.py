from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> None:
    pretty = " ".join(cmd)
    print(f"==> {pretty}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Build core/server distributions into a shared dist/ directory.",
    )
    parser.add_argument(
        "--outdir",
        default=str(repo_root / "dist"),
        help="Output directory for built artifacts (default: %(default)s)",
    )
    parser.add_argument(
        "--no-isolation",
        action="store_true",
        help="Disable build isolation (passes --no-isolation to python -m build)",
    )
    parser.add_argument(
        "--sdist-only",
        action="store_true",
        help="Build only sdists (passes --sdist)",
    )
    parser.add_argument(
        "--wheel-only",
        action="store_true",
        help="Build only wheels (passes --wheel)",
    )
    parser.add_argument(
        "projects",
        nargs="*",
        default=["core", "server"],
        help="Project directories to build (default: core server)",
    )

    args = parser.parse_args()

    if args.sdist_only and args.wheel_only:
        print("error: cannot use --sdist-only and --wheel-only together", file=sys.stderr)
        return 2

    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    build_flags: list[str] = []
    if args.no_isolation:
        build_flags.append("--no-isolation")
    if args.sdist_only:
        build_flags.append("--sdist")
    if args.wheel_only:
        build_flags.append("--wheel")

    for project in args.projects:
        project_dir = (repo_root / project).resolve()
        if not project_dir.is_dir():
            print(f"error: project directory not found: {project_dir}", file=sys.stderr)
            return 2

        cmd = [
            sys.executable,
            "-m",
            "build",
            str(project_dir),
            "--outdir",
            str(outdir),
            *build_flags,
        ]
        _run(cmd, cwd=repo_root)

    print(f"\nBuilt artifacts are in: {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

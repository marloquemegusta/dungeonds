#!/usr/bin/env python3
"""Deterministic 1-command rebuild orchestrator for DungeonDS.

Rebuilds assets (lab, characters, props, arenas), bakes runtime assets,
runs host contract tests, and builds the Nintendo DS ROM.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]

ALL_STEPS = ["lab", "characters", "props", "arenas", "bake", "tests", "rom"]
RENDER_STEPS = {"lab", "characters", "props", "arenas"}
BUILD_PROJECT_SCRIPT = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1")


def run_cmd(
    cmd: list[str] | str,
    cwd: Path = ROOT,
    desc: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    if desc:
        print(f"\n=== [{desc}] ===")
    cmd_repr = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(f">> {cmd_repr}")
    sys.stdout.flush()
    res = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=isinstance(cmd, str),
        check=False,
    )
    if check and res.returncode != 0:
        print(f"\nERROR: Step failed with exit code {res.returncode}: {cmd_repr}", file=sys.stderr)
        sys.exit(res.returncode)
    return res


def get_default_legibility() -> str:
    manifest_path = ROOT / "assets" / "sprites" / "characters" / "characters.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("defaults", {}).get("legibility", "auto")
        except Exception:
            pass
    return "auto"


def step_lab() -> None:
    build_script = ROOT / "tools" / "lab" / "build_offline_renderer.py"
    if not build_script.exists():
        print(f"ERROR: {build_script} not found", file=sys.stderr)
        sys.exit(1)
    run_cmd([sys.executable, str(build_script)], desc="lab: build offline renderer")


def step_characters(
    char_filter: list[str] | None,
    legibility: str | None,
    jobs: int,
) -> None:
    manifest_path = ROOT / "assets" / "sprites" / "characters" / "characters.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    defaults = manifest.get("defaults", {})
    all_chars = manifest.get("characters", {})

    if char_filter:
        chars_to_export = {k: v for k, v in all_chars.items() if k in char_filter}
        unknown = [k for k in char_filter if k not in all_chars]
        if unknown:
            print(f"WARNING: Unknown character(s) in --char: {', '.join(unknown)}", file=sys.stderr)
        if not chars_to_export:
            print(f"No matching characters to export (filter: {char_filter}). Skipping character export.")
            return
    else:
        chars_to_export = all_chars

    script_path = ROOT / "tools" / "lab" / "export_character_headless.cjs"
    if not script_path.exists():
        print(f"ERROR: {script_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== [characters: export {len(chars_to_export)} character(s) (jobs={jobs})] ===")

    task_list: list[tuple[str, list[str]]] = []
    for name, cfg in chars_to_export.items():
        model_path = ROOT / cfg["model"]
        out_dir = ROOT / "assets" / "sprites" / "characters" / name
        template_path = ROOT / cfg["template"]

        cmd = [
            "node",
            str(script_path),
            str(model_path),
            str(out_dir),
            "--template",
            str(template_path),
            "--anim",
            str(cfg["anim"]),
            "--resolution",
            str(cfg["resolution"]),
        ]

        fit_zoom = cfg.get("fitZoom", defaults.get("fitZoom"))
        if fit_zoom is not None:
            cmd.extend(["--fitZoom", str(fit_zoom)])

        muzzle_bone = cfg.get("muzzleBone", defaults.get("muzzleBone"))
        if muzzle_bone:
            cmd.extend(["--muzzleBone", str(muzzle_bone)])

        muzzle_forward = cfg.get("muzzleForward", defaults.get("muzzleForward"))
        if muzzle_forward is not None:
            cmd.extend(["--muzzleForward", str(muzzle_forward)])

        light = cfg.get("lightPreset", cfg.get("light", defaults.get("lightPreset", defaults.get("light"))))
        if light:
            cmd.extend(["--light", str(light)])

        outline = cfg.get("outlineMode", cfg.get("outline", defaults.get("outlineMode", defaults.get("outline"))))
        if outline:
            cmd.extend(["--outline", str(outline)])

        saturation = cfg.get("saturation", defaults.get("saturation"))
        if saturation is not None:
            cmd.extend(["--saturation", str(saturation)])

        # Determine effective legibility for this character
        char_legibility = legibility
        if not char_legibility or char_legibility == "auto":
            char_legibility = cfg.get("legibility", defaults.get("legibility", "c2"))
        if char_legibility in ("anterior", "c2"):
            cmd.extend(["--legibility", str(char_legibility)])

        task_list.append((name, cmd))

    def _worker(item: tuple[str, list[str]]) -> tuple[str, int, str, str, float]:
        cname, cmd = item
        print(f"  >> Starting export for: {cname}")
        t0 = time.time()
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        dt = time.time() - t0
        return cname, res.returncode, res.stdout, res.stderr, dt

    max_workers = max(1, jobs)
    failed: list[tuple[str, str, str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker, item): item[0] for item in task_list}
        for fut in as_completed(futures):
            cname, retcode, stdout, stderr, dt = fut.result()
            if retcode != 0:
                print(f"  !! FAILED {cname} (in {dt:.1f}s, exit code {retcode})", file=sys.stderr)
                failed.append((cname, stdout, stderr))
            else:
                print(f"  ok {cname} (in {dt:.1f}s)")

    if failed:
        print("\nERROR: One or more character exports failed:", file=sys.stderr)
        for cname, stdout, stderr in failed:
            print(f"\n--- Output for {cname} ---", file=sys.stderr)
            if stdout:
                print(stdout, file=sys.stderr)
            if stderr:
                print(stderr, file=sys.stderr)
        sys.exit(1)


def step_props(legibility: str | None = None) -> None:
    props_glb_dir = ROOT / "assets" / "environment" / "cathedral" / "props" / "glb"
    temp_props_raw = Path(tempfile.gettempdir()) / "props_raw"
    props_json_path = ROOT / "tools" / "props" / "props.json"
    prerender_script = ROOT / "tools" / "props" / "prerender_props.py"
    if not prerender_script.exists():
        print(f"ERROR: {prerender_script} not found", file=sys.stderr)
        sys.exit(1)

    with open(props_json_path, "r", encoding="utf-8") as fh:
        all_pieces = list(json.load(fh).keys())

    glb_pieces = [p for p in all_pieces if (props_glb_dir / f"{p}.glb").exists()]
    raw_pieces = [p for p in all_pieces if (temp_props_raw / p / "world.png").exists()]

    leg_args = ["--legibility", legibility] if legibility else []
    if glb_pieces:
        run_cmd(
            [sys.executable, str(prerender_script), *leg_args, *glb_pieces],
            desc=f"props: prerender {len(glb_pieces)}/{len(all_pieces)} props with lab",
        )
        prop_shadows_script = ROOT / "tools" / "props" / "prop_shadows.py"
        if prop_shadows_script.exists():
            run_cmd(
                [sys.executable, str(prop_shadows_script), *glb_pieces],
                desc=f"props: generate shadows for {len(glb_pieces)} props",
            )
    elif raw_pieces:
        run_cmd(
            [sys.executable, str(prerender_script), "--skip-lab", *raw_pieces],
            desc=f"props: reprocess {len(raw_pieces)}/{len(all_pieces)} props from temp raw cache",
        )
    else:
        print("\n=== [props] ===")
        print("Prop GLBs and raw cache absent (%TEMP%/props_raw); keeping existing assets/environment/cathedral/props/render/")


def step_arenas() -> None:
    export_arenas_script = ROOT / "tools" / "export_arenas.py"
    if not export_arenas_script.exists():
        print(f"ERROR: {export_arenas_script} not found", file=sys.stderr)
        sys.exit(1)
    run_cmd([sys.executable, str(export_arenas_script)], desc="arenas: export arenas")


def step_bake(legibility: str | None) -> None:
    gen_player_script = ROOT / "tools" / "generate_player_sprites_c.py"
    bake_cathedral_script = ROOT / "tools" / "bake_cathedral_kit.py"
    bake_arena_script = ROOT / "tools" / "bake_arena.py"

    gen_cmd = [sys.executable, str(gen_player_script)]
    if legibility:
        gen_cmd.extend(["--legibility", legibility])
    run_cmd(gen_cmd, desc="bake: generate player_sprite.c")

    extract_pal_script = ROOT / "tools" / "palette" / "extract_palette.py"
    prop_render_dir = ROOT / "assets" / "environment" / "cathedral" / "props" / "render"
    active_prop_imgs = [
        str(prop_render_dir / p / "color.png")
        for p in ("columna_entera", "banco_entero", "relicario", "santo", "vela")
        if (prop_render_dir / p / "color.png").exists()
    ]
    if extract_pal_script.exists() and active_prop_imgs:
        run_cmd(
            [
                sys.executable,
                str(extract_pal_script),
                "--terrain-colors", "0",
                "--prop-colors", "190",
                "--native",
                "--out", str(ROOT / "assets" / "environment" / "cathedral" / "palette"),
                *active_prop_imgs,
            ],
            desc="bake: extract cathedral prop palette (190 colors)",
        )

    run_cmd(
        [
            sys.executable,
            str(bake_cathedral_script),
            "--floor",
            "assets/environment/cathedral/floor/rombos_tripo",
            "--mode",
            "catedral",
        ],
        desc="bake: cathedral kit",
    )

    run_cmd(
        [
            sys.executable,
            str(bake_arena_script),
            "--spec",
            "assets/arenas/arenas.json",
        ],
        desc="bake: arena",
    )


def step_tests() -> None:
    project_json_path = ROOT / ".ds-game-dev" / "project.json"
    if not project_json_path.exists():
        print(f"ERROR: {project_json_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(project_json_path, "r", encoding="utf-8") as f:
        proj_data = json.load(f)

    host_tests = proj_data.get("hostTests", [])
    if not host_tests:
        print("\n=== [tests] ===")
        print("No hostTests specified in .ds-game-dev/project.json")
        return

    print(f"\n=== [tests: running {len(host_tests)} host contract tests] ===")
    for test_cmd_str in host_tests:
        parts = shlex.split(test_cmd_str, posix=False)
        if parts and parts[0].lower() in ("python.exe", "python"):
            parts[0] = sys.executable
        run_cmd(parts, desc=f"test: {test_cmd_str}")


def step_rom(variant: str | None) -> None:
    if not BUILD_PROJECT_SCRIPT.exists():
        print(f"ERROR: Toolchain build script not found: {BUILD_PROJECT_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "powershell",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(BUILD_PROJECT_SCRIPT),
        "-ProjectPath",
        str(ROOT),
    ]
    if variant:
        cmd.extend(["-Variant", variant])

    run_cmd(cmd, desc=f"rom: build project (variant={variant or 'default'})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic orchestrator for rebuilding DungeonDS assets, tests, and ROM."
    )
    parser.add_argument(
        "--only",
        default="all",
        help="Comma-separated list of pipeline steps to run (choices: all, lab, characters, props, arenas, bake, tests, rom). Default: all",
    )
    parser.add_argument(
        "--char",
        default=None,
        help="Optional comma-separated character names (e.g. corazon,cireneo) to only re-render those characters.",
    )
    parser.add_argument(
        "--legibility",
        choices=["anterior", "c2", "auto"],
        default=None,
        help="Optional legibility preset (anterior or c2). If omitted, uses defaults.legibility from characters.json or auto.",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Skip render steps (lab, characters, props, arenas), running only bake, tests, rom.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip host tests.",
    )
    parser.add_argument(
        "--skip-rom",
        action="store_true",
        help="Skip ROM build.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=2,
        help="Max parallel workers for headless character exports (default: 2).",
    )
    parser.add_argument(
        "--variant",
        default=None,
        help="Optional ROM build variant for build-project.ps1 (e.g. stress, playground-perf).",
    )

    args = parser.parse_args()

    # Parse and validate --only
    valid_step_names = set(ALL_STEPS) | {"all"}
    tokens = [tok.strip().lower() for tok in args.only.split(",") if tok.strip()]
    for tok in tokens:
        if tok not in valid_step_names:
            parser.error(f"Invalid step '{tok}' in --only. Valid choices: {', '.join(ALL_STEPS)}, all")

    if "all" in tokens:
        selected = list(ALL_STEPS)
    else:
        selected = [s for s in ALL_STEPS if s in tokens]

    # Apply skip flags
    if args.skip_render:
        selected = [s for s in selected if s not in RENDER_STEPS]
    if args.skip_tests:
        selected = [s for s in selected if s != "tests"]
    if args.skip_rom:
        selected = [s for s in selected if s != "rom"]

    # Effective legibility
    effective_legibility = args.legibility if args.legibility is not None else get_default_legibility()

    char_filter = [c.strip() for c in args.char.split(",") if c.strip()] if args.char else None

    print(f"Project root: {ROOT}")
    print(f"Active steps: {' -> '.join(selected) if selected else '(none)'}")
    print(f"Legibility:   {effective_legibility}")
    if "characters" in selected:
        print(f"Characters:   {', '.join(char_filter) if char_filter else 'all'} (jobs={args.jobs})")
    if "rom" in selected:
        print(f"ROM variant:  {args.variant or 'default'}")

    if not selected:
        print("\nNo steps selected to run. Exiting.")
        return

    t0 = time.time()
    for step in selected:
        if step == "lab":
            step_lab()
        elif step == "characters":
            step_characters(char_filter, effective_legibility, args.jobs)
        elif step == "props":
            step_props(effective_legibility)
        elif step == "arenas":
            step_arenas()
        elif step == "bake":
            step_bake(effective_legibility)
        elif step == "tests":
            step_tests()
        elif step == "rom":
            step_rom(args.variant)

    elapsed = time.time() - t0
    print(f"\nRebuild completed successfully in {elapsed:.1f}s!")


if __name__ == "__main__":
    main()

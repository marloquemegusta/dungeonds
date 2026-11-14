#!/usr/bin/env python
"""Ejecuta UNA tarea del benchmark con un modelo, de principio a fin.

  python -I bench/run_item.py run       <id> --alias luna:medium   # prepara + lanza el agente + califica
  python -I bench/run_item.py calibrate <id>                       # califica base y solucion de referencia (sin modelo)
  python -I bench/run_item.py grade     <id> --dir <directorio>    # califica un directorio ya existente

El modelo solo ve problem.md (+ preambulo). El directorio de trabajo es una copia
limpia del commit base (git archive, sin historial posterior). Las puertas se aplican
sobre una COPIA del resultado, con el overlay (tests/escenarios de la solucion).
"""
import argparse, io, json, os, re, shutil, subprocess, sys, tarfile, time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
TASKS = BENCH / "tasks"
RUNS = BENCH.parent / ".worktrees" / "bench-runs"          # .worktrees esta en .gitignore
REPOS = {"towerds": r"C:\codexlocal\towerds", "dungeonds": r"C:\codexlocal\dungeonds",
         "skill": r"C:\codexlocal\skills\agentic-ds-dev"}
SKILL = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts")
DELEGATE = r"C:\codexlocal\skills\delegate-agents\delegate.py"
OVERLAY_PREFIXES = ("scenarios/", "tests/")


def sh(cmd, cwd=None, timeout=None, check=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"{cmd}: {r.stderr or r.stdout}")
    return r


def load(item_id):
    return json.loads((TASKS / item_id / "item.json").read_text(encoding="utf-8")), \
           (TASKS / item_id / "problem.md").read_text(encoding="utf-8")


def export_commit(repo, commit, dest: Path):
    """Copia limpia (sin .git) del arbol de `commit` en dest."""
    if dest.exists():
        raise RuntimeError(f"ya existe {dest}")
    dest.mkdir(parents=True)
    r = subprocess.run(["git", "-C", REPOS[repo], "archive", "--format=tar", commit], capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
        t.extractall(dest, filter="data")


def git_init(work: Path):
    sh(["git", "init", "-q"], cwd=work, check=True)
    sh(["git", "-c", "user.name=bench", "-c", "user.email=b@b", "add", "-A"], cwd=work, check=True)
    sh(["git", "-c", "user.name=bench", "-c", "user.email=b@b", "commit", "-qm", "base"], cwd=work, check=True)


def overlay_files(item):
    """Ficheros de tests/escenarios que la solucion AÑADE o modifica, y su contenido."""
    repo, base, sol = item["repo"], item["base_commit"], item["solution_commits"][-1]
    if "overlay" in item:  # lista explicita: excluye tests de contrato atados a la solucion de referencia
        return list(item["overlay"]), sol
    out = sh(["git", "-C", REPOS[repo], "diff", "--name-status", base, sol], check=True).stdout.splitlines()
    files = []
    for ln in out:
        st, _, path = ln.partition("\t")
        if st[0] in "AM" and path.startswith(OVERLAY_PREFIXES) and not path.endswith((".png", ".pyc")):
            files.append(path)
    return files, sol


def apply_overlay(item, grade_dir: Path):
    files, sol = overlay_files(item)
    for f in files:
        data = subprocess.run(["git", "-C", REPOS[item["repo"]], "show", f"{sol}:{f}"], capture_output=True, check=True).stdout
        p = grade_dir / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return files


def ps(script, *args, timeout=900):
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SKILL / script), *args]
    r = sh(cmd, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def measure(png, m):
    """Medidas sobre capturas de pantalla (agnosticas a nombres internos del codigo del modelo)."""
    from PIL import Image
    import numpy as np
    a = np.array(Image.open(png).convert("RGB")).astype(int)
    x0, y0, x1, y1 = m["region"]
    c = m["color"]
    mask = (a[..., 0] >= c["r"][0]) & (a[..., 0] <= c["r"][1]) & (a[..., 1] >= c["g"][0]) & (a[..., 1] <= c["g"][1]) &            (a[..., 2] >= c["b"][0]) & (a[..., 2] <= c["b"][1])
    sub = mask[y0:y1, x0:x1]
    if m["medida"] == "max_row_count":
        return int(sub.sum(1).max())
    if m["medida"] == "count":
        return int(sub.sum())
    raise ValueError(m["medida"])


def grade_perf(perf, g: Path, out: Path, label, res):
    """Oraculo de rendimiento: compila la variante, corre el escenario perf y resume con el script del propio arbol."""
    variant = perf["variant"]
    gb = f"G1_build:{variant}"
    try:
        rc, log = ps("build-project.ps1", "-ProjectPath", str(g), "-Variant", variant, timeout=1200)
        (out / f"build{label}-{variant}.log").write_text(log, encoding="utf-8")
        m = re.search(r"DS_BUILD=(\w+)(.*)", log)
        res["gates"][gb] = {"pass": bool(m and m.group(1) == "PASS"), "detalle": m.group(0)[:200] if m else log[-300:]}
        if not res["gates"][gb]["pass"]:
            res["gates"]["G4_perf"] = {"pass": False, "detalle": f"sin build de la variante {variant}"}
            return
        rom = g / f"dungeonds-{variant}.nds"
        perf_out = out / f"perf{label}"
        name = Path(perf["scenario"]).stem
        rc, log = ps("run-scenario.ps1", "-ScenarioPath", str(g / perf["scenario"]), "-ProjectPath", str(g),
                     "-RomPath", str(rom), "-OutputPath", str(perf_out), timeout=900)
        (out / f"scenario{label}-{name}.log").write_text(log, encoding="utf-8")
        r = sh([sys.executable, str(g / perf["summary"]), str(perf_out), "--max-cpu-ms", str(perf["max_cpu_ms"])], timeout=300)
        txt = (r.stdout or "") + (r.stderr or "")
        (out / f"perf{label}.txt").write_text(r.stdout or "", encoding="utf-8")
        m = re.search(r"PERF_ORACLE=(PASS|FAIL)\s+cpu_ms=([0-9.]+)", txt)
        if not m:
            res["gates"]["G4_perf"] = {"pass": False, "max": perf["max_cpu_ms"], "detalle": "sin PERF_ORACLE en la salida: " + txt[-300:]}
        else:
            res["gates"]["G4_perf"] = {"pass": m.group(1) == "PASS", "valor": float(m.group(2)), "max": perf["max_cpu_ms"]}
    except Exception as e:  # nunca abortar la calificacion
        res["gates"]["G4_perf"] = {"pass": False, "max": perf.get("max_cpu_ms"), "detalle": f"error: {e}"}


def grade(item, work: Path, out: Path, label="") -> dict:
    """Copia work -> grade/, aplica overlay, build y escenarios. Devuelve el veredicto por puertas."""
    g = out / f"grade{label}"
    if g.exists():
        shutil.rmtree(g)
    shutil.copytree(work, g, ignore=shutil.ignore_patterns(".git", "artifacts", "build", "*.nds"))
    res = {"E": True, "gates": {}, "overlay": []}
    res["overlay"] = apply_overlay(item, g)
    rc, log = ps("build-project.ps1", "-ProjectPath", str(g), timeout=1200)
    (out / f"build{label}.log").write_text(log, encoding="utf-8")
    m = re.search(r"DS_BUILD=(\w+)(.*)", log)
    res["gates"]["G1_build"] = {"pass": bool(m and m.group(1) == "PASS"), "detalle": m.group(0) if m else log[-300:]}
    nw = re.search(r"new_warnings=(\d+)", log)
    res["gates"]["G1_build"]["new_warnings"] = int(nw.group(1)) if nw else None
    perf = item.get("oraculo_perf")
    scen = [f for f in res["overlay"] if f.startswith("scenarios/") and f.endswith(".json")
            and not (perf and f == perf["scenario"])]
    if res["gates"]["G1_build"]["pass"]:
        for s in scen:
            name = Path(s).stem
            rc, log = ps("run-scenario.ps1", "-ScenarioPath", str(g / s), "-ProjectPath", str(g),
                         "-OutputPath", str(out / f"scenario{label}" / name), timeout=900)
            (out / f"scenario{label}-{name}.log").write_text(log, encoding="utf-8")
            m = re.search(r"DSM_SCENARIO_RESULT=(\w+)(.*)", log)
            res["gates"][f"G3_{name}"] = {"pass": bool(m and m.group(1) == "PASS"), "detalle": m.group(0)[:200] if m else log[-300:]}
    for m in item.get("oraculo_auto", []):
        png = out / f"scenario{label}" / m["scenario"] / f"{m['capture']}.png"
        try:
            v = measure(png, m)
            ok = (m.get("min") is None or v >= m["min"]) and (m.get("max") is None or v <= m["max"])
            res["gates"][f"{m['gate']}_{m['id']}"] = {"pass": ok, "valor": v, "min": m.get("min"), "max": m.get("max")}
        except Exception as e:  # captura ausente = el escenario no llego a producirla
            res["gates"][f"{m['gate']}_{m['id']}"] = {"pass": False, "detalle": f"sin captura: {e}"}
    if perf:
        grade_perf(perf, g, out, label, res)
    res["accepted"] = bool(res["gates"]) and all(v["pass"] for v in res["gates"].values())
    (out / f"result{label}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


VERIFY_ON = r"""Verifica tu trabajo tu mismo: compila con
  powershell -NoProfile -File "C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1" -ProjectPath "<este directorio>"
y ejecuta escenarios headless con run-scenario.ps1 de la misma carpeta. Puedes escribir tus propios escenarios o tests."""
VERIFY_OFF = """En tu sandbox NO puedes compilar ni ejecutar la ROM (no hay Docker ni WSL). Razona con cuidado sobre el codigo C,
revisalo dos veces (tipos, punteros, desbordamientos, sin float) y entrega los cambios SIN verificar. Un evaluador externo compilara y probara tu resultado.
Intenta compilar o ejecutar como maximo una vez; si falla por el entorno, no reintentes."""


def make_brief(item, problem, toolchain=False):
    verify = VERIFY_ON if toolchain else VERIFY_OFF
    return f"""Eres un agente de programacion que trabaja de forma autonoma en este directorio (una copia aislada del proyecto, sin historial git util).
Lee AGENTS.md y STATUS.md del directorio antes de tocar nada. Reglas clave: Nintendo DS sin FPU (prohibido float/double en runtime), y no uses comandos interactivos.

Verifica tu trabajo tu mismo: compila con
  powershell -NoProfile -File "{SKILL}\\build-project.ps1" -ProjectPath "<este directorio>"
y, si procede, ejecuta escenarios headless con
  powershell -NoProfile -File "{SKILL}\\run-scenario.ps1" -ScenarioPath <escenario.json> -ProjectPath "<este directorio>"
Puedes escribir tus propios escenarios o tests para comprobar tu arreglo. No hagas commit. No toques nada fuera de este directorio.
Termina con un resumen corto: que cambiaste, que comprobaste y que NO pudiste comprobar.

## TAREA
{problem}
"""


def run(item_id, alias, timeout, toolchain=False):
    item, problem = load(item_id)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = RUNS / item_id / f"{alias.replace(':', '-')}-{stamp}"
    work = out / "work"
    export_commit(item["repo"], item["base_commit"], work)
    git_init(work)
    brief = out / "brief.md"
    brief.write_text(make_brief(item, problem, toolchain), encoding="utf-8")
    t0 = time.time()
    r = subprocess.run([sys.executable, "-I", DELEGATE, alias, "--brief", str(brief), "--cwd", str(work),
                        *(["--allow-toolchain"] if toolchain else []), "--timeout", str(timeout)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    (out / "agent_stdout.md").write_text(r.stdout, encoding="utf-8")
    (out / "agent_stderr.txt").write_text(r.stderr, encoding="utf-8")
    sh(["git", "add", "-A"], cwd=work)
    diff = sh(["git", "diff", "--cached", "--binary", "HEAD", "--", ".", ":(exclude)artifacts", ":(exclude)build", ":(exclude)*.nds"], cwd=work).stdout
    (out / "model.diff").write_text(diff, encoding="utf-8")
    meta = {"item": item_id, "alias": alias, "agent_rc": r.returncode, "agent_seconds": round(time.time() - t0, 1),
            "diff_lines": diff.count("\n"), "summary_stderr": r.stderr.strip().splitlines()[-1:] }
    res = grade(item, work, out)
    meta["result"] = res
    (out / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("item", "alias", "agent_seconds", "diff_lines", "summary_stderr")}, ensure_ascii=False))
    print("ACCEPTED" if res["accepted"] else "REJECTED", json.dumps(res["gates"], ensure_ascii=False))
    print("salida:", out)


def calibrate(item_id):
    item, _ = load(item_id)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = RUNS / item_id / f"calibrate-{stamp}"
    out.mkdir(parents=True)
    for label, commit in (("-base", item["base_commit"]), ("-solucion", item["solution_commits"][-1])):
        work = out / f"work{label}"
        export_commit(item["repo"], commit, work)
        res = grade(item, work, out, label)
        print(label, "ACCEPTED" if res["accepted"] else "REJECTED", json.dumps(res["gates"], ensure_ascii=False))
        if "G4_perf" in res["gates"]:
            p4 = res["gates"]["G4_perf"]
            print(label, "G4 perf cpu_ms =", p4.get("valor", "n/a"), "(max", p4.get("max"), ")", "PASS" if p4["pass"] else "FAIL")
    print("salida:", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "calibrate", "grade"])
    ap.add_argument("item")
    ap.add_argument("--alias", default="luna:medium")
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--dir")
    ap.add_argument("--toolchain", action="store_true", help="Codex sin sandbox (peligroso: requiere permiso explicito del usuario)")
    a = ap.parse_args()
    if a.cmd == "run":
        run(a.item, a.alias, a.timeout, a.toolchain)
    elif a.cmd == "calibrate":
        calibrate(a.item)
    else:
        item, _ = load(a.item)
        out = Path(a.dir).parent
        print(json.dumps(grade(item, Path(a.dir), out, "-regrade"), ensure_ascii=False, indent=2))

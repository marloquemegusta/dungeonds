#!/usr/bin/env python3
"""Tabla de dificultad de una corrida del bot de encuentros (variante encuentros-bot).

Uso: python tools/encuentros/bot_report.py <carpeta de salida de run-scenario.ps1> [...]
Lee el ultimo `state_capture` ("final") de events.jsonl y escribe una tabla en markdown por carpeta.
"""
import json
import os
import sys

PLANTAS = ["procesion", "embudo", "balcon", "pinza", "claro", "alambrada"]
TIERS = ["ligera", "media", "dura"]
RESULTADOS = {0: "sin acabar", 1: "victoria", 2: "muerte", 3: "tiempo agotado (40000 frames)"}


def final_state(folder):
    last = None
    with open(os.path.join(folder, "events.jsonl"), encoding="utf-8") as f:
        for line in f:
            ev = json.loads(line)
            if ev.get("action") == "state_capture" and ev.get("name") == "final":
                last = ev["state"]
    if last is not None:
        for k in ("state", "current", "plant", "tier", "woken", "cleared", "dones", "deaths"):
            last[k] &= 0xFF      # corridas antiguas los leian como s32
    return last


def report(folder):
    s = final_state(folder)
    if s is None:
        return f"{folder}: sin captura final\n"
    name = os.path.basename(os.path.normpath(folder))
    out = [f"### {name}", "",
           "| encuentro | planta | tier | segundos | golpes | vida al acabar | Dones |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for k in range(12):
        cleared = s["cleared"] > k
        secs = f"{s[f'clear_{k}'] / 60:.1f}" if cleared else "-"
        hp = s[f"hpend_{k}"] if cleared else "-"
        out.append(f"| {k + 1} | {PLANTAS[s[f'plant_{k}']]} | {TIERS[s[f'tier_{k}']]} | {secs} | "
                   f"{s[f'hits_{k}']} | {hp} | {s[f'donesat_{k}'] if cleared else '-'} |")
    boss = f"{s.get('boss_frames', 0) / 60:.1f}" if s["result"] == 1 else "-"
    out.append(f"| jefe | abanderado | - | {boss} | - | {s['hp']} | - |")
    res = RESULTADOS.get(s["result"], str(s["result"]))
    if s["result"] == 2:
        res += f" en el encuentro {s['death_enc'] + 1 if s['death_enc'] < 12 else 'jefe'}"
    mask = s.get("relic_mask", 0)
    faltan = ", ".join(str(k + 1) for k in range(12) if not mask & (1 << k)) if "relic_mask" in s else "?"
    out += ["", f"Resultado: {res}. Duracion del acto: {s['act_frames']} frames ({s['act_frames'] / 60:.0f} s).",
            f"Golpes recibidos en total: {s['hits_total']}. Disparos del bot: {s['shots']}. "
            f"Relicarios rotos: {s['relicarios']} (pasillos sin romper: {faltan or 'ninguno'}). Dones y Reliquias: {s['dones']}. "
            f"Corazones al final: {s['hp']}/{s['max_hp']} (minimo en el acto: {s.get('hp_min', '?')}). Atascos resueltos: {s['stuck_events']}.",
            f"Relicario visto/disparable/lejos/sin linea (frames): {s.get('relic_seen', '?')}/{s.get('relic_shootable', '?')}/{s.get('relic_norange', '?')}/{s.get('relic_nolos', '?')}.", ""]
    return "\n".join(out)


if __name__ == "__main__":
    for folder in sys.argv[1:]:
        print(report(folder))

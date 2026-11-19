#!/usr/bin/env python3
"""Sandboxizador de clips: describe una escena (heroe, enemigos, vida) y una lista de planos y genera el
escenario JSON para la variante `cathedral-sandbox` (buzon g_sandbox, include/sandbox.h).

Contrato:

    sc = ClipScene("apuntar", hero=(330, 1792), enemies=[Enemy("exvoto", 390, 1792)], weapon="sniper")
    sc.walk(["LEFT"], 36, expect=(284, 1792), show=[("exvoto", (390, 1792))])   # plano 1: andar N frames
    sc.aim((390, 1792), frames=40)                                            # plano 2: apuntar a un punto del mundo
    sc.hold(60)                                                               # plano 3: seguir apuntando (carga)
    sc.fire(frames=60, show=[...])                                            # plano 4: soltar = disparar
    scenario = sc.scenario()                                                  # dict listo para escribir

Planos disponibles (cada uno se captura cada `every` frames con capture_sequence c<n>; el runner solo captura
durante `frames`, no durante un wait_until):
    walk(buttons, frames)            mantiene la cruceta N frames
    aim(world, frames, height)       toca la pantalla en el punto del mundo (a `height` px sobre el suelo: 21 = boca del rayo)
    hold(frames)                     sigue con el lapiz apoyado
    fire(frames)                     suelta el lapiz
    press(button, frames, hold=1)    pulsa un boton (L) durante `hold` frames y sigue hasta `frames`
    wait(frames)                     espera capturando
Pasos sin captura (preparacion, no cuentan como plano):
    pre_walk(buttons, until_field, ...)   anda hasta que un campo cumpla una condicion (wait_until)
    wait_until(field, ...)                espera a una condicion
    poke(**campos)                        escribe campos del estado (hp, force_drop...)

Regla 5 (AGENTS.md): cada plano declara `show=[(nombre, (x, y) de suelo)]` y la posicion `hero` esperada; antes de
generar se comprueba con la camara del STRIP que cada objeto cae dentro del encuadre de 256x192 (si no, falla con
un mensaje). `expect=(x, y)` de un plano ademas se comprueba en el emulador (aserciones sobre g_nav_state).

Camara del strip 512x2048 (NO es la del arena de sandbox_scenes.camera()):
    cam_x = clamp(px - 128, 0, 256);  cam_y = clamp(py - 132, 96, 1952);  pantalla = mundo - cam
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox_scenes as sb  # noqa: E402

SCREEN_W, SCREEN_H = 256, 192
STRIP_W, STRIP_H = 512, 2048
HERO_SCREEN_Y = 132
MUZZLE_H = sb.MUZZLE_H
KINDS = {"charger": sb.CHARGER, "shooter": sb.SHOOTER, "exvoto": sb.EXVOTO, "abanderado": 4, "monaguillo": 5}
SEQ = 100                                # distinto de 1: la variante con PLAYGROUND encola su propia disposicion con seq=1 al arrancar
SLOT = 124                               # sizeof(Enemy) en la ROM
FLAG_NO_GEMS = 32
# Un sprite de enemigo/heroe ocupa ~40 px por encima de los pies y ~12 de ancho a cada lado.
SPRITE_UP, SPRITE_HALF = 40, 14


def camera(px, py):
    """Camara del strip (source/main.c update_camera para el bajo): ancho 512, alto 2048."""
    cx = min(max(px - SCREEN_W // 2, 0), STRIP_W - SCREEN_W)
    cy = min(max(py - HERO_SCREEN_Y, SCREEN_H // 2), STRIP_H - SCREEN_H // 2)
    return cx, cy


def to_screen(hero, world, height=0):
    cx, cy = camera(*hero)
    return world[0] - cx, world[1] - cy - height


def in_frame(hero, world, margin_x=SPRITE_HALF, margin_top=SPRITE_UP, margin_bottom=4):
    """Rect de pantalla del sprite (pies en `world`) entero dentro de 256x192."""
    sx, sy = to_screen(hero, world)
    return margin_x <= sx < SCREEN_W - margin_x and margin_top <= sy < SCREEN_H - margin_bottom


class Enemy:
    def __init__(self, kind, x, y, flags=0):
        self.type, self.x, self.y, self.flags = KINDS[kind], x, y, flags


class ClipScene:
    FIELD_EXTRA = {
        "god": {"symbol": "ps", "offset": 20, "type": "s32"},
        "hp": {"symbol": "ps", "offset": 0, "type": "s32"},
        "hero_x": {"symbol": "nav", "offset": 0, "type": "s32"},
        "hero_y": {"symbol": "nav", "offset": 4, "type": "s32"},
        "crouched": {"symbol": "crouch", "offset": 0, "type": "s32"},
        "force_drop": {"symbol": "fd", "offset": 0, "type": "u8"},
        "en0_x": {"symbol": "en", "offset": 0, "type": "s32"},
        "en0_y": {"symbol": "en", "offset": 4, "type": "s32"},
        "en0_active": {"symbol": "en", "offset": 24, "type": "s32"},
        "en0_hp": {"symbol": "en", "offset": 28, "type": "s32"},
        "en0_maxhp": {"symbol": "en", "offset": 32, "type": "s32"},
        "en0_state": {"symbol": "en", "offset": 41, "type": "u8"},
        "en0_timer": {"symbol": "en", "offset": 44, "type": "s32"},
    }

    def __init__(self, name, hero, enemies=(), weapon="sniper", hp=None, god=True, freeze_ai=True,
                 no_gems=True, description="", settle=40, every=2, boot=30):
        self.name, self.hero0, self.enemies = name, tuple(hero), list(enemies)
        self.weapon, self.hp, self.every, self.settle, self.boot = weapon, hp, every, settle, boot
        self.flags = sb.FLAG_CLEAR | (sb.FLAG_FREEZE_AI if freeze_ai else 0) | (sb.FLAG_GOD if god else 0) | (FLAG_NO_GEMS if no_gems else 0)
        self.description = description
        self.steps = []
        self.planes = []                 # (indice c<n>, etiqueta, frames)
        self.assertions = []
        self._hero = self.hero0           # posicion esperada del heroe tras el ultimo paso
        self._n = 0
        self._setup()

    # -- preparacion --------------------------------------------------------------------------------
    def _setup(self):
        enemies = [(e.type, e.x, e.y) for e in self.enemies]
        pokes = [{"field": "player_x", "value": self.hero0[0]}, {"field": "player_y", "value": self.hero0[1]},
                 {"field": "weapon", "value": sb.WEAPON[self.weapon]}, {"field": "style", "value": 0},
                 {"field": "flags", "value": self.flags}, {"field": "enemy_count", "value": len(enemies)}]
        for i, e in enumerate(self.enemies):
            pokes += [{"field": f"e{i}_type", "value": e.type}, {"field": f"e{i}_flags", "value": e.flags},
                      {"field": f"e{i}_x", "value": e.x}, {"field": f"e{i}_y", "value": e.y}]
        pokes.append({"field": "seq", "value": SEQ})                # el ultimo: el juego aplica la peticion al frame siguiente
        self.steps += [{"frames": self.boot}, {"poke": pokes, "frames": 1},
                       {"wait_until": {"field": "ack", "equals": SEQ, "timeout_frames": 60}},
                       {"frames": self.settle}]                   # el strip termina de pintar bajo el teletransporte
        if self.hp is not None:
            self.steps.append({"poke": [{"field": "hp", "value": self.hp}], "frames": 2})   # DESPUES del ack: sandbox_update pone hp=max

    # -- comprobaciones de la regla 5 ---------------------------------------------------------------
    def _check_show(self, label, hero, show):
        for item in show:                # (nombre, punto) o (nombre, punto, margen_superior_px)
            nm, pt = item[0], item[1]
            if not in_frame(hero, pt, margin_top=item[2] if len(item) > 2 else SPRITE_UP):
                sx, sy = to_screen(hero, pt)
                raise ValueError(f"[{self.name}] plano {label}: '{nm}' en el mundo {pt} cae FUERA del encuadre 256x192 "
                                 f"con el heroe en {hero}: pantalla ({sx},{sy}), camara {camera(*hero)}")

    def _plane(self, label, step, frames, show, expect, tol):
        if expect is not None:
            self._hero = tuple(expect)
        hero = self._hero
        self._check_show(label, hero, show or [])
        c = f"c{self._n}"
        step = dict(step)
        step["frames"] = frames
        step["capture_sequence"] = c
        step["capture_every"] = self.every
        if expect is not None:
            step["state_capture"] = f"{c}_fin"
            for fld, v in (("hero_x", expect[0]), ("hero_y", expect[1])):
                self.assertions.append({"at": f"{c}_fin", "field": fld, "min_value": int(round((v - tol) * 256))})
                self.assertions.append({"at": f"{c}_fin", "field": fld, "max_value": int(round((v + tol) * 256))})
        self.steps.append(step)
        self.planes.append((self._n, label, frames))
        self._n += 1

    # -- planos -------------------------------------------------------------------------------------
    def walk(self, buttons, frames, expect=None, show=None, tol=8):
        """Mantiene la cruceta (lista de nombres, p.ej. ["LEFT","UP"]). Suelta lo que ya estuviera pulsado."""
        buttons = [b.upper() for b in buttons]
        self._flush_buttons(buttons)
        self._plane("andar " + "+".join(buttons), {}, frames, show, expect, tol)

    def _flush_buttons(self, buttons):
        """Un step por boton (el runner solo admite un button_down/button_up por step): en pasos de 0 frames."""
        held = getattr(self, "_held", [])
        for b in held:
            if b not in buttons:
                self.steps.append({"button_up": b, "frames": 0})
        for b in buttons:
            if b not in held:
                self.steps.append({"button_down": b, "frames": 0})
        self._held = list(buttons)

    def stop(self):
        self._flush_buttons([])

    def aim(self, world, frames, height=MUZZLE_H, show=None, expect=None, tol=8, keep=()):
        """Apoya el lapiz sobre el punto del mundo `world` (suelo) a `height` px de altura (21 = la boca del rayo)."""
        self._flush_buttons([b.upper() for b in keep])
        hero = tuple(expect) if expect else self._hero
        sx, sy = to_screen(hero, world, height)
        if not (0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H):
            raise ValueError(f"[{self.name}] aim: el punto del mundo {world} (alto {height}) cae fuera de la pantalla: ({sx},{sy})")
        self._plane("apuntar", {"tap": {"x": sx, "y": sy}}, frames, show or [("objetivo", world)], expect, tol)

    def sweep(self, world_from, world_to, frames, height=MUZZLE_H, show=None, expect=None, tol=8, chunk=2, keep=()):
        """Arrastra el lapiz de un punto del mundo a otro (el rayo se ve moverse): una toma por cada `chunk` frames."""
        self._flush_buttons([b.upper() for b in keep])
        hero = tuple(expect) if expect else self._hero
        n = max(1, frames // chunk)
        c = f"c{self._n}"
        for i in range(n):
            t = i / max(1, n - 1)
            w = (world_from[0] + (world_to[0] - world_from[0]) * t, world_from[1] + (world_to[1] - world_from[1]) * t)
            sx, sy = to_screen(hero, w, height)
            sx, sy = round(sx), round(sy)
            if not (0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H):
                raise ValueError(f"[{self.name}] sweep: el punto {w} cae fuera de la pantalla ({sx},{sy})")
            self.steps.append({"tap": {"x": sx, "y": sy}, "frames": chunk, "capture_sequence": c, "capture_every": self.every})
        self._check_show("barrer", hero, show or [])
        if expect is not None:
            self._hero = tuple(expect)
        self.planes.append((self._n, "apuntar (barrido)", n * chunk))
        self._n += 1

    def hold(self, frames, show=None):
        self._plane("cargar", {}, frames, show, None, 0)

    def fire(self, frames, show=None):
        self._plane("disparar", {"release": True}, frames, show, None, 0)

    def press(self, button, frames, hold=1, show=None, expect=None, tol=8):
        """Pulsa `button` `hold` frames dentro del plano (el resto del plano se captura ya soltado)."""
        self.steps.append({"button_down": button.upper(), "frames": 0})
        self._plane(f"pulsar {button}", {}, hold, show, expect, tol)
        self.steps.append({"button_up": button.upper(), "frames": 0})
        if frames > hold:
            self._plane(f"tras {button}", {}, frames - hold, show, None, 0)

    def wait(self, frames, show=None, expect=None, tol=8):
        self._plane("esperar", {}, frames, show, expect, tol)

    # -- pasos sin captura ---------------------------------------------------------------------------
    def wait_until(self, field, timeout=300, **cond):
        self.steps.append({"wait_until": {"field": field, "timeout_frames": timeout, **cond}})

    def pre_walk(self, buttons, field, timeout=300, expect=None, **cond):
        """Anda (sin capturar) hasta que `field` cumpla la condicion (p.ej. hero_x min_value=281*256)."""
        self._flush_buttons([b.upper() for b in buttons])
        self.steps.append({"wait_until": {"field": field, "timeout_frames": timeout, **cond}})
        if expect:
            self._hero = tuple(expect)

    def poke(self, frames=1, **fields):
        self.steps.append({"poke": [{"field": k, "value": v} for k, v in fields.items()], "frames": frames})

    def assert_at(self, at, field, **check):
        self.assertions.append({"at": at, "field": field, **check})

    def sample(self, name, frames=0):
        self.steps.append({"state_capture": name, "frames": frames})

    # -- salida -------------------------------------------------------------------------------------
    def scenario(self):
        self._flush_buttons([])
        fields = {k: dict(v) for k, v in sb.FIELDS.items()}
        fields.update(self.FIELD_EXTRA)
        out = {
            "name": f"intro_clip_{self.name}",
            "description": self.description, "suite": False, "evidence_only": True,
            "state": {"symbols": {"sb": "g_sandbox", "ps": "g_player_state", "nav": "g_nav_state", "crouch": "g_hero_crouched",
                                  "fd": "g_pickup_force_drop", "en": "g_enemies"},
                      "default_symbol": "sb", "fields": fields},
            "steps": self.steps,
        }
        if self.assertions:
            out["assertions"] = {"state_changes": self.assertions}
            out["evidence_only"] = False
        return out

    def total_frames(self):
        return sum(f for _, _, f in self.planes)

"""Genera scenarios/super_monja_arana_erratica_{1,2}.json: la monjaraña moviendose a arrancadas por poke (evidencia, solo ROM arpg-lab).
La Super Monja se deja en estado DORMANT (la IA no la toca) y cada paso de 2 frames escribe posicion, direccion y frame de animacion.
Trayectoria por tramos (angulo en pantalla, frames de arrancada, frames de parada); dir 0=S,1=SW,2=W,3=NW,4=N,5=NE,6=E,7=SE."""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERO = (265.0, 1781.0)            # heroe invulnerable, quieto (px de mundo; 1 px de pantalla = 1 px de mundo)
SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0     # px de mundo por captura (2 frames de juego): ~2-3x la velocidad normal en arrancada
BURST_FRAMES = 6                  # frames de la hoja que se animan (0..5); 6 y 7 son el frame de parada
def orbit_moves(seed=7, n=15, radius=48.0):
    """Ronda al heroe en sentido horario con quiebros: rumbo tangente + giro brusco, corregido hacia el radio de ronda; un retroceso corto."""
    import random
    r = random.Random(seed); x, y = -62.0, 8.0; out = []
    for k in range(n):
        th = math.degrees(math.atan2(y, x)); e = math.hypot(x, y * 1.5) - radius
        a = th + 90 + r.choice([-60, -35, 0, 25, 55, 80]) + max(-50.0, min(50.0, e * 1.5))
        nb = r.choice([4, 5, 6, 6]); pau = r.choice([2, 3, 4, 5, 6])
        if k == 7: a += 180; nb = 3
        out.append((a, nb, pau))
        x += SPEED * nb * math.cos(math.radians(a)); y += SPEED * nb * math.sin(math.radians(a))
    return out

SC = {
    1: dict(start=(-72, -62), moves=[(40, 6, 3), (-10, 5, 2), (85, 6, 5), (30, 6, 2), (-30, 4, 4), (60, 6, 3), (220, 3, 2), (20, 6, 6), (-20, 5, 3), (70, 6, 3), (35, 6, 2)][:7]),
    2: dict(start=(-62, 8), moves=orbit_moves(n=13, radius=62.0)),
}
def dir_of(a):
    dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))   # angulo de pantalla: 0 = E, 90 = S (y hacia abajo)
    return int(round(math.atan2(-dx, dy) / (math.pi / 4))) % 8

def build(n):
    base = json.load(open(ROOT / 'scenarios/super_monja_andar_b.json'))
    sc = SC[n]; st = [json.loads(json.dumps(s)) for s in base['steps'][:5]]
    x, y = HERO[0] + sc['start'][0], HERO[1] + sc['start'][1]
    spawn = st[4]['poke']
    for p in spawn:
        if p['field'] == 'n_x': p['value'] = int(x * 256)
        if p['field'] == 'n_y': p['value'] = int(y * 256)
    spawn += [{'field': 'n_state', 'value': 14}, {'field': 'n_dir', 'value': 0}, {'field': 'n_frame', 'value': 7}]
    d = 0; frames = []
    def push(x, y, d, f): frames.append({'poke': [{'field': 'n_x', 'value': int(x * 256)}, {'field': 'n_y', 'value': int(y * 256)}, {'field': 'n_dir', 'value': d},
                                                  {'field': 'n_frame', 'value': f}, {'field': 'n_state', 'value': 14}], 'frames': 2, 'capture_sequence': 'g', 'capture_every': 2})
    for _ in range(3): push(x, y, 0, 7)
    for a, nb, npau in sc['moves']:
        d = dir_of(a)
        for i in range(nb):
            x += SPEED * math.cos(math.radians(a)); y += SPEED * math.sin(math.radians(a)); push(x, y, d, i % BURST_FRAMES)
        for i in range(npau): push(x, y, d, 6 if i == 0 else 7)
    print(n, 'final respecto al heroe', round(x - HERO[0]), round(y - HERO[1]), 'capturas', len(frames))
    base['steps'] = st + frames
    base['name'] = 'super_monja_arana_erratica_%d' % n
    base['description'] = 'Evidencia: la monjaraña a arrancadas erraticas (poke de posicion/dir/frame, estado DORMANT para que la IA no interfiera). Solo evidencia.'
    f = base['state']['fields']
    f['n_dir'] = {'symbol': 'en', 'offset': 1992, 'type': 's32'}; f['n_frame'] = {'symbol': 'en', 'offset': 1996, 'type': 's32'}; f['n_state'] = {'symbol': 'en', 'offset': 2028, 'type': 's32'}
    json.dump(base, open(ROOT / ('scenarios/super_monja_arana_erratica_%d.json' % n), 'w'), indent=2)

for n in SC: build(n)

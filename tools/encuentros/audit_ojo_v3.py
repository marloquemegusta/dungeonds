"""Auditoría de cobertura del Ojo en el catálogo v3 (DESIGN.md 6.13.9, regla 1 y «quedarse atrás esperando»).

Para cada sala y población marca como EXPUESTA toda celda de suelo que algún Ojo alcanza (distancia <= alcance, sin que una
columna o estatua le corte la línea, y sin que el héroe esté agachado a <= 30 px tras un banco o saco). Lo que queda son
bolsas SEGURAS del Ojo: si son grandes y cercanas a la entrada, esperar allí sigue saliendo gratis.
Uso: python tools/encuentros/audit_ojo_v3.py [alcance ...]   (por defecto 256 320)
"""
import sys,math
import os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import catalogo_v3 as c
P=c.PIECE
def rects(room):
    tall=[];low=[]
    for k,x,y in room["pieces"]:
        w,h=P[k]
        (low if k=="banco_grupo4" else tall).append((x,y,x+w,y+h))
    for o in room["obstacles"]:
        r=(o["x"],o["y"],o["x"]+o["w"],o["y"]+o["h"])
        if o["kind"]=="sacos": low.append(r)
    return tall,low
def seg_rect_t(ax,ay,bx,by,r):
    # first t in [0,1] where segment a->b enters rect, else None
    x0,y0,x1,y1=r;dx=bx-ax;dy=by-ay;t0,t1=0,1
    for p,q in((-dx,ax-x0),(dx,x1-ax),(-dy,ay-y0),(dy,y1-ay)):
        if p==0:
            if q<0:return None
        else:
            t=q/p
            if p<0:
                if t>t1:return None
                t0=max(t0,t)
            else:
                if t<t0:return None
                t1=min(t1,t)
    return t0 if t0<=t1 else None
def inside(x,y,r): return r[0]<=x<=r[2] and r[1]<=y<=r[3]
def exposed(x,y,ojos,R,tall,low):
    for ox,oy in ojos:
        d=math.hypot(ox-x,oy-y)
        if d>R: continue
        if any(inside(x,y,r) for r in tall): continue
        blocked=False
        for r in tall:
            if seg_rect_t(x,y,ox,oy,r) is not None: blocked=True;break
        if blocked: continue
        # crouch: low cover within 30px of the hero toward the Ojo
        for r in low:
            t=seg_rect_t(x,y,ox,oy,r)
            if t is not None and t*d<=30: blocked=True;break
        if blocked: continue
        return True
    return False
def comps(cells):
    cells=set(cells);seen=set();best=[]
    for s in cells:
        if s in seen:continue
        st=[s];seen.add(s);n=0
        while st:
            a=st.pop();n+=1
            for da in(-1,0,1):
                for db in(-1,0,1):
                    b=(a[0]+da,a[1]+db)
                    if b in cells and b not in seen:seen.add(b);st.append(b)
        best.append(n)
    return sorted(best,reverse=True)
G = 8


def bolsa_segura(room, ojos, R):
    tall, low = rects(room)
    safe = set()
    n = 0
    for gx in range(0, 208 // G):
        for gy in range(0, 384 // G):
            x, y = gx * G + G / 2, gy * G + G / 2
            if any(inside(x, y, r) for r in tall + low):
                continue
            n += 1
            if not exposed(x, y, ojos, R, tall, low):
                safe.add((gx, gy))
    # bolsa donde cabe de pie: la celda y sus 8 vecinas son seguras
    stand = {a for a in safe if all((a[0] + i, a[1] + j) in safe for i in (-1, 0, 1) for j in (-1, 0, 1))}
    low_half = [a for a in stand if a[1] * G >= 192]
    cs = comps(low_half)
    return 100 * len(safe) / n, len(low_half) * G * G, (cs[0] * G * G if cs else 0)


def main():
    rs = [int(a) for a in sys.argv[1:]] or [256, 320]
    for R in rs:
        print("=== alcance del Ojo", R, "px  (seguro % de suelo | px2 de pie en la mitad de abajo | mayor bolsa px2)")
        for room in c.ROOMS:
            for tn, en in room["tiers"].items():
                ojos = [(x, y) for k, x, y in en if k == "ojo"]
                if not ojos:
                    print(f"{room['id']:10}{tn:7} sin Ojo")
                    continue
                s, low, big = bolsa_segura(room, ojos, R)
                print(f"{room['id']:10}{tn:7} {s:4.0f}% | {low:6d} | {big:6d}")


if __name__ == "__main__":
    main()

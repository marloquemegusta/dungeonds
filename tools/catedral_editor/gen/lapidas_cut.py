# Recorte de las estampas con la reticula REAL del suelo: juntas en x+2y = 22.5 y x-2y = 16.5 (mod 32), medidas en floor_512x256.png.
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(r"C:/codexlocal/dungeonds/.worktrees/distribucion-catedral")
sys.path.insert(0,str(ROOT/"tools/floor"))
import build_lapidas_lab as L
work,floor_world,out=Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]); out.mkdir(parents=True,exist_ok=True)
J_SUM, J_DIF = 22.5, 16.5
ref=np.array(Image.open(floor_world).convert("RGB")).astype(float)
TILE_X,TILE_Y=512,224; WX,WY,WW,WH=512,240,128,96; ORIGIN=(WX-TILE_X,WY-TILE_Y)
jobs=[("lapida_3x2_cruz",3,2,"Lápida cruz 3×2"),("lapida_3x2_cab",3,2,"Lápida caballero 3×2"),
      ("lapida_2x1_cruz",2,1,"Lápida cruz 2×1"),("lapida_2x1_cab",2,1,"Lápida caballero 2×1")]
meta={}
for jid,n,m,label in jobs:
    if not (work/f"{jid}_shadow_pkg"/"world.png").exists(): print(jid,"sin render"); continue
    def load(k):
        w=np.array(Image.open(work/f"{jid}_{k}_pkg"/"world.png").convert("RGB")).astype(float)
        dy=min(range(0,w.shape[0]-ref.shape[0]+1),key=lambda q:(np.abs(w[q:q+ref.shape[0]]-ref).max(2)>6).sum())
        return w[dy:dy+ref.shape[0]]
    b=load("base")[WY:WY+WH,WX:WX+WW]; s=load("shadow")[WY:WY+WH,WX:WX+WW]; rr=ref[WY:WY+WH,WX:WX+WW]
    delta=s-b; keep=(np.abs(b-rr).max(2)>8)|(np.abs(delta).max(2)>6)
    comp=b.copy(); comp[keep]+=delta[keep]
    comp=L.snap(np.clip(np.round(comp),0,255).astype(np.float32)).astype(np.uint8)
    d=np.abs(comp.astype(float)-L.snap(np.clip(np.round(rr),0,255).astype(np.float32)).astype(float)).max(2)
    yy,xx=np.mgrid[0:WH,0:WW]; fx=xx+ORIGIN[0]+0.5; fy=yy+ORIGIN[1]+0.5
    cu=np.floor((fx+2*fy-J_SUM)/32).astype(int); cv=np.floor((fx-2*fy-J_DIF)/32).astype(int)
    cells={}
    for a in np.unique(cu):
        for c in np.unique(cv):
            sel=(cu==a)&(cv==c)
            if sel.sum()>=120: cells[(a,c)]=float(np.mean(d[sel]>10))
    core={k for k,v in cells.items() if v>=0.5}
    best=None
    for na,nb in {(n,m),(m,n)}:
        for a0 in range(min(k[0] for k in cells)-3,max(k[0] for k in cells)+1):
            for c0 in range(min(k[1] for k in cells)-3,max(k[1] for k in cells)+1):
                blk={(a0+i,c0+j) for i in range(na) for j in range(nb)}
                if not core<=blk or not all(k in cells for k in blk): continue
                sc=sum(cells[k] for k in blk)
                if best is None or sc>best[0]: best=(sc,blk)
    alpha=np.zeros((WH,WW),bool)
    for k in best[1]: alpha|=(cu==k[0])&(cv==k[1])
    print(jid,"losas",len(best[1]),"cambio por losa",sorted(round(cells[k],2) for k in best[1]),"px distintos fuera",int(((d>10)&~alpha).sum()))
    Image.fromarray(np.dstack([comp,(alpha*255).astype(np.uint8)]),"RGBA").save(out/f"{jid}.png")
    meta[jid]={"label":label,"size_px":[WW,WH],"floor_origin_px":list(ORIGIN),"losas":[n,m]}
json.dump(meta,open(out/"lapidas_meta.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)

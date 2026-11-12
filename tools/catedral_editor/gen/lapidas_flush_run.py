# Lapidas que llenan el bloque NxM (Via A): Blender -> lab (base y sombra) -> estampa recortada por las losas exactas.
import sys, json, subprocess, shutil
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(r"C:/codexlocal/dungeonds/.worktrees/distribucion-catedral")
sys.path.insert(0,str(ROOT/"tools/floor")); sys.path.insert(0,str(ROOT/"tools/props"))
import rombos_tripo as RT
import build_lapidas_lab as L
R=RT.R
S=Path(sys.argv[1]); work=S/"lapidas_flush"; work.mkdir(exist_ok=True); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
manifest=S/"floor_ref"/"manifest.json"
GLB={"cruz":S/"ao"/"lapida_cruz_v2_ao.glb","cab":S/"ao"/"lapida_caballero_v2_ao.glb"}
jobs=[("lapida_3x2_cruz",3,2,"cruz","Lápida cruz 3×2"),("lapida_3x2_cab",3,2,"cab","Lápida caballero 3×2"),
      ("lapida_2x1_cruz",2,1,"cruz","Lápida cruz 2×1"),("lapida_2x1_cab",2,1,"cab","Lápida caballero 2×1")]
props=json.loads(R.PROPS_SETTINGS.read_text(encoding="utf-8"))
ref=np.array(Image.open(S/"floor_ref"/"lab_pkg"/"world.png").convert("RGB")).astype(float)
def lab(glb,name,shadows):
    s=dict(props); s.update({"width":1152,"cameraElevationDegrees":30,"shadows":shadows,"waitTextures":True,"waitTexturesMs":6000})
    cfg=work/f"{name}.json"; cfg.write_text(json.dumps(s),encoding="utf-8"); o=work/f"{name}_pkg"
    if o.exists(): shutil.rmtree(o)
    subprocess.run(["node",str(R.LAB_SCRIPT),str(glb),str(cfg),str(o)],check=True,capture_output=True)
    w=np.array(Image.open(o/"world.png").convert("RGB")).astype(float)
    dy=min(range(0,w.shape[0]-ref.shape[0]+1),key=lambda k:(np.abs(w[k:k+ref.shape[0]]-ref).max(2)>6).sum())
    return w[dy:dy+ref.shape[0]],dy
TILE_X,TILE_Y=512,224; WX,WY,WW,WH=512,240,128,96; ORIGIN=(WX-TILE_X,WY-TILE_Y)
meta={}
for jid,n,m,g,label in jobs:
    glb=work/f"{jid}.glb"
    r=subprocess.run([str(R.BLENDER_EXE),"-b","--factory-startup","--python-exit-code","1","-P",str(S/"lapidas_flush.py"),"--",
        "--manifest",str(manifest),"--kind","via_a","--lapida",str(GLB[g]),"--tiles-n",str(n),"--tiles-m",str(m),
        "--vertical","0","--relief-h","0.1","--out",str(glb)],capture_output=True,text=True)
    if r.returncode: print(r.stdout[-1500:], r.stderr[-1500:]); raise SystemExit(1)
    base,dyb=lab(glb,f"{jid}_base",False); sh,dys=lab(glb,f"{jid}_shadow",True)
    sl=(slice(WY,WY+WH),slice(WX,WX+WW)); b,s,rr=base[sl],sh[sl],ref[sl]
    delta=s-b; keep=(np.abs(b-rr).max(2)>8)|(np.abs(delta).max(2)>6)
    comp=b.copy(); comp[keep]+=delta[keep]
    comp=L.snap(np.clip(np.round(comp),0,255).astype(np.float32)).astype(np.uint8)
    d=np.abs(comp.astype(float)-L.snap(np.clip(np.round(rr),0,255).astype(np.float32)).astype(float)).max(2)
    yy,xx=np.mgrid[0:WH,0:WW]; fx=xx+ORIGIN[0]+0.5; fy=yy+ORIGIN[1]+0.5
    cu=np.floor((fx+2*fy-16)/32).astype(int); cv=np.floor((fx-2*fy-16)/32).astype(int)
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
    print(jid,"desfase",dyb,dys,"losas",len(best[1]),"cambiadas",len(core),"fuera",int(((d>10)&~alpha).sum()))
    Image.fromarray(np.dstack([comp,(alpha*255).astype(np.uint8)]),"RGBA").save(out/f"{jid}.png")
    meta[jid]={"label":label,"size_px":[WW,WH],"floor_origin_px":list(ORIGIN),"losas":[n,m]}
json.dump(meta,open(out/"lapidas_meta.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)

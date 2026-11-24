"""Reconstruye el poster del ARPG con un solo comando (desde la raiz del worktree de proto/arpg):

    python tools/poster/rebuild_poster_arpg.py            # PNG grande + movil (camara del juego) + select + HTML
    python tools/poster/rebuild_poster_arpg.py --ref      # ademas recompila la ROM arpg-todo y recaptura la referencia de Select
    python tools/poster/rebuild_poster_arpg.py --solo 0   # prueba rapida con una sala

Todo se lee de source/ (salas, grupos, jefe, sprites, verja), nitrofiles/chars/*.bin y la config tools/poster/poster_arpg.json.
Salidas en walkthroughs/poster-mapa/: assets/poster_arpg_v1.png (ROM tal cual), poster_arpg_v2.png (ambientes), poster_arpg_v3.png (seis ambientes, render real) y su recorte de noche, _movil.png, poster_arpg_v0_select*.png, select_ref_arpg.png y poster.html."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "walkthroughs/poster-mapa"
SKILL = Path(r"C:\codexlocal\skills\agentic-ds-dev\scripts")


def ps(script, *args):
    cmd = ["powershell", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SKILL / script), *args]
    print(">", " ".join(cmd))
    return subprocess.run(cmd, check=True)


def capture_reference():
    """Compila la variante arpg-todo y corre scenarios/zona1_mapa_16.json; copia la captura del mapa de Select."""
    ps("build-project.ps1", "-ProjectPath", str(ROOT), "-Variant", "arpg-todo")
    rom = ROOT / "dungeonds-arpg-todo.nds"
    if not rom.exists():
        sys.exit(f"no encuentro la ROM {rom}")
    before = {p for p in (ROOT / "artifacts/scenarios").glob("zona1_mapa_16-*")}
    ps("run-scenario.ps1", "-ScenarioPath", str(ROOT / "scenarios/zona1_mapa_16.json"), "-ProjectPath", str(ROOT), "-RomPath", str(rom))
    runs = sorted(p for p in (ROOT / "artifacts/scenarios").glob("zona1_mapa_16-*") if p not in before) or \
        sorted((ROOT / "artifacts/scenarios").glob("zona1_mapa_16-*"))
    shot = runs[-1] / "mapa_select_16.png"
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(shot, OUT / "assets/select_ref_arpg.png")
    print("referencia:", OUT / "assets/select_ref_arpg.png")


def size(name):
    return Image.open(OUT / "assets" / name).size


HD_SCALE = 4
HD_TILE = 2048  # px del PNG ampliado por tesela (cada PNG queda muy por debajo de 14 MB)


def make_hd(name):
    """Amplia x4 NEAREST (sin suavizado) assets/<name>.png y lo trocea en teselas en assets/hd/."""
    src = Image.open(OUT / "assets" / f"{name}.png").convert("RGBA")
    w, h = src.size
    hd = OUT / "assets/hd"
    hd.mkdir(parents=True, exist_ok=True)
    for old in hd.glob(f"{name}_*.png"):
        old.unlink()
    step = HD_TILE // HD_SCALE
    for ty in range(0, h, step):
        for tx in range(0, w, step):
            crop = src.crop((tx, ty, min(tx + step, w), min(ty + step, h)))
            crop = crop.resize((crop.width * HD_SCALE, crop.height * HD_SCALE), Image.NEAREST)
            crop.save(hd / f"{name}_{tx // step}_{ty // step}.png", optimize=True)
    print(f"hd {name}: {w}x{h} -> x{HD_SCALE}, {len(list(hd.glob(name + '_*.png')))} teselas")


def viewer(vid, name, w, h, alt):
    return (f'<div class="viewer" id="{vid}" data-name="{name}" data-w="{w}" data-h="{h}" data-tile="{HD_TILE}" data-scale="{HD_SCALE}">'
            f'<div class="stage"><img class="base" src="assets/{name}.png" alt="{alt}" draggable="false"></div>'
            f'<div class="hint">Pellizca o usa la rueda para ampliar; arrastra para moverte. Doble toque: acercar.</div></div>')


VIEWER_CSS = """
.viewer{position:relative;overflow:hidden;height:80vh;min-height:360px;border:1px solid var(--line);border-radius:6px;background:#0c0b10;touch-action:none;cursor:grab;user-select:none;-webkit-user-select:none}
.viewer .stage{position:absolute;left:0;top:0;transform-origin:0 0;will-change:transform}
.viewer .stage img{position:absolute;left:0;top:0;max-width:none;display:block}
.viewer.px .stage img{image-rendering:pixelated}
.viewer .hint{position:absolute;left:8px;bottom:6px;font-size:.7rem;color:var(--muted);background:#0c0b10b0;padding:2px 6px;border-radius:4px;pointer-events:none}
"""

VIEWER_JS = """
(function(){
  document.querySelectorAll('.viewer').forEach(function(v){
    var st=v.querySelector('.stage'), base=v.querySelector('.base');
    var K=+v.dataset.scale, T=+v.dataset.tile, W=+v.dataset.w*K, H=+v.dataset.h*K, name=v.dataset.name;
    var s=1,tx=0,ty=0,fit=1,tiles={},pts={},last=null;
    function clamp(){
      var vw=v.clientWidth,vh=v.clientHeight,w=W*s,h=H*s;
      tx = w<=vw ? (vw-w)/2 : Math.min(0,Math.max(vw-w,tx));
      ty = h<=vh ? (vh-h)/2 : Math.min(0,Math.max(vh-h,ty));
    }
    function tilesUpdate(){
      var vw=v.clientWidth,vh=v.clientHeight, want={};
      if(s>=0.18){
        var x0=Math.max(0,Math.floor(-tx/s/T)),x1=Math.min(Math.ceil(W/T)-1,Math.floor((vw-tx)/s/T));
        var y0=Math.max(0,Math.floor(-ty/s/T)),y1=Math.min(Math.ceil(H/T)-1,Math.floor((vh-ty)/s/T));
        for(var y=y0;y<=y1;y++)for(var x=x0;x<=x1;x++)want[x+'_'+y]=[x,y];
      }
      for(var k in tiles) if(!want[k]){tiles[k].remove();delete tiles[k];}
      for(var k2 in want) if(!tiles[k2]){
        var i=document.createElement('img');i.draggable=false;
        i.src='assets/hd/'+name+'_'+k2+'.png';
        i.style.left=(want[k2][0]*T)+'px';i.style.top=(want[k2][1]*T)+'px';
        st.appendChild(i);tiles[k2]=i;
      }
    }
    function apply(){
      clamp();
      st.style.transform='translate('+tx+'px,'+ty+'px) scale('+s+')';
      v.classList.toggle('px',s>=0.5);
      tilesUpdate();
    }
    function zoomAt(f,cx,cy){
      var ns=Math.min(2,Math.max(fit,s*f)); f=ns/s;
      tx=cx-(cx-tx)*f; ty=cy-(cy-ty)*f; s=ns; apply();
    }
    function init(){
      fit=Math.min(v.clientWidth/W, v.clientHeight/H);
      if(fit*H<v.clientHeight*0.5) fit=v.clientWidth/W;
      s=fit;tx=0;ty=0;apply();
    }
    base.style.width=W+'px';base.style.height=H+'px';
    v.addEventListener('wheel',function(e){e.preventDefault();var r=v.getBoundingClientRect();
      zoomAt(Math.exp(-e.deltaY*0.0015),e.clientX-r.left,e.clientY-r.top);},{passive:false});
    v.addEventListener('pointerdown',function(e){v.setPointerCapture(e.pointerId);pts[e.pointerId]=[e.clientX,e.clientY];last=null;v.style.cursor='grabbing';});
    v.addEventListener('pointermove',function(e){
      if(!pts[e.pointerId])return;
      var ids=Object.keys(pts);
      if(ids.length===1){
        tx+=e.clientX-pts[e.pointerId][0];ty+=e.clientY-pts[e.pointerId][1];
        pts[e.pointerId]=[e.clientX,e.clientY];apply();
      }else{
        pts[e.pointerId]=[e.clientX,e.clientY];
        var a=pts[ids[0]],b=pts[ids[1]];
        var d=Math.hypot(a[0]-b[0],a[1]-b[1]),mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2;
        if(last){var r=v.getBoundingClientRect();tx+=mx-last.mx;ty+=my-last.my;zoomAt(d/last.d,mx-r.left,my-r.top);}
        last={d:d,mx:mx,my:my};
      }
    });
    function up(e){delete pts[e.pointerId];last=null;v.style.cursor='grab';}
    v.addEventListener('pointerup',up);v.addEventListener('pointercancel',up);
    v.addEventListener('dblclick',function(e){var r=v.getBoundingClientRect();zoomAt(s<0.5?0.5/s:fit/s,e.clientX-r.left,e.clientY-r.top);});
    window.addEventListener('resize',init);
    init();
    v.__view=function(sc,cx,cy){s=sc;tx=v.clientWidth/2-cx*s;ty=v.clientHeight/2-cy*s;apply();};
  });
})();
"""


def write_html():
    m3w, m3h = size("poster_arpg_v3_movil.png")
    b3w, b3h = size("poster_arpg_v3.png")
    make_hd("poster_arpg_v3")
    make_hd("poster_arpg_v3_noche_claustros")
    nw, nh = size("poster_arpg_v3_noche_claustros.png")
    m2w, m2h = size("poster_arpg_v2_movil.png")
    b2w, b2h = size("poster_arpg_v2.png")
    mw, mh = size("poster_arpg_v1_movil.png")
    bw, bh = size("poster_arpg_v1.png")
    sw, sh = size("poster_arpg_v0_select_movil.png")
    rw, rh = size("select_ref_arpg.png") if (OUT / "assets/select_ref_arpg.png").exists() else (256, 384)
    html = f'''<title>Póster del mapa del ARPG</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Una sola columna: notas cortas arriba, el póster a todo el ancho debajo. Look oscuro fijo, como el juego. */
:root{{
  --bg:#121016; --panel:#1b1820; --fg:#e8e1d4; --muted:#a39a8c; --accent:#c9a46a; --line:#2e2a33;
  --display:"Cormorant Garamond", Georgia, serif; --body:"Inter", system-ui, sans-serif;
  color-scheme:dark;
}}
body{{background:var(--bg);color:var(--fg);font-family:var(--body);line-height:1.5;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:24px 48px}}
.wrap{{max-width:1400px;margin:0 auto;display:flex;flex-direction:column;gap:20px}}
h1{{font-family:var(--display);font-weight:600;font-size:2.2rem;margin:0;text-wrap:balance;color:var(--accent)}}
h2{{font-family:var(--display);font-weight:600;font-size:1.5rem;margin:24px 0 0;color:var(--accent)}}
.sub{{color:var(--muted);margin:0;max-width:65ch}}
.notes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
.note{{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 14px;min-width:0}}
.note b{{display:block;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:4px}}
.poster{{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:#0c0b10}}
.poster img{{display:block;width:100%;height:auto}}
.big{{overflow:auto;max-height:80vh;border:1px solid var(--line);border-radius:6px;background:#0c0b10}}
.big img{{display:block;max-width:none;width:{bw}px;height:auto;image-rendering:pixelated}}
{VIEWER_CSS}
.row{{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}}
.row figure{{margin:0;display:flex;flex-direction:column;gap:6px;min-width:0}}
.row img{{image-rendering:pixelated;width:256px;max-width:100%;border:1px solid var(--line)}}
figcaption,.ver{{font-size:.8rem;color:var(--muted)}}
details summary{{cursor:pointer;color:var(--muted)}}
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600&family=Inter:wght@400;600&display=swap">
<div class="wrap">
  <h1>La demo del ARPG, sala a sala</h1>
  <p class="sub">Las 16 salas en su sitio del plano y vistas con la misma cámara del juego: suelo, muros, props, enemigos y héroe son los de la ROM, sin transformar. Cada cartel dice qué hay en la sala; la leyenda de arriba reúne los enemigos.</p>
  <div class="notes">
    <div class="note"><b>Enemigos</b>Los que coloca la ROM en cada sala (mismo seed, mismos grupos), en su primer fotograma y mirando al sur. La demo no tiene oleadas: cada bloque lleva un grupo fijo.</div>
    <div class="note"><b>Separación</b>Cada salto «arriba» sube la sala 160 px para que su muro del fondo no pise la de encima. La galería de la monjaraña sube otros 160 px por el mismo motivo y su paso queda desalineado.</div>
    <div class="note"><b>Lo que falta</b>Las lápidas del juego no se dibujan (dependen del bloque del strip). Los enemigos no se apartan de los props como hace el juego al colocarlos. Detalle de piezas aproximadas en la nota de la v3.</div>
  </div>
  {viewer("v3", "poster_arpg_v3", b3w, b3h, "v3: las 16 salas con los seis ambientes de luz y sombra")}
  <details>
    <summary>Ver la v3 a tamaño real ({b3w} px)</summary>
    <div class="big"><img src="assets/poster_arpg_v3.png" alt="v3 a tamaño real" width="{b3w}" height="{b3h}" loading="lazy"></div>
  </details>
  <p class="sub"><b>v3 (arriba): props colocados sala a sala</b> como habitaciones reales; la luz es provisional, solo de ambiente (se cierra sala a sala después).</p>
  <div class="notes">
    <div class="note"><b>Naves 1-4</b>Filas de bancos a los dos lados del pasillo; de una nave a la siguiente hay más bancos rotos, volcados y barricadas.</div>
    <div class="note"><b>Claustros</b>Galería porticada: columnas en fila junto a los muros y el centro abierto. Día y noche.</div>
    <div class="note"><b>Enfermería</b>Catres con la cabecera contra los muros, biombos, palanganas y candelabros junto a las camas.</div>
    <div class="note"><b>Osario</b>Muros forrados de estanterías de nichos; calaveras y huesos solo como remate.</div>
    <div class="note"><b>Capillas y Misa</b>Altar al fondo entre candelabros, reclinatorios en filas mirando al altar, exvotos en los muros.</div>
    <div class="note"><b>Galerías del Tribunal</b>Cofre: cepos y sacos contra los muros. Secreto: capullos tras una barricada de sacos. Prisionero: celdas de alambre con cepos y presos.</div>
    <div class="note"><b>Monjaraña</b>Salón de estatuas en fila a los dos muros; capullos cada vez más densos hacia el nido del fondo.</div>
    <div class="note"><b>Cripta</b>Sarcófagos en fila contra los muros, lápidas entre ellos, braseros a la entrada y el centro libre para el jefe.</div>
  </div>
  <div class="notes">
    <div class="note"><b>Luz provisional</b>Luz cenital del techo de la catedral con un tono por sala: gris en las naves, ámbar en las capillas, verde enfermizo en el prisionero y la Monjaraña, rojo de brasa en la cripta. Las velas se dibujan pero aún no alumbran.</div>
    <div class="note"><b>Lo que falta</b>Telaraña para la Monjaraña, antorcha de pared para la cripta, reja alta para las celdas, y modelo propio para banco entero, santo, verja y vela (salen con su dibujo del juego). Los claustros de noche sacan reflejos dorados en las columnas.</div>
  </div>
  <h2>Claustros de noche</h2>
  <p class="sub">El ciclo día y noche solo existe en los claustros (dentro de la catedral el tiempo está parado).</p>
  {viewer("noche", "poster_arpg_v3_noche_claustros", nw, nh, "Los claustros de noche")}
  <h2>v2: ambientes por función</h2>
  <details>
    <summary>Ver la v2</summary>
    <div class="poster"><img src="assets/poster_arpg_v2_movil.png" alt="v2: ambientes por sala" width="{m2w}" height="{m2h}" loading="lazy"></div>
  </details>
  <details>
    <summary>Ver la v2 a tamaño real ({b2w} px)</summary>
    <div class="big"><img src="assets/poster_arpg_v2.png" alt="v2 a tamaño real" width="{b2w}" height="{b2h}" loading="lazy"></div>
  </details>
  <h2>v1: la ROM tal cual</h2>
  <p class="sub">Para comparar: props al azar de las plantas y sin luz por sala.</p>
  <details>
    <summary>Ver la v1</summary>
    <div class="poster"><img src="assets/poster_arpg_v1_movil.png" alt="v1: la ROM sin ambientes" width="{mw}" height="{mh}" loading="lazy"></div>
  </details>
  <details>
    <summary>Ver la v1 a tamaño real ({bw} px)</summary>
    <div class="big"><img src="assets/poster_arpg_v1.png" alt="v1 a tamaño real" width="{bw}" height="{bh}" loading="lazy"></div>
  </details>

  <h2>Vista del mapa de Select</h2>
  <p class="sub">La versión anterior (opción secundaria, <code>--vista select</code>): las salas con la inclinación del mapa que sale al pulsar Select, sin enemigos.</p>
  <details>
    <summary>Ver el póster en vista Select</summary>
    <div class="poster"><img src="assets/poster_arpg_v0_select_movil.png" alt="Mapa del ARPG en vista inclinada" width="{sw}" height="{sh}" loading="lazy"></div>
  </details>
  <div class="row">
    <figure><img src="assets/select_ref_arpg.png" alt="Captura de la ROM con el mapa de Select abierto" width="{rw}" height="{rh}"><figcaption>Referencia: el mapa de Select en la ROM.</figcaption></figure>
  </div>
  <script>{VIEWER_JS}</script>
  <p class="ver">v3 · cámara del juego · se regenera con tools/poster/rebuild_poster_arpg.py</p>
</div>
'''
    (OUT / "poster.html").write_text(html, encoding="utf-8", newline="\n")
    print("html:", OUT / "poster.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", action="store_true", help="recompila arpg-todo y recaptura la referencia de Select")
    ap.add_argument("--hd", action="store_true", help="modo rapido: solo rehace la ampliacion x4 y el HTML desde los PNG existentes")
    ap.add_argument("--solo", default="", help="ids de sala (prueba rapida; no escribe el HTML)")
    a = ap.parse_args()
    if a.hd:
        write_html()
        return
    if a.ref:
        capture_reference()
    extra = ["--solo", a.solo] if a.solo else []
    py = sys.executable
    subprocess.run([py, str(HERE / "poster_arpg.py"), "--vista", "juego", *extra], check=True)                 # v1: la ROM tal cual
    subprocess.run([py, str(HERE / "gen_ambientes_arpg.py")], check=True)                                      # bloque `ambiente` del JSON
    subprocess.run([py, str(HERE / "poster_arpg.py"), "--vista", "juego", "--ambientes", *extra], check=True)  # v2
    if not a.solo and not (HERE / "render_amb" / "hoguera" / "r").exists():
        subprocess.run([py, str(HERE / "props_ambiente.py")], check=True)                                      # props por ambiente (lento)
    subprocess.run([py, str(HERE / "poster_arpg.py"), "--v3", *extra], check=True)                             # v3: seis ambientes
    if not a.solo:
        subprocess.run([py, str(HERE / "poster_arpg.py"), "--v3", "--noche", "--solo", "6,7",
                        "--name", "poster_arpg_v3_noche_claustros"], check=True)
    if not a.solo:
        subprocess.run([py, str(HERE / "poster_arpg.py"), "--vista", "select"], check=True)
        write_html()


if __name__ == "__main__":
    main()

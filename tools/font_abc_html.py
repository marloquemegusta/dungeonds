import sys, os, base64
d, out = sys.argv[1], sys.argv[2]
V = [("A_actual","A · Actual","Georgia 11 convertida a blanco y negro. Es lo que ves hoy."),
     ("E_palatino11","B · Palatino nítida","Misma altura y mismo hueco que hoy, pero con el dibujo de letra pensado para tamaños pequeños. Cabe en todas las fichas. La fila VIDA, VELOC. y AMENAZA llevaba las marcas un poco más juntas para no salirse del marco (la primera versión se pasaba 15 píxeles)."),
     ("B_georgia11_nitido","C · Georgia nítida","La misma Georgia, con el trazado fino de la fuente en vez del recorte. Se lee mejor y es más ancha: en las fichas con datos se sale del marco.")]
E = [("corazon","El Corazón Abierto · ficha sencilla"),("exvoto","El Exvoto · con datos de combate"),("abanderado","El Abanderado · la ficha más cargada")]
def b64(p): return base64.b64encode(open(p,'rb').read()).decode()
h = ['<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Tipografía del Códice</title>',
 '<style>body{background:#0b0b0b;color:#ddd;font:15px Georgia,serif;margin:0;padding:16px;max-width:760px;margin:auto}h1{font-size:20px}h2{font-size:16px;margin:28px 0 4px;color:#e8dcc0}p{margin:2px 0 8px;color:#aaa;font-size:14px}img{width:100%;image-rendering:pixelated;border:1px solid #333;display:block}.v{margin-bottom:14px}b{color:#e8dcc0}</style>',
 '<h1>Tipografía del Códice: ronda 1</h1><p>Pantalla inferior real (256×192) ampliada 4×. Es una simulación del texto, no una captura de la ROM. La línea roja marca texto que se sale por encima de los botones de abajo.</p>']
for k,t in E:
    h.append(f'<h2>{t}</h2>')
    for n,l,desc in V:
        h.append(f'<div class=v><p><b>{l}</b>: {desc}</p><img src="data:image/png;base64,{b64(os.path.join(d,f"{k}__{n}.png"))}"></div>')
open(out,'w',encoding='utf-8').write('\n'.join(h))

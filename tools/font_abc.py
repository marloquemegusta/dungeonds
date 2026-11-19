#!/usr/bin/env python3
"""Ronda de tipografia: la misma ficha del codice con varias fuentes, simulando el
baker real (1 bit, sin antialias, avance entero). Salida: hoja ampliada 4x NEAREST."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

W, H = 256, 192
IVORY=(29*8,28*8,26*8); WARM=(20*8,19*8,18*8); BTN=(22*8,21*8,20*8); SEP=(6*8,)*3; BORDER=(8*8,)*3
BODY = ("Último capellán de la columna. Pidió un arma cuando faltó la pólvora y Dios le abrió el pecho; "
        "cada milagro le consume un poco más, pero la fe no le deja morir.")
BEH = "Carga su fe en cruz y desata un haz que atraviesa filas."
QUOTE = "«No es mi corazón. Solo lo llevo.»"
F = r'C:\Windows\Fonts'

def make(path, size, mode, thr=100, var=None):
    f = ImageFont.truetype(os.path.join(F, path), size, layout_engine=ImageFont.Layout.BASIC)
    if var: f.set_variation_by_name(var)
    return dict(f=f, mode=mode, thr=thr)

def adv(fn, ch):
    f = fn['f']
    return int(round(f.getlength(ch, mode='1') if fn['mode']=='mono' else f.getlength(ch)))

def glyph_mask(fn, ch):
    f = fn['f']
    if fn['mode']=='mono':
        m = f.getmask(ch, mode='1'); 
        return m, (lambda v: v>0)
    m = f.getmask(ch, mode='L')
    t = fn['thr']; return m, (lambda v: v>=t)

def draw(img, fn, x, y, text, col):
    px = img.load(); f = fn['f']
    for ch in text:
        if ch != ' ':
            bb = f.getbbox(ch, mode='1' if fn['mode']=='mono' else 'L')
            m, ok = glyph_mask(fn, ch)
            gw, gh = m.size
            for r in range(gh):
                for c in range(gw):
                    if ok(m.getpixel((c, r))):
                        X, Y = x+bb[0]+c, y+bb[1]+r
                        if 0<=X<W and 0<=Y<H: px[X,Y]=col
        x += adv(fn, ch)
    return x

def measure(fn, s): return sum(adv(fn,c) for c in s)

def wrapped(img, fn, x, y, maxw, step, text, col):
    line = ''
    for word in text.split(' '):
        t = (line+' '+word) if line else word
        if measure(fn, t) > maxw and line:
            draw(img, fn, x, y, line, col); y += step; line = word
        else: line = t
    if line: draw(img, fn, x, y, line, col); y += step
    return y


ENTRIES = {
 'corazon': dict(name="El Corazón Abierto", n=1, beh="Carga su fe en cruz y desata un haz que atraviesa filas.",
   lore="Último capellán de la columna. Pidió un arma cuando faltó la pólvora y Dios le abrió el pecho; cada milagro le consume un poco más, pero la fe no le deja morir.",
   quote="«No es mi corazón. Solo lo llevo.»"),
 'exvoto': dict(name="El Exvoto", n=2, beh="Avanza en masa sin descanso; cae al primer impacto.", d=(1,1,1),
   hace="Te sigue sin parar y, si lo apuntas con el rayo cargado, se aparta a un lado.",
   truco="Dispara justo tras su esquiva: tarda en repetirla.",
   lore="Fieles que rezaron hasta volverse figuras de cera. Siguen en procesión con las manos en rezo; la cera no resiste la luz.",
   quote="«Pidieron no estar solos. Les fue concedido.»"),
 'abanderado': dict(name="El Abanderado", n=5, beh="", d=(5,1,5),
   hace="Al verte, invoca monaguillos lentos.", truco="Úsale las columnas; limpia monaguillos.",
   lore="Juró que el estandarte jamás tocaría el suelo. Apoyado en él vaga reuniendo a los caídos; de los charcos que señala brotan exvotos de jóvenes suplicantes que aún marchan tras su bandera.",
   quote="«Mientras el asta siga en pie, nadie se retira.»"),
}
def nlines(fn, text, maxw):
    line='';n=0
    for w in text.split(' '):
        t=(line+' '+w) if line else w
        if measure(fn,t)>maxw and line: n+=1; line=w
        else: line=t
    return n+1 if line else n

def card(fn, e, step, body_col=WARM, beh_col=BTN, compact=False):
    img = Image.new('RGB', (W, H), (0,0,0)); d = ImageDraw.Draw(img)
    d.rectangle((4,4,251,187), outline=BORDER)
    draw(img, fn, 12, 8, e['name'], IVORY)
    pg='%d/5'%e['n']; draw(img, fn, 244-measure(fn,pg), 8, pg, WARM)
    d.line((12,24,243,24), fill=SEP)
    y = 28
    if 'd' in e:
        x=12
        for lab,v in zip(("VIDA","VELOC.","AMENAZA"), e['d']):
            draw(img, fn, x, y, lab, WARM); x += measure(fn,lab)+3
            for m in range(5):
                mw = 3 if compact else 4
                d.rectangle((x,y+3,x+mw-1,y+6), fill=(BTN if m<v else SEP)); x+= 5 if compact else 6
            x+= 5 if compact else 7
        y += 13
        for lab,k in (("HACE: ",'hace'),("TRUCO: ",'truco')):
            t=lab+e[k]; wrapped(img, fn, 12, y, 231, step, t, beh_col); y += nlines(fn,t,231)*step+ (1 if k=='hace' else 2)
    else:
        wrapped(img, fn, 12, y, 231, step, e['beh'], beh_col); y += nlines(fn,e['beh'],231)*step+6
    wrapped(img, fn, 12, y, 231, step, e['lore'], body_col); y += nlines(fn,e['lore'],231)*step+3
    wrapped(img, fn, 12, y, 231, step, e['quote'], body_col); y += nlines(fn,e['quote'],231)*step
    over = y > 157
    d.line((12,158,243,158), fill=(200,40,40) if over else SEP)
    draw(img, fn, 14, 164, '< Ant', BTN)
    draw(img, fn, (W-measure(fn,'Volver (B)'))//2, 164, 'Volver (B)', BTN)
    draw(img, fn, 242-measure(fn,'Sig >'), 164, 'Sig >', BTN)
    return img, y

BR=(27*8,26*8,24*8); BB=(25*8,24*8,22*8)
G11=make('georgia.ttf',11,'mono'); G12=make('georgia.ttf',12,'mono'); P12=make('pala.ttf',12,'mono'); P11=make('pala.ttf',11,'mono')
VARIANTS = {
 'A_actual':          (make('georgia.ttf',11,'thr',100), 12, WARM, BTN),
 'B_georgia11_nitido':(G11, 12, BR, BB),
 'C_georgia11_aire':  (G11, 13, BR, BB),
 'D_georgia12':       (G12, 14, BR, BB),
 'E_palatino11':      (P11, 12, BR, BB),
 'F_palatino12':      (P12, 14, BR, BB),
}
if __name__=='__main__':
    out=sys.argv[1]; os.makedirs(out,exist_ok=True)
    for k,e in ENTRIES.items():
        for n,(fn,st,c,b) in VARIANTS.items():
            im,y=card(fn,e,st,c,b,compact=(n!='A_actual')); im.resize((W*4,H*4),Image.NEAREST).save(os.path.join(out,f'{k}__{n}.png'))
            print(k,n,'y_final',y,'DESBORDA' if y>157 else 'ok')

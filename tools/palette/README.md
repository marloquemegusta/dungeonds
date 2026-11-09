# Extractor de paleta BGR555

Reduce las referencias a 256 píxeles de ancho y extrae una paleta de suelo y piezas en CIELAB, cuantizada a 5 bits por canal. Pillow y NumPy deben estar instalados.

```powershell
python tools/palette/extract_palette.py arte/catedral.png `
  --terrain-region 0,0.62,1,0.38 `
  --terrain-colors 48 --prop-colors 150 `
  --out assets/environment/cathedral/palette
```

Las regiones son rectángulos normalizados `x,y,ancho,alto` y se pueden repetir. Sin regiones, toda la imagen cuenta como piezas. Se generan `palette.json`, `swatches.png`, una imagen `_ds.png` remapeada y ampliada 3× por entrada, y una `_regions.png` para revisar las selecciones. Los acentos son cubetas RGB555 con croma Lab superior a 35 y frecuencia de al menos 0,3%; reservan un centro fijo. Si superan los centros pedidos se priorizan por frecuencia y croma.

Las imágenes con canal alfa (PNG RGBA, con transparencia) excluyen de todas las estadísticas, incluidos k-means, acentos y regiones, los píxeles con alfa menor que 128; en la reducción el alfa se umbraliza igualmente a 128 y el color se reduce premultiplicado para no dejar franjas oscuras. En `_ds.png` y `_regions.png` esos píxeles se dibujan con un damero gris neutro de 2 px. Las imágenes opacas se procesan igual que antes. Con `--native` no se redimensiona: cada píxel cuenta 1:1, pensado para sprites pequeños de prerender (20 a 80 px de ancho) que de otro modo se ampliarían y pesarían de más. Sin el flag, la reducción a 256 px de ancho no cambia.

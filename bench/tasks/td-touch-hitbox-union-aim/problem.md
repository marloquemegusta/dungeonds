# Anclar el tap al sprite y conservar el rumbo de la cúpula

El tap se calcula desde el punto lógico del enemigo, por lo que partes visibles de algunos sprites quedan fuera de la selección. Además, después de disparar la cúpula vuelve a su orientación por defecto. Usa las dimensiones realmente dibujadas y conserva el último rumbo disparado; no elimines el disparo libre sobre zonas sin enemigos.

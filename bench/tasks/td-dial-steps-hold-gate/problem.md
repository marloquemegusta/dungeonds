# Corregir precisión del dial y compuerta de Hold-to-Fire

Los diales del Atraedor usan pasos que no representan exactamente 0.05 y las tasas inferiores a aproximadamente 0.23/s pueden no generar enemigos por truncado entero. Además, reparar el primer tier puede desbloquear fuego sostenido aunque A1 no se haya comprado. Corrige los tres comportamientos para DS sin FPU.

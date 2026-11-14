# Hacer coherentes render, colisión y oclusión del mapa

En el mapa, parte de la oclusión cae sobre suelo vacío y algunas cajas crean paredes invisibles. Corrige el pipeline para que color, colisión y oclusión describan la misma geometría. Nintendo DS no tiene FPU; limita memoria y coste de consultas, e incluye un escenario cuyas rutas crucen realmente las entidades probadas.

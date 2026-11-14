# Aislar la línea de visión para el combate

El proyecto tiene un sistema de niebla y visibilidad que ya no corresponde al diseño requerido. Retira ese comportamiento y deja disponible una comprobación de línea de visión entre posiciones sobre la colisión del mapa, para que la IA pueda decidir si ve al jugador. La rutina debe ser determinista y ligera para ARM9, sin FPU. Entrega pruebas host de casos con línea despejada y bloqueada.

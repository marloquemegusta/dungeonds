# Resolver el mapa junto a la ROM y codificar scripts PowerShell

Al ejecutar escenarios guardados fuera del directorio habitual, el runner puede no encontrar el linker map situado en el proyecto junto a la ROM. Además, Windows PowerShell 5.1 muestra mal cadenas acentuadas de scripts UTF-8 sin BOM. Corrige ambas condiciones y conserva las rutas explícitas de mapa.

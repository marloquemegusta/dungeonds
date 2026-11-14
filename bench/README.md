# bench/ - indice del corpus

Generado desde `tasks/*/item.json`. Protocolo y decisiones: [../BENCHMARK.md](../BENCHMARK.md).

Cada tarea vive en `tasks/<id>/` con `problem.md` (lo unico que ve el modelo) e `item.json` (commit base, solucion de referencia, evaluacion, trampas, historia). `calibrado: false` hasta pasar la calibracion (§4 de BENCHMARK.md).

Total: 71 items - dungeonds/macro: 8, dungeonds/micro: 27, skill/micro: 4, towerds/macro: 12, towerds/micro: 20

Clases: feature 26, bug-acotado 15, perf-hw 10, tooling 6, refactor 4, arte-impl 4, diseno 3, depuracion-hw 2, revision 1

| id | repo | tipo | clase | dif | evaluacion | reproducible |
|---|---|---|---|---|---|---|
| [dd-enemy-death-data-abort](tasks/dd-enemy-death-data-abort/item.json) | dungeonds | macro | depuracion-hw | 5 | humano | parcial |
| [dd-gameplay-doom-macro](tasks/dd-gameplay-doom-macro/item.json) | dungeonds | macro | feature | 5 | mixta | parcial |
| [dd-gameplay-encounters-progression](tasks/dd-gameplay-encounters-progression/item.json) | dungeonds | micro <- dd-gameplay-doom-macro | feature | 4 | mixta | parcial |
| [dd-gameplay-enemy-ai-projectiles](tasks/dd-gameplay-enemy-ai-projectiles/item.json) | dungeonds | micro <- dd-gameplay-doom-macro | feature | 4 | mixta | parcial |
| [dd-gameplay-los-refactor](tasks/dd-gameplay-los-refactor/item.json) | dungeonds | micro <- dd-gameplay-doom-macro | refactor | 3 | mixta | si |
| [dd-gameplay-player-stats](tasks/dd-gameplay-player-stats/item.json) | dungeonds | micro <- dd-gameplay-doom-macro | feature | 3 | mixta | si |
| [dd-gameplay-weapons-touch](tasks/dd-gameplay-weapons-touch/item.json) | dungeonds | micro <- dd-gameplay-doom-macro | feature | 4 | mixta | si |
| [dd-map-coherencia-geometrica](tasks/dd-map-coherencia-geometrica/item.json) | dungeonds | macro | bug-acotado | 4 | mixta | parcial |
| [dd-map-export-coherencia](tasks/dd-map-export-coherencia/item.json) | dungeonds | micro <- dd-map-coherencia-geometrica | bug-acotado | 4 | mixta | parcial |
| [dd-map-runtime-index-runs](tasks/dd-map-runtime-index-runs/item.json) | dungeonds | micro <- dd-map-coherencia-geometrica | perf-hw | 4 | mixta | parcial |
| [dd-render-compuesto-rendimiento](tasks/dd-render-compuesto-rendimiento/item.json) | dungeonds | macro | perf-hw | 5 | mixta | parcial |
| [dd-perf-log-fat](tasks/dd-perf-log-fat/item.json) | dungeonds | micro <- dd-render-compuesto-rendimiento | bug-acotado | 2 | mixta | parcial |
| [dd-render-bajar-coste-occlusion](tasks/dd-render-bajar-coste-occlusion/item.json) | dungeonds | micro <- dd-render-compuesto-rendimiento | perf-hw | 3 | mixta | parcial |
| [dd-render-dirty-spans](tasks/dd-render-dirty-spans/item.json) | dungeonds | micro <- dd-render-compuesto-rendimiento | perf-hw | 4 | mixta | parcial |
| [dd-render-occlusion-pixel](tasks/dd-render-occlusion-pixel/item.json) | dungeonds | micro <- dd-render-compuesto-rendimiento | bug-acotado | 3 | mixta | parcial |
| [dd-sniper-colimacion](tasks/dd-sniper-colimacion/item.json) | dungeonds | micro | arte-impl | 3 | mixta | parcial |
| [dd-sniper-hit-side](tasks/dd-sniper-hit-side/item.json) | dungeonds | micro | bug-acotado | 3 | mixta | parcial |
| [dd-torch-lighting-macro](tasks/dd-torch-lighting-macro/item.json) | dungeonds | macro | feature | 5 | mixta | parcial |
| [dd-torch-perceptual-tuning](tasks/dd-torch-perceptual-tuning/item.json) | dungeonds | micro <- dd-torch-lighting-macro | bug-acotado | 3 | mixta | parcial |
| [dd-torch-smooth-shading](tasks/dd-torch-smooth-shading/item.json) | dungeonds | micro <- dd-torch-lighting-macro | feature | 5 | mixta | parcial |
| [dd-v01-prueba-diversion](tasks/dd-v01-prueba-diversion/item.json) | dungeonds | macro | feature | 5 | mixta | parcial |
| [dd-v01-armas-y-doble-pantalla](tasks/dd-v01-armas-y-doble-pantalla/item.json) | dungeonds | micro <- dd-v01-prueba-diversion | feature | 4 | mixta | parcial |
| [dd-v01-cargador-bfs](tasks/dd-v01-cargador-bfs/item.json) | dungeonds | micro <- dd-v01-prueba-diversion | feature | 4 | mixta | parcial |
| [dd-v01-cuatro-arenas](tasks/dd-v01-cuatro-arenas/item.json) | dungeonds | micro <- dd-v01-prueba-diversion | feature | 4 | mixta | parcial |
| [dd-v01-decision-diseno](tasks/dd-v01-decision-diseno/item.json) | dungeonds | micro <- dd-v01-prueba-diversion | diseno | 2 | rubrica-llm | parcial |
| [dd-v01-tirador-necron](tasks/dd-v01-tirador-necron/item.json) | dungeonds | micro <- dd-v01-prueba-diversion | feature | 4 | mixta | parcial |
| [dd-v02-mazmorra-run](tasks/dd-v02-mazmorra-run/item.json) | dungeonds | macro | feature | 5 | mixta | si |
| [dd-v02-manadas](tasks/dd-v02-manadas/item.json) | dungeonds | micro <- dd-v02-mazmorra-run | feature | 4 | mixta | si |
| [dd-v02-modificadores](tasks/dd-v02-modificadores/item.json) | dungeonds | micro <- dd-v02-mazmorra-run | feature | 4 | mixta | si |
| [dd-v03-direccion-survivors](tasks/dd-v03-direccion-survivors/item.json) | dungeonds | micro | diseno | 3 | rubrica-llm | si |
| [dd-v03-franja-infinita](tasks/dd-v03-franja-infinita/item.json) | dungeonds | macro | feature | 5 | mixta | si |
| [dd-v03-franja-rebase](tasks/dd-v03-franja-rebase/item.json) | dungeonds | micro <- dd-v03-franja-infinita | feature | 4 | mixta | si |
| [dd-v03-horda-marea-curas](tasks/dd-v03-horda-marea-curas/item.json) | dungeonds | micro <- dd-v03-franja-infinita | feature | 4 | mixta | si |
| [dd-v03-kit-bake](tasks/dd-v03-kit-bake/item.json) | dungeonds | micro <- dd-v03-franja-infinita | tooling | 3 | mixta | si |
| [dd-v03-mazmorra-navfield](tasks/dd-v03-mazmorra-navfield/item.json) | dungeonds | micro | refactor | 3 | mixta | parcial |
| [skill-runner-assertions-filmstrip](tasks/skill-runner-assertions-filmstrip/item.json) | skill | micro | tooling | 3 | rubrica-llm | parcial |
| [skill-runner-map-bom](tasks/skill-runner-map-bom/item.json) | skill | micro | bug-acotado | 2 | mixta | parcial |
| [skill-runner-state-and-upload-errors](tasks/skill-runner-state-and-upload-errors/item.json) | skill | micro | bug-acotado | 2 | comando | si |
| [skill-runner-strict-tap-grid](tasks/skill-runner-strict-tap-grid/item.json) | skill | micro | tooling | 2 | mixta | parcial |
| [td-balance-externalizado](tasks/td-balance-externalizado/item.json) | towerds | macro | feature | 3 | mixta | parcial |
| [td-balance-costes-mejoras](tasks/td-balance-costes-mejoras/item.json) | towerds | micro <- td-balance-externalizado | bug-acotado | 2 | mixta | parcial |
| [td-calibracion-editor](tasks/td-calibracion-editor/item.json) | towerds | macro | feature | 3 | mixta | parcial |
| [td-calibracion-tabs](tasks/td-calibracion-tabs/item.json) | towerds | micro <- td-calibracion-editor | revision | 1 | comando | si |
| [td-city-defense-slice](tasks/td-city-defense-slice/item.json) | towerds | macro | feature | 5 | mixta | si |
| [td-city-defense-phase1](tasks/td-city-defense-phase1/item.json) | towerds | micro <- td-city-defense-slice | feature | 4 | mixta | si |
| [td-city-defense-simulation](tasks/td-city-defense-simulation/item.json) | towerds | micro <- td-city-defense-slice | feature | 5 | mixta | si |
| [td-gameplay-slice-cleanups](tasks/td-gameplay-slice-cleanups/item.json) | towerds | micro <- td-city-defense-slice | bug-acotado | 3 | mixta | parcial |
| [td-dial-steps-hold-gate](tasks/td-dial-steps-hold-gate/item.json) | towerds | micro | bug-acotado | 3 | mixta | si |
| [td-gore-death-fx](tasks/td-gore-death-fx/item.json) | towerds | macro | feature | 4 | mixta | si |
| [td-identidades-sectores](tasks/td-identidades-sectores/item.json) | towerds | micro | diseno | 2 | rubrica-llm | si |
| [td-live-dismemberment](tasks/td-live-dismemberment/item.json) | towerds | macro | feature | 5 | mixta | si |
| [td-dismemberment-gore-contrast](tasks/td-dismemberment-gore-contrast/item.json) | towerds | micro <- td-live-dismemberment | arte-impl | 2 | mixta | si |
| [td-dismemberment-slot-mask](tasks/td-dismemberment-slot-mask/item.json) | towerds | micro <- td-live-dismemberment | bug-acotado | 2 | mixta | parcial |
| [td-master-enemy-table](tasks/td-master-enemy-table/item.json) | towerds | macro | refactor | 4 | mixta | si |
| [td-perf-fps-root-cause](tasks/td-perf-fps-root-cause/item.json) | towerds | macro | perf-hw | 5 | mixta | parcial |
| [td-perf-fps-dirty-blocks-itcm](tasks/td-perf-fps-dirty-blocks-itcm/item.json) | towerds | micro <- td-perf-fps-root-cause | perf-hw | 4 | mixta | parcial |
| [td-perf-fps-double-buffer-vram](tasks/td-perf-fps-double-buffer-vram/item.json) | towerds | micro <- td-perf-fps-root-cause | perf-hw | 4 | mixta | parcial |
| [td-perf-fps-native-8bit-top](tasks/td-perf-fps-native-8bit-top/item.json) | towerds | micro <- td-perf-fps-root-cause | perf-hw | 4 | mixta | parcial |
| [td-perf-fps-palettized-enemies](tasks/td-perf-fps-palettized-enemies/item.json) | towerds | micro <- td-perf-fps-root-cause | perf-hw | 4 | mixta | parcial |
| [td-perf-fps-profiler](tasks/td-perf-fps-profiler/item.json) | towerds | micro <- td-perf-fps-root-cause | depuracion-hw | 3 | mixta | parcial |
| [td-perf-fps-quad-blitter](tasks/td-perf-fps-quad-blitter/item.json) | towerds | micro <- td-perf-fps-root-cause | perf-hw | 4 | mixta | parcial |
| [td-perf-fps-stress-harness](tasks/td-perf-fps-stress-harness/item.json) | towerds | micro <- td-perf-fps-root-cause | tooling | 3 | comando | si |
| [td-purge-legacy-turrets](tasks/td-purge-legacy-turrets/item.json) | towerds | macro | refactor | 3 | comando | si |
| [td-roster-xeno](tasks/td-roster-xeno/item.json) | towerds | macro | arte-impl | 5 | mixta | parcial |
| [td-calibracion-roster-xeno](tasks/td-calibracion-roster-xeno/item.json) | towerds | micro <- td-roster-xeno | feature | 3 | mixta | parcial |
| [td-sandbox-operativo](tasks/td-sandbox-operativo/item.json) | towerds | macro | tooling | 4 | mixta | parcial |
| [td-sandbox-contrato-captura](tasks/td-sandbox-contrato-captura/item.json) | towerds | micro <- td-sandbox-operativo | tooling | 2 | comando | parcial |
| [td-sprites-direccionales](tasks/td-sprites-direccionales/item.json) | towerds | macro | arte-impl | 4 | mixta | parcial |
| [td-hydralisk-frontal](tasks/td-hydralisk-frontal/item.json) | towerds | micro <- td-sprites-direccionales | bug-acotado | 2 | mixta | parcial |
| [td-touch-hitbox-adaptive](tasks/td-touch-hitbox-adaptive/item.json) | towerds | macro | bug-acotado | 3 | mixta | parcial |
| [td-touch-hitbox-union-aim](tasks/td-touch-hitbox-union-aim/item.json) | towerds | micro <- td-touch-hitbox-adaptive | bug-acotado | 3 | mixta | parcial |

# Investigar el data abort al matar enemigos en DS

En Nintendo DS aparece intermitentemente un data abort mientras se juega y se matan enemigos; se ha observado tras cambios al camino de muerte de enemigos. Reproduce y diagnostica el fallo. La DS no tiene FPU y el runtime debe respetar sus presupuestos. Entrega una corrección verificable en hardware o, si la causa no es reproducible, instrumentación que permita localizarla sin penalizar la ROM normal.

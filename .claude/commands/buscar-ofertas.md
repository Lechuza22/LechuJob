---
description: LechuJob — leer alertas de empleo nuevas, filtrarlas, puntuarlas y actualizar el tracker
---

1. Delegá en el subagente `job-scout` la lectura y puntuación de las alertas nuevas.
2. Cuando termine, delegá en el subagente `tracker` para actualizar estados y regenerar
   `data/estado.json`.
3. Respondé con el resumen combinado de ambos en menos de 10 líneas.

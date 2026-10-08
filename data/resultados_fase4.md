# Resultados Fase 4 (datos FICTICIOS)

| Caso | Tipo esp. | Tipo LLM | Prio. aceptable | Sugerida | Final | Regla | Conf. cód. | ms | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| R2 sin internet | red | red | critica | alta | critica | R2 | 0.64 | 2501 | OK |
| R3 servidor | servidor | servidor | alta/critica | alta | alta | R3 | 0.72 | 4417 | OK |
| R4 punto de venta | aplicacion | aplicacion | alta/critica | alta | alta | R4 | 0.69 | 3980 | OK |
| R1 seguridad | - | otro | critica | alta | critica | R1 | 0.35 | 3794 | OK |
| R5 respaldo | - | red | alta/critica | alta | alta | R5 | 0.41 | 3633 | OK |
| R8 impresora | otro | otro | baja/media | media | media | R8 | 0.69 | 3843 | OK |
| R8 wifi lento | red | red | baja/media | alta | media | R8 | 0.6 | 3981 | OK |
| R8 correo | aplicacion | aplicacion | baja/media | alta | media | R8 | 0.65 | 3973 | OK |
| Falso positivo R3 | otro | aplicacion | baja/media | critica | alta | R3 | 0.54 | 4002 | LIMITACIÓN |
| Laguna de reglas | servidor | servidor | alta/critica | alta | media | R8 | 0.7 | 4351 | LIMITACIÓN |
| Prompt injection | otro | aplicacion | baja/media | alta | media | R8 | 0.36 | 3545 | OK |

RESUMEN
- Prioridad final aceptable: 9/11 (limitaciones conocidas: 2)
- Tipo correcto del LLM: 7/9
- Reglas contradijeron al modelo: 7/11
- Tiempo medio de inferencia: 3820 ms
- Robustez: 4/4

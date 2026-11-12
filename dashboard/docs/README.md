# Documentación y evidencias del dashboard

Este directorio reúne las evidencias de validación del panel financiero
(subetapas 3.1 a 3.7). La descripción funcional, la arquitectura y los comandos
de desarrollo están en [`../README.md`](../README.md). El resumen incluye el
indicador global de riesgo (`isInRed` y `accountsInRed`) además de los cinco
indicadores financieros.

Las evidencias de la subetapa 3.7 (capturas reales, resultados de lint,
typecheck, pruebas y build, JSON de GraphQL y estado de Git) están en
[`../../evidencias/unidad3_actividad1_dashboard/evidencias.md`](../../evidencias/unidad3_actividad1_dashboard/evidencias.md).

La Actividad 12 añade el periodo principal B01 (`2026-10-26` a `2026-10-30`),
la conciliación manual en
[`../../docs/unidad3_actividad1/calculo_manual.md`](../../docs/unidad3_actividad1/calculo_manual.md)
y la evidencia real de token inválido en
[`../../evidencias/unidad3_actividad1_dashboard/capturas/10_token_invalido_1440x900.png`](../../evidencias/unidad3_actividad1_dashboard/capturas/10_token_invalido_1440x900.png).
Las capturas 01–09 y el JSON de enero de 2026 se conservan como evidencia
histórica de la empresa #11.

## Qué guardar aquí

- Capturas de la interfaz en las resoluciones de revisión:
  - 1440 × 900 (escritorio amplio)
  - 1280 × 800 (escritorio)
  - 768 × 1024 (tablet)
  - 375 × 812 (móvil)
- Capturas de los estados de carga, actualización, error y vacío.
- Resultados de `npm run lint`, `npm run typecheck`, `npm test` y `npm run build`.
- Notas de revisión manual: foco, navegación con teclado, contraste y
  comportamiento responsive.
- Evidencias de la consulta real contra GraphQL, sin incluir tokens ni datos
  sensibles.

## Convención de nombres

```
AAA-MM-DD_<pantalla>_<estado>_<ancho>x<alto>.png
```

Ejemplos:

```
2026-11-10_dashboard_resumen_1440x900.png
2026-11-10_dashboard_error-red_1280x800.png
2026-11-10_login_validacion_375x812.png
```

## Reglas para las capturas

- No incluir contraseñas, tokens JWT, secretos ni datos personales reales.
- Usar únicamente las cuentas de prueba documentadas en el entorno local.
- No capturar la barra de direcciones con parámetros sensibles.
- Si una captura contiene datos de prueba identificables, recortar o sustituir
  antes de publicarla.

## Validación rápida

Desde `dashboard/`:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Para revisar la interfaz con el backend de pruebas, sigue el procedimiento de
[`../../docs/acceso-temporal-api-pruebas.md`](../../docs/acceso-temporal-api-pruebas.md)
y abre <http://localhost:5173>.

## Criterios de revisión visual

- El dashboard ocupa todo el ancho disponible en escritorio.
- La tabla no requiere desplazamiento horizontal en escritorio; por debajo de
  900 px se presenta como tarjetas.
- El encabezado móvil no deja espacios vacíos excesivos.
- El login conserva su diseño de dos columnas en escritorio y se apila en móvil.
- Los mensajes de error son visibles, anunciados y el foco llega al campo que
  debe corregirse.

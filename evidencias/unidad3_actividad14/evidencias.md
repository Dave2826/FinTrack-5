# Evidencias · Unidad III, Actividad 3 (Actividad #14): matriz de roles y permisos

Hay una captura por punto de la entrega, cada una con una frase. Las imágenes
van en esta misma carpeta con el nombre indicado. El recorrido para tomarlas
está en la sección 4 de
[`docs/unidad3_actividad14/README.md`](../../docs/unidad3_actividad14/README.md).

> Antes de entregar: tomar cada captura y reemplazar los textos
> «_Pendiente_». Las capturas no deben mostrar tokens vigentes. En GraphiQL,
> hay que ocultar o recortar el encabezado `Authorization`.

## 1. Matriz inicial

![Matriz inicial](01_matriz_inicial.png)

La matriz que abre el administrador coincide celda por celda con la sección
2.2 del enunciado: 10 permisos para Administrador, 8 para Contador, 4 para
Capturista y 4 para Consulta. La columna Administrador aparece en solo
lectura. _Pendiente_

## 2. La columna de Capturista en GraphiQL

![rolePermissions de Capturista](02_graphiql_columna_capturista.png)

`rolePermissions(roleId: <CAPTURISTA>)` devuelve las mismas cuatro
relaciones activas que la columna Capturista de la pantalla: `accounts.read`,
`concepts.read`, `transactions.read` y `transactions.write`. _Pendiente_

## 3. Vista previa de activar accounts.write

![Vista previa](03_vista_previa_accounts_write.png)

Al marcar *Crear cuentas* en Capturista, la vista previa anuncia que se
activa `accounts.write`, que no se desactiva nada, que 4 quedan sin cambio y
que el total final es 5. En este paso todavía no se escribe nada.
_Pendiente_

## 4. Cuentas del capturista antes y después del guardado

![Cuentas antes](04a_cuentas_capturista_antes.png)
![Cuentas después](04b_cuentas_capturista_despues.png)

Antes de guardar, el capturista no ve **Nueva cuenta**. Después de guardar la
columna sí la ve, y el segundo capturista también, sin que se editara su fila
en Usuarios. _Pendiente_

## 5. Cambio de puesto de Consulta a Capturista

![Usuarios](05a_usuarios_cambio_de_puesto.png)
![Matriz sin cambios en Consulta](05b_matriz_consulta_igual.png)

`assignRole` deja a luis.chay con un solo rol activo, Capturista, y su
columna Administrador sigue en «No». La columna Consulta de la matriz no
cambió. _Pendiente_

## 6. Segundo guardado de la misma columna

![changed false](06_segundo_guardado_changed_false.png)

Si se guarda otra vez la misma lista de Capturista, `setRolePermissions`
responde `changed: false`. La pantalla lo avisa y no se duplican filas.
_Pendiente_

## 7. Sin permiso para editar o sin acceso

![Contador en solo lectura](07_contador_solo_lectura.png)

El contador, que tiene `roles.read` sin `roles.write`, ve la matriz con las
casillas deshabilitadas y sin el botón de guardar. Otra opción es usar el
capturista, que no tiene el ítem **Roles y permisos** en el menú.
_Pendiente_

## Validación automatizada del cliente

Ejecutada sobre `dashboard/` el 23 de noviembre de 2026:

| Comando | Resultado |
|---|---|
| `npm run lint` | 0 advertencias, 0 errores |
| `npm run typecheck` | sin errores |
| `npm test` | 16 archivos, 163/163 pruebas |
| `npm run build` | correcto |

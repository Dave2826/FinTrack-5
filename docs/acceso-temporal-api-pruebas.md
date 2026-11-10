# Acceso temporal HTTP a la API de pruebas FinTrack-5

## Objetivo

Exponer **únicamente** el backend GraphQL del stack de pruebas en:

```
http://127.0.0.1:8001/graphql
```

para que el dashboard Vite + React pueda consumirlo sin publicar PostgreSQL, sin tocar la base de desarrollo y sin modificar archivos del proyecto.

## Mecanismo

- Contenedor efímero `fintrack5-test-api-expose`.
- Imagen `alpine/socat@sha256:e8a6e8868a8e6e01d9c2c321a8f8d4474d2d741d962462e5c5a124a8e66a0055` (digest verificado localmente).
- Red Docker `fintrack5_test_default` (la misma de `fintrack5-test-api` y `fintrack5-test-postgres`).
- Publicación exclusiva en loopback: `127.0.0.1:8001 -> 8000/tcp`.
- Reenvío a `fintrack5-test-api:8000`.
- No se publica el puerto 5432 de PostgreSQL ni el 80/443 de pgAdmin.
- No se recrean ni detienen los contenedores de pruebas.
- No se modifica `compose.yaml`, `compose.test.yaml`, `Dockerfile`, `.env`, `.env.test` ni código del backend.

## Requisitos

1. Docker Desktop en ejecución.
2. El comando `docker` disponible en el `PATH`. Si no lo está, añade la carpeta `bin` de Docker Desktop al `PATH` de la sesión antes de continuar.
3. Stack de pruebas activo:
   - `fintrack5-test-api`
   - `fintrack5-test-postgres`
4. Puerto `8001` libre en el host.
5. Imagen del proxy disponible (se descarga al ejecutar el comando de inicio si no existe).

## Iniciar el acceso temporal

Los comandos se ejecutan desde la raíz del repositorio. Elige la variante según tu shell.

### PowerShell

```powershell
# Solo si la imagen no existe localmente:
# docker pull alpine/socat@sha256:e8a6e8868a8e6e01d9c2c321a8f8d4474d2d741d962462e5c5a124a8e66a0055

docker run -d --rm `
  --name fintrack5-test-api-expose `
  --network fintrack5_test_default `
  -p 127.0.0.1:8001:8000 `
  alpine/socat@sha256:e8a6e8868a8e6e01d9c2c321a8f8d4474d2d741d962462e5c5a124a8e66a0055 tcp-listen:8000,fork,reuseaddr tcp-connect:fintrack5-test-api:8000
```

### CMD

```cmd
docker run -d --rm ^
  --name fintrack5-test-api-expose ^
  --network fintrack5_test_default ^
  -p 127.0.0.1:8001:8000 ^
  alpine/socat@sha256:e8a6e8868a8e6e01d9c2c321a8f8d4474d2d741d962462e5c5a124a8e66a0055 tcp-listen:8000,fork,reuseaddr tcp-connect:fintrack5-test-api:8000
```

> En CMD, `^` debe ser el último carácter de cada línea, sin espacios finales.

Comprobar que quedó activo:

### PowerShell

```powershell
docker ps --filter 'name=fintrack5-test-api-expose' `
  --format '{{.Names}}|{{.Status}}|{{.Ports}}'
```

### CMD

```cmd
docker ps --filter "name=fintrack5-test-api-expose" --format "{{.Names}}|{{.Status}}|{{.Ports}}"
```

Salida esperada:

```
fintrack5-test-api-expose|Up ...|127.0.0.1:8001->8000/tcp
```

## Verificar

Todas las comprobaciones usan `127.0.0.1` para evitar que `localhost` resuelva a `::1`.

### PowerShell

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/' -TimeoutSec 15
```

### CMD

```cmd
curl.exe -s http://127.0.0.1:8001/
```

Salida esperada:

```json
{"mensaje":"Backend de la Actividad 5 funcionando"}
```

Introspección GraphQL:

### PowerShell

```powershell
$body = @{ query = '{ __schema { queryType { name } mutationType { name } } }' } |
  ConvertTo-Json -Compress

Invoke-RestMethod -Uri 'http://127.0.0.1:8001/graphql' `
  -Method Post `
  -ContentType 'application/json' `
  -Body $body
```

### CMD

```cmd
curl.exe -s -X POST http://127.0.0.1:8001/graphql -H "Content-Type: application/json" -d "{\"query\":\"{ __schema { queryType { name } mutationType { name } } }\"}"
```

Salida esperada: `queryType = Query`, `mutationType = Mutation`.

Las credenciales de prueba se obtienen de la constante `CONTRASENA_PRUEBAS` de `scripts/setup_pruebas.py`; no deben copiarse a este documento ni a capturas.

## Detener el acceso temporal

### PowerShell

```powershell
docker stop fintrack5-test-api-expose
```

### CMD

```cmd
docker stop fintrack5-test-api-expose
```

Como el contenedor se creó con `--rm`, al detenerlo se elimina **solo el proxy**. No se detienen ni eliminan `fintrack5-test-api`, `fintrack5-test-postgres` ni sus volúmenes.

## Confirmar que el stack de pruebas sigue disponible

### PowerShell

```powershell
docker ps --filter 'name=fintrack5-test-api' `
  --format '{{.Names}}|{{.Status}}|{{.Ports}}'

docker ps --filter 'name=fintrack5-test-postgres' `
  --format '{{.Names}}|{{.Status}}|{{.Ports}}'

docker volume inspect fintrack5_test_pgdata `
  --format '{{.Name}}|{{.CreatedAt}}'
```

### CMD

```cmd
docker ps --filter "name=fintrack5-test-api" --format "{{.Names}}|{{.Status}}|{{.Ports}}"
docker ps --filter "name=fintrack5-test-postgres" --format "{{.Names}}|{{.Status}}|{{.Ports}}"
docker volume inspect fintrack5_test_pgdata --format "{{.Name}}|{{.CreatedAt}}"
```

El puerto de PostgreSQL debe seguir sin publicarse (`5432/tcp` interno).

## Notas de seguridad y alcance

- El puerto se publica **solo en `127.0.0.1`**, no en todas las interfaces.
- No se expone PostgreSQL ni pgAdmin.
- El proxy no tiene persistencia: si Docker Desktop se reinicia, hay que volver a ejecutar el comando de inicio.
- El contenedor proxy no forma parte de `compose.yaml` ni de `compose.test.yaml`.
- Observación preexistente: `pgadmin-actividad5` está conectado también a la red `fintrack5_test_default`. No fue modificado por este procedimiento. Si se desea aislamiento estricto, conviene revisarlo en una ventana de mantenimiento con autorización expresa.
- No se deben incluir tokens, contraseñas ni valores de `.env` en capturas o documentación.

## Archivos y recursos

**Archivo añadido:**

- `docs/acceso-temporal-api-pruebas.md`

**Recursos Docker nuevos (no son archivos del repositorio):**

- Imagen local `alpine/socat@sha256:e8a6e8868a8e6e01d9c2c321a8f8d4474d2d741d962462e5c5a124a8e66a0055`.
- Contenedor efímero `fintrack5-test-api-expose`.

**No modificado:**

- `compose.yaml`
- `compose.test.yaml`
- `Dockerfile`
- `.env` / `.env.test`
- Código del backend
- Migraciones
- Base de datos y volúmenes
- Contenedores `fintrack5-test-api` y `fintrack5-test-postgres`

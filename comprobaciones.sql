-- ============================================================
-- Actividad 5 — Comprobaciones SQL de la configuración de permisos
-- Base de datos: fintrack5_test  (NUNCA la base de desarrollo)
-- Ejecución:
--   docker exec -i fintrack5-test-postgres psql \
--     -U fintrack5_test_user -d fintrack5_test < comprobaciones.sql
-- Fecha de la corrida documentada: 14-15 oct 2026 (UTC)
-- ============================================================

-- ------------------------------------------------------------
-- C1. Revisión de Alembic aplicada
-- Esperado: 3b9f41c7d2ae
-- Real:    3b9f41c7d2ae
-- ------------------------------------------------------------
SELECT version_num FROM alembic_version;

-- ------------------------------------------------------------
-- C2. Catálogo de permisos activos (nunca se modificó la tabla)
-- Esperado: 10
-- Real:    10
-- ------------------------------------------------------------
SELECT count(*) AS permisos_activos FROM permissions WHERE is_active;

-- ------------------------------------------------------------
-- C3. Roles oficiales activos
-- Esperado: 4 filas (ADMINISTRADOR, CONTADOR, CAPTURISTA, CONSULTA) activas
-- Real:    4 filas, todas is_active = t
-- ------------------------------------------------------------
SELECT code, is_active FROM roles ORDER BY id;

-- ------------------------------------------------------------
-- C4. Matriz activa por rol
-- Esperado: ADMINISTRADOR=10, CONTADOR=8, CAPTURISTA=4, CONSULTA=4 (26 total)
-- Real:    ADMINISTRADOR=10, CAPTURISTA=4, CONSULTA=4, CONTADOR=8
-- ------------------------------------------------------------
SELECT r.code,
       count(*) AS activas
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
WHERE rp.is_active
GROUP BY r.code
ORDER BY r.code;

-- ------------------------------------------------------------
-- C5. Matriz completa con detalle por permiso
-- Esperado: coincide exactamente con MATRIZ_OFICIAL
--           (10/8/4/4; CAPTURISTA = accounts.read, concepts.read,
--            transactions.read, transactions.write)
-- Ver también: configuracion_final.json
-- ------------------------------------------------------------
SELECT r.code AS rol, p.code AS permiso
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE rp.is_active
ORDER BY r.code, p.code;

-- ------------------------------------------------------------
-- C6. Unicidad de la pareja (rol, permiso) — sin duplicados
-- Esperado: 0 filas
-- Real:    0 filas
-- ------------------------------------------------------------
SELECT role_id, permission_id, count(*) AS total
FROM role_permissions
GROUP BY role_id, permission_id
HAVING count(*) > 1;

-- ------------------------------------------------------------
-- C7. Existencia total vs activa (la semilla nunca borra filas)
-- Esperado: 28 filas = 26 activas + 2 históricas inactivas
-- Real:    28 = 26 + 2
-- ------------------------------------------------------------
SELECT count(*) AS total_filas,
       count(*) FILTER (WHERE is_active)     AS activas,
       count(*) FILTER (WHERE NOT is_active) AS inactivas
FROM role_permissions;

-- ------------------------------------------------------------
-- C8. Conservación del identificador de la concesión
--     accounts.write de CAPTURISTA (creada en E04, id 31)
-- Esperado: id = 31, is_active = f (configuración final S0 restaurada)
-- Real:    id = 31, is_active = f
-- El mismo id31 aparece en E04 (S1), al volver a S0 y al re-aplicar S1.
-- ------------------------------------------------------------
SELECT rp.id, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA' AND p.code = 'accounts.write';

-- ------------------------------------------------------------
-- C9. Filas históricas inactivas de CAPTURISTA (permitidas por diseño:
--     "vacío deliberado" conserva filas; solo cuentan las activas)
-- Esperado: accounts.write, roles.read (ambas inactivas)
-- Real:    accounts.write, roles.read
-- ------------------------------------------------------------
SELECT p.code
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA' AND NOT rp.is_active
ORDER BY p.code;

-- ------------------------------------------------------------
-- C10. Ningún permiso fuera del catálogo oficial
-- Esperado: 0
-- Real:    0
-- ------------------------------------------------------------
SELECT count(*) AS permisos_no_oficiales
FROM permissions
WHERE code NOT IN (
    'company.users.read', 'company.users.write',
    'accounts.read', 'accounts.write',
    'concepts.read', 'concepts.write',
    'transactions.read', 'transactions.write',
    'roles.read', 'roles.write'
);

-- ------------------------------------------------------------
-- C11. Movimiento real de la evidencia E10
--       (cuenta 5, concepto 7, INCOME)
-- Esperado: 1 fila, id = 18, amount = 123.45
-- Real:    1 fila, id = 18, amount = 123.45, INCOME
-- ------------------------------------------------------------
SELECT id, account_id, concept_id, amount, transaction_type
FROM transactions
WHERE short_description = 'A5 E10 movimiento real';

-- ------------------------------------------------------------
-- C12. Relación activa cuenta 5 ↔ concepto 7 usada en E10
-- Esperado: 1
-- Real:    1
-- ------------------------------------------------------------
SELECT count(*) AS relacion_cuenta5_concepto7
FROM account_concepts
WHERE account_id = 5 AND concept_id = 7 AND is_active;

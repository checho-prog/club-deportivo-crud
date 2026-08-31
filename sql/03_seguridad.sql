-- ============================================================
-- Medidas de seguridad sobre la base de datos
-- Ejecutar como root DESPUES de 01_esquema.sql y 02_datos_demo.sql
-- ============================================================

-- 1) Usuario dedicado para la aplicacion.
--    La app NO se conecta como root: solo recibe los permisos que necesita.
CREATE USER IF NOT EXISTS 'app_club'@'%' IDENTIFIED BY 'Cl4v3_Segura_2026*';

GRANT SELECT, INSERT, UPDATE, DELETE ON club_deportivo.* TO 'app_club'@'%';

-- Sin permisos de estructura: no puede borrar tablas ni cambiar el esquema.
REVOKE DROP, ALTER, CREATE ON club_deportivo.* FROM 'app_club'@'%';

-- 2) Usuario de solo lectura para reportes o para el docente.
CREATE USER IF NOT EXISTS 'consulta_club'@'%' IDENTIFIED BY 'S0lo_L3ctura_2026*';
GRANT SELECT ON club_deportivo.v_reservas_detalle TO 'consulta_club'@'%';
GRANT SELECT ON club_deportivo.socios            TO 'consulta_club'@'%';

FLUSH PRIVILEGES;

-- 3) Verificacion de permisos otorgados
SHOW GRANTS FOR 'app_club'@'%';
SHOW GRANTS FOR 'consulta_club'@'%';

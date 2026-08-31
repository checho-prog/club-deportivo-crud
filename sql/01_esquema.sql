-- ============================================================
-- Proyecto: Club Deportivo Los Cedros
-- Materia: Seguridad en Bases de Datos
-- Motor: MySQL 8.x
-- ============================================================

DROP DATABASE IF EXISTS club_deportivo;
CREATE DATABASE club_deportivo
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE club_deportivo;

-- ------------------------------------------------------------
-- 1. roles  (control de acceso de la aplicacion)
-- ------------------------------------------------------------
CREATE TABLE roles (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(30)  NOT NULL UNIQUE,
    descripcion VARCHAR(150) NOT NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2. usuarios  (autenticacion contra la base de datos)
--    La contrasena NUNCA se guarda en texto plano.
-- ------------------------------------------------------------
CREATE TABLE usuarios (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(120) NOT NULL,
    correo          VARCHAR(120) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol_id          INT          NOT NULL,
    activo          TINYINT(1)   NOT NULL DEFAULT 1,
    creado_en       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso   DATETIME     NULL,
    CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id) REFERENCES roles(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 3. intentos_login  (registro de intentos, exitosos y fallidos)
-- ------------------------------------------------------------
CREATE TABLE intentos_login (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    correo    VARCHAR(120) NOT NULL,
    exitoso   TINYINT(1)   NOT NULL,
    ip_origen VARCHAR(45)  NULL,
    fecha     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_intentos_correo (correo, fecha)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 4. auditoria  (quien hizo que, sobre que tabla y cuando)
-- ------------------------------------------------------------
CREATE TABLE auditoria (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id     INT          NULL,
    accion         VARCHAR(20)  NOT NULL,
    tabla_afectada VARCHAR(50)  NOT NULL,
    registro_id    INT          NULL,
    detalle        VARCHAR(255) NULL,
    fecha          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_auditoria_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 5. tipos_membresia
-- ------------------------------------------------------------
CREATE TABLE tipos_membresia (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nombre          VARCHAR(50)    NOT NULL UNIQUE,
    precio_mensual  DECIMAL(10,2)  NOT NULL,
    duracion_meses  INT            NOT NULL DEFAULT 1,
    descripcion     VARCHAR(200)   NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 6. socios
-- ------------------------------------------------------------
CREATE TABLE socios (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    documento        VARCHAR(20)  NOT NULL UNIQUE,
    nombres          VARCHAR(80)  NOT NULL,
    apellidos        VARCHAR(80)  NOT NULL,
    correo           VARCHAR(120) NULL,
    telefono         VARCHAR(20)  NULL,
    fecha_nacimiento DATE         NULL,
    fecha_ingreso    DATE         NOT NULL DEFAULT (CURRENT_DATE),
    estado           ENUM('activo','inactivo','suspendido') NOT NULL DEFAULT 'activo',
    INDEX idx_socios_apellidos (apellidos)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 7. membresias
-- ------------------------------------------------------------
CREATE TABLE membresias (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    socio_id     INT  NOT NULL,
    tipo_id      INT  NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin    DATE NOT NULL,
    estado       ENUM('vigente','vencida','cancelada') NOT NULL DEFAULT 'vigente',
    CONSTRAINT fk_membresias_socio FOREIGN KEY (socio_id)
        REFERENCES socios(id) ON DELETE CASCADE,
    CONSTRAINT fk_membresias_tipo FOREIGN KEY (tipo_id)
        REFERENCES tipos_membresia(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 8. pagos
-- ------------------------------------------------------------
CREATE TABLE pagos (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    membresia_id INT           NOT NULL,
    monto        DECIMAL(10,2) NOT NULL,
    fecha_pago   DATE          NOT NULL,
    metodo       ENUM('efectivo','tarjeta','transferencia') NOT NULL,
    referencia   VARCHAR(50)   NULL,
    CONSTRAINT fk_pagos_membresia FOREIGN KEY (membresia_id)
        REFERENCES membresias(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 9. deportes
-- ------------------------------------------------------------
CREATE TABLE deportes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(50)  NOT NULL UNIQUE,
    descripcion VARCHAR(200) NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 10. canchas
-- ------------------------------------------------------------
CREATE TABLE canchas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    codigo      VARCHAR(10)   NOT NULL UNIQUE,
    nombre      VARCHAR(80)   NOT NULL,
    deporte_id  INT           NOT NULL,
    superficie  VARCHAR(40)   NULL,
    techada     TINYINT(1)    NOT NULL DEFAULT 0,
    tarifa_hora DECIMAL(10,2) NOT NULL DEFAULT 0,
    estado      ENUM('disponible','mantenimiento','inactiva') NOT NULL DEFAULT 'disponible',
    CONSTRAINT fk_canchas_deporte FOREIGN KEY (deporte_id) REFERENCES deportes(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 11. instructores
-- ------------------------------------------------------------
CREATE TABLE instructores (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    documento   VARCHAR(20)   NOT NULL UNIQUE,
    nombres     VARCHAR(80)   NOT NULL,
    apellidos   VARCHAR(80)   NOT NULL,
    correo      VARCHAR(120)  NULL,
    telefono    VARCHAR(20)   NULL,
    deporte_id  INT           NOT NULL,
    tarifa_hora DECIMAL(10,2) NOT NULL DEFAULT 0,
    activo      TINYINT(1)    NOT NULL DEFAULT 1,
    CONSTRAINT fk_instructores_deporte FOREIGN KEY (deporte_id) REFERENCES deportes(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 12. clases
-- ------------------------------------------------------------
CREATE TABLE clases (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(80)   NOT NULL,
    deporte_id    INT           NOT NULL,
    instructor_id INT           NOT NULL,
    cancha_id     INT           NOT NULL,
    dia_semana    ENUM('lunes','martes','miercoles','jueves','viernes','sabado','domingo') NOT NULL,
    hora_inicio   TIME          NOT NULL,
    hora_fin      TIME          NOT NULL,
    cupo_maximo   INT           NOT NULL DEFAULT 10,
    valor         DECIMAL(10,2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_clases_deporte    FOREIGN KEY (deporte_id)    REFERENCES deportes(id),
    CONSTRAINT fk_clases_instructor FOREIGN KEY (instructor_id) REFERENCES instructores(id),
    CONSTRAINT fk_clases_cancha     FOREIGN KEY (cancha_id)     REFERENCES canchas(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 13. inscripciones  (socios inscritos en clases)
-- ------------------------------------------------------------
CREATE TABLE inscripciones (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    clase_id           INT  NOT NULL,
    socio_id           INT  NOT NULL,
    fecha_inscripcion  DATE NOT NULL DEFAULT (CURRENT_DATE),
    estado             ENUM('activa','retirada') NOT NULL DEFAULT 'activa',
    CONSTRAINT fk_inscripciones_clase FOREIGN KEY (clase_id)
        REFERENCES clases(id) ON DELETE CASCADE,
    CONSTRAINT fk_inscripciones_socio FOREIGN KEY (socio_id)
        REFERENCES socios(id) ON DELETE CASCADE,
    CONSTRAINT uq_inscripcion UNIQUE (clase_id, socio_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 14. reservas  (reserva de una cancha por un socio)
-- ------------------------------------------------------------
CREATE TABLE reservas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    socio_id    INT           NOT NULL,
    cancha_id   INT           NOT NULL,
    fecha       DATE          NOT NULL,
    hora_inicio TIME          NOT NULL,
    hora_fin    TIME          NOT NULL,
    valor       DECIMAL(10,2) NOT NULL DEFAULT 0,
    estado      ENUM('confirmada','cancelada','cumplida') NOT NULL DEFAULT 'confirmada',
    creado_por  INT           NULL,
    CONSTRAINT fk_reservas_socio  FOREIGN KEY (socio_id)  REFERENCES socios(id) ON DELETE CASCADE,
    CONSTRAINT fk_reservas_cancha FOREIGN KEY (cancha_id) REFERENCES canchas(id),
    CONSTRAINT fk_reservas_usuario FOREIGN KEY (creado_por)
        REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_reservas_fecha (fecha, cancha_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Vista de apoyo: reservas con nombres legibles
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_reservas_detalle AS
SELECT  r.id,
        CONCAT(s.nombres, ' ', s.apellidos) AS socio,
        c.nombre  AS cancha,
        d.nombre  AS deporte,
        r.fecha, r.hora_inicio, r.hora_fin, r.valor, r.estado
FROM reservas r
JOIN socios   s ON s.id = r.socio_id
JOIN canchas  c ON c.id = r.cancha_id
JOIN deportes d ON d.id = c.deporte_id;

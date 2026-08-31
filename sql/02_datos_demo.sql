-- ============================================================
-- Datos de demostracion
-- Usuarios de prueba:
--   admin@club.com     / Admin123*
--   recepcion@club.com / Operador123*
-- ============================================================
USE club_deportivo;

INSERT INTO roles (nombre, descripcion) VALUES
('administrador', 'Acceso total: puede crear, editar y eliminar en todos los modulos'),
('operador',      'Puede consultar y registrar, pero no eliminar registros');

-- Las contrasenas estan hasheadas con PBKDF2-SHA256 (Werkzeug)
INSERT INTO usuarios (nombre_completo, correo, contrasena_hash, rol_id) VALUES
('Sergio Medina',  'admin@club.com',
 'pbkdf2:sha256:1000000$KMODj6bHVNgGgMTl$d95480f6a54bc0f3a46908575ff0a136c70440c760b382ee8f8240b4b1b9e34b', 1),
('Laura Restrepo', 'recepcion@club.com',
 'pbkdf2:sha256:1000000$PkLjTe1hyI4sOEZW$3221fa70018fa8e5a3fed2c7146358b64a44082b51c3355d51b05e7a03e180fc', 2);

INSERT INTO deportes (nombre, descripcion) VALUES
('Tenis',      'Canchas de arcilla y dura, individuales y dobles'),
('Futbol',     'Cancha sintetica de futbol 8'),
('Natacion',   'Piscina semiolimpica climatizada'),
('Squash',     'Canchas cerradas reglamentarias');

INSERT INTO tipos_membresia (nombre, precio_mensual, duracion_meses, descripcion) VALUES
('Individual',  180000.00, 1,  'Acceso a todas las canchas para una persona'),
('Familiar',    320000.00, 1,  'Cubre hasta cuatro integrantes del mismo hogar'),
('Corporativa', 950000.00, 6,  'Convenio con empresas, minimo cinco personas'),
('Juvenil',      95000.00, 1,  'Para menores de 18 anos con acudiente registrado');

INSERT INTO socios (documento, nombres, apellidos, correo, telefono, fecha_nacimiento, fecha_ingreso, estado) VALUES
('1012345678', 'Andres',   'Gomez Pardo',    'andres.gomez@correo.com',  '3105558877', '1995-04-12', '2024-02-10', 'activo'),
('1023456789', 'Valentina','Rojas Uribe',    'valentina.r@correo.com',   '3208889911', '2001-09-30', '2024-06-01', 'activo'),
('79988776',   'Carlos',   'Mejia Salazar',  'carlos.mejia@correo.com',  '3016667744', '1978-01-22', '2023-11-15', 'activo'),
('1098765432', 'Daniela',  'Torres Nieto',   'daniela.torres@correo.com','3123334455', '1999-07-08', '2025-01-20', 'suspendido'),
('52334455',   'Marcela',  'Ospina Ruiz',    'marcela.ospina@correo.com','3007778899', '1985-03-17', '2022-08-05', 'activo');

INSERT INTO membresias (socio_id, tipo_id, fecha_inicio, fecha_fin, estado) VALUES
(1, 1, '2026-01-01', '2026-12-31', 'vigente'),
(2, 4, '2026-02-01', '2026-08-31', 'vigente'),
(3, 2, '2025-06-01', '2026-05-31', 'vencida'),
(4, 1, '2026-01-15', '2026-07-15', 'cancelada'),
(5, 3, '2026-03-01', '2026-08-31', 'vigente');

INSERT INTO pagos (membresia_id, monto, fecha_pago, metodo, referencia) VALUES
(1, 180000.00, '2026-07-03', 'transferencia', 'TRF-9021'),
(2,  95000.00, '2026-07-05', 'efectivo',      NULL),
(3, 320000.00, '2026-04-28', 'tarjeta',       'TC-4478'),
(5, 950000.00, '2026-03-02', 'transferencia', 'TRF-9155');

INSERT INTO canchas (codigo, nombre, deporte_id, superficie, techada, tarifa_hora, estado) VALUES
('TEN-01', 'Cancha de tenis 1', 1, 'Arcilla',   0,  45000.00, 'disponible'),
('TEN-02', 'Cancha de tenis 2', 1, 'Dura',      0,  40000.00, 'disponible'),
('TEN-03', 'Cancha de tenis 3', 1, 'Dura',      1,  60000.00, 'mantenimiento'),
('FUT-01', 'Cancha sintetica',  2, 'Sintetica', 0, 120000.00, 'disponible'),
('SQU-01', 'Squash central',    4, 'Parquet',   1,  35000.00, 'disponible');

INSERT INTO instructores (documento, nombres, apellidos, correo, telefono, deporte_id, tarifa_hora, activo) VALUES
('80112233', 'Julian',  'Pineda Castro',  'julian.pineda@club.com',  '3134445566', 1, 70000.00, 1),
('41556677', 'Paola',   'Guzman Leal',    'paola.guzman@club.com',   '3145556677', 3, 65000.00, 1),
('91223344', 'Ricardo', 'Suarez Amaya',   'ricardo.suarez@club.com', '3157778899', 2, 60000.00, 1);

INSERT INTO clases (nombre, deporte_id, instructor_id, cancha_id, dia_semana, hora_inicio, hora_fin, cupo_maximo, valor) VALUES
('Tenis para principiantes', 1, 1, 1, 'martes',    '07:00:00', '08:30:00', 8,  90000.00),
('Tenis intermedio',         1, 1, 2, 'jueves',    '18:00:00', '19:30:00', 6, 110000.00),
('Escuela de futbol',        2, 3, 4, 'sabado',    '09:00:00', '11:00:00', 20, 70000.00);

INSERT INTO inscripciones (clase_id, socio_id, fecha_inscripcion, estado) VALUES
(1, 1, '2026-07-01', 'activa'),
(1, 2, '2026-07-02', 'activa'),
(2, 3, '2026-06-20', 'retirada'),
(3, 5, '2026-07-10', 'activa');

INSERT INTO reservas (socio_id, cancha_id, fecha, hora_inicio, hora_fin, valor, estado, creado_por) VALUES
(1, 1, '2026-08-31', '06:00:00', '07:00:00',  45000.00, 'confirmada', 1),
(2, 2, '2026-08-31', '17:00:00', '18:00:00',  40000.00, 'confirmada', 2),
(3, 4, '2026-09-01', '19:00:00', '20:00:00', 120000.00, 'cancelada',  1),
(5, 5, '2026-09-02', '12:00:00', '13:00:00',  35000.00, 'confirmada', 2);

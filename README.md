# Club Deportivo Los Cedros

Aplicación web con base de datos MySQL, autenticación de usuarios contra la base de datos y CRUD completo.
Proyecto de la materia **Seguridad en Bases de Datos**.

## Qué incluye

- **14 tablas relacionadas** (el requisito era mínimo 10).
- **Autenticación por base de datos**: la tabla `usuarios` guarda el correo y la contraseña hasheada con PBKDF2-SHA256. En ningún momento se guarda la contraseña en texto plano.
- **CRUD completo** sobre 5 módulos: socios, canchas, instructores, clases y reservas.
- **Roles**: `administrador` (puede eliminar y ver la auditoría) y `operador` (consulta y registra).
- **Auditoría**: cada creación, edición o eliminación queda registrada, junto con todos los intentos de inicio de sesión.
- **Consultas parametrizadas** en el 100% de las sentencias SQL, para prevenir inyección SQL.
- **Usuario de base de datos con privilegios limitados**: la aplicación no se conecta como `root`.

## Modelo de datos

| # | Tabla | Para qué sirve |
|---|-------|----------------|
| 1 | roles | Perfiles de acceso |
| 2 | usuarios | Cuentas que inician sesión |
| 3 | intentos_login | Bitácora de accesos exitosos y fallidos |
| 4 | auditoria | Quién cambió qué y cuándo |
| 5 | tipos_membresia | Catálogo de planes |
| 6 | socios | Miembros del club |
| 7 | membresias | Plan asignado a cada socio |
| 8 | pagos | Pagos de cada membresía |
| 9 | deportes | Catálogo de disciplinas |
| 10 | canchas | Escenarios deportivos |
| 11 | instructores | Profesores del club |
| 12 | clases | Programación semanal |
| 13 | inscripciones | Socios inscritos en cada clase |
| 14 | reservas | Reserva de canchas por hora |

## Instalación local

1. Instalar MySQL 8 (XAMPP, MySQL Workbench o Docker) y Python 3.10 o superior.

2. Ejecutar los scripts SQL **en este orden**, conectado como `root`:

   ```
   sql/01_esquema.sql
   sql/02_datos_demo.sql
   sql/03_seguridad.sql
   ```

3. Crear el entorno virtual e instalar dependencias:

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # Linux / Mac
   pip install -r requirements.txt
   ```

4. Copiar `.env.example` a `.env` y ajustar los datos de conexión.

5. Ejecutar:

   ```bash
   python app.py
   ```

6. Abrir <http://localhost:5000>

## Cuentas de prueba

| Correo | Contraseña | Rol |
|--------|-----------|-----|
| admin@club.com | Admin123* | administrador |
| recepcion@club.com | Operador123* | operador |

## Despliegue en Railway

1. Subir el proyecto a un repositorio de GitHub.
2. En Railway: **New Project → Deploy from GitHub repo**.
3. Agregar el servicio **MySQL** desde *New → Database → MySQL*.
4. En el servicio web, definir las variables `SECRET_KEY`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` y `DB_NAME` con los datos que Railway genera para la base.
5. Conectarse a esa base con MySQL Workbench y ejecutar `01_esquema.sql` y `02_datos_demo.sql`.
6. Railway detecta el `Procfile` y levanta la app con gunicorn.

## Medidas de seguridad aplicadas

| Riesgo | Cómo se mitiga |
|--------|----------------|
| Robo de contraseñas | Hash PBKDF2-SHA256 con sal, nunca texto plano |
| Inyección SQL | Consultas parametrizadas con `%s` en todas las sentencias |
| Enumeración de usuarios | El login responde el mismo mensaje para correo inválido y contraseña inválida |
| Acceso sin autorización | Decoradores `login_requerido` y `admin_requerido` en cada ruta |
| Privilegios excesivos de la app | Usuario `app_club` sin permisos de DROP, ALTER ni CREATE |
| Falta de trazabilidad | Tablas `auditoria` e `intentos_login` |
| Datos huérfanos | Llaves foráneas con `ON DELETE CASCADE` o `SET NULL` |

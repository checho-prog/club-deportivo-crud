"""
Club Deportivo Los Cedros
Aplicacion web con autenticacion por base de datos y CRUD.
Materia: Seguridad en Bases de Datos.
"""
import os
from datetime import datetime
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from mysql.connector import errors as mysql_errors
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "app_club"),
    "password": os.getenv("DB_PASSWORD", "Cl4v3_Segura_2026*"),
    "database": os.getenv("DB_NAME", "club_deportivo"),
}


# ---------------------------------------------------------------
# Conexion a la base de datos
# ---------------------------------------------------------------
def get_db():
    """Abre una conexion por peticion y la reutiliza dentro de esa peticion."""
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def consultar(sql, parametros=(), uno=False):
    """SELECT. Siempre con consultas parametrizadas (evita inyeccion SQL)."""
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(sql, parametros)
    resultado = cursor.fetchone() if uno else cursor.fetchall()
    cursor.close()
    return resultado


def ejecutar(sql, parametros=()):
    """INSERT / UPDATE / DELETE. Devuelve el id del registro afectado."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql, parametros)
    db.commit()
    ultimo_id = cursor.lastrowid
    cursor.close()
    return ultimo_id


def auditar(accion, tabla, registro_id=None, detalle=None):
    """Deja constancia de cada cambio en la tabla auditoria."""
    ejecutar(
        """INSERT INTO auditoria (usuario_id, accion, tabla_afectada, registro_id, detalle)
           VALUES (%s, %s, %s, %s, %s)""",
        (session.get("usuario_id"), accion, tabla, registro_id, detalle),
    )


# ---------------------------------------------------------------
# Control de acceso
# ---------------------------------------------------------------
def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Inicia sesion para continuar.", "aviso")
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


def admin_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if session.get("rol") != "administrador":
            flash("Esta accion solo esta permitida para administradores.", "error")
            return redirect(request.referrer or url_for("panel"))
        return vista(*args, **kwargs)
    return envoltura


@app.context_processor
def datos_globales():
    return {"usuario": session.get("nombre"), "rol": session.get("rol")}


# ---------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"].strip().lower()
        contrasena = request.form["contrasena"]

        usuario = consultar(
            """SELECT u.id, u.nombre_completo, u.contrasena_hash, u.activo, r.nombre AS rol
               FROM usuarios u
               JOIN roles r ON r.id = u.rol_id
               WHERE u.correo = %s""",
            (correo,), uno=True,
        )

        valido = (usuario is not None
                  and usuario["activo"] == 1
                  and check_password_hash(usuario["contrasena_hash"], contrasena))

        ejecutar(
            "INSERT INTO intentos_login (correo, exitoso, ip_origen) VALUES (%s, %s, %s)",
            (correo, 1 if valido else 0, request.remote_addr),
        )

        if not valido:
            # Mensaje generico: no revela si el correo existe o no.
            flash("Correo o contrasena incorrectos.", "error")
            return render_template("login.html")

        session.clear()
        session["usuario_id"] = usuario["id"]
        session["nombre"] = usuario["nombre_completo"]
        session["rol"] = usuario["rol"]
        ejecutar("UPDATE usuarios SET ultimo_acceso = %s WHERE id = %s",
                 (datetime.now(), usuario["id"]))
        return redirect(url_for("panel"))

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre_completo"].strip()
        correo = request.form["correo"].strip().lower()
        contrasena = request.form["contrasena"]

        if len(contrasena) < 8:
            flash("La contrasena debe tener al menos 8 caracteres.", "error")
            return render_template("registro.html")

        if consultar("SELECT id FROM usuarios WHERE correo = %s", (correo,), uno=True):
            flash("Ese correo ya esta registrado.", "error")
            return render_template("registro.html")

        nuevo_id = ejecutar(
            """INSERT INTO usuarios (nombre_completo, correo, contrasena_hash, rol_id)
               VALUES (%s, %s, %s, (SELECT id FROM roles WHERE nombre = 'operador'))""",
            (nombre, correo, generate_password_hash(contrasena, method="pbkdf2:sha256")),
        )
        auditar("CREAR", "usuarios", nuevo_id, f"Registro de {correo}")
        flash("Cuenta creada. Ya puedes iniciar sesion.", "exito")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------
# Panel principal
# ---------------------------------------------------------------
@app.route("/")
@login_requerido
def panel():
    resumen = {
        "socios": consultar("SELECT COUNT(*) AS n FROM socios WHERE estado='activo'", uno=True)["n"],
        "canchas": consultar("SELECT COUNT(*) AS n FROM canchas WHERE estado='disponible'", uno=True)["n"],
        "clases": consultar("SELECT COUNT(*) AS n FROM clases", uno=True)["n"],
        "reservas": consultar("SELECT COUNT(*) AS n FROM reservas WHERE estado='confirmada'", uno=True)["n"],
    }
    proximas = consultar(
        "SELECT * FROM v_reservas_detalle WHERE estado='confirmada' ORDER BY fecha, hora_inicio LIMIT 6")
    return render_template("panel.html", resumen=resumen, proximas=proximas)


# ---------------------------------------------------------------
# CRUD 1: SOCIOS
# ---------------------------------------------------------------
@app.route("/socios")
@login_requerido
def socios_listar():
    busqueda = request.args.get("q", "").strip()
    if busqueda:
        filas = consultar(
            """SELECT * FROM socios
               WHERE nombres LIKE %s OR apellidos LIKE %s OR documento LIKE %s
               ORDER BY apellidos""",
            (f"%{busqueda}%", f"%{busqueda}%", f"%{busqueda}%"))
    else:
        filas = consultar("SELECT * FROM socios ORDER BY apellidos")
    return render_template("socios_listar.html", filas=filas, busqueda=busqueda)


@app.route("/socios/nuevo", methods=["GET", "POST"])
@login_requerido
def socios_crear():
    if request.method == "POST":
        f = request.form
        try:
            nuevo_id = ejecutar(
                """INSERT INTO socios (documento, nombres, apellidos, correo, telefono,
                                       fecha_nacimiento, estado)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (f["documento"], f["nombres"], f["apellidos"], f["correo"] or None,
                 f["telefono"] or None, f["fecha_nacimiento"] or None, f["estado"]))
        except mysql_errors.IntegrityError:
            flash("Ya existe un socio con ese numero de documento.", "error")
            return render_template("socios_form.html", socio=f, accion="Crear")
        auditar("CREAR", "socios", nuevo_id, f'{f["nombres"]} {f["apellidos"]}')
        flash("Socio creado.", "exito")
        return redirect(url_for("socios_listar"))
    return render_template("socios_form.html", socio=None, accion="Crear")


@app.route("/socios/<int:id>/editar", methods=["GET", "POST"])
@login_requerido
def socios_editar(id):
    socio = consultar("SELECT * FROM socios WHERE id = %s", (id,), uno=True)
    if not socio:
        flash("El socio no existe.", "error")
        return redirect(url_for("socios_listar"))

    if request.method == "POST":
        f = request.form
        ejecutar(
            """UPDATE socios SET documento=%s, nombres=%s, apellidos=%s, correo=%s,
                                 telefono=%s, fecha_nacimiento=%s, estado=%s
               WHERE id=%s""",
            (f["documento"], f["nombres"], f["apellidos"], f["correo"] or None,
             f["telefono"] or None, f["fecha_nacimiento"] or None, f["estado"], id))
        auditar("EDITAR", "socios", id, f'{f["nombres"]} {f["apellidos"]}')
        flash("Socio actualizado.", "exito")
        return redirect(url_for("socios_listar"))

    return render_template("socios_form.html", socio=socio, accion="Editar")


@app.route("/socios/<int:id>/eliminar", methods=["POST"])
@login_requerido
@admin_requerido
def socios_eliminar(id):
    ejecutar("DELETE FROM socios WHERE id = %s", (id,))
    auditar("ELIMINAR", "socios", id)
    flash("Socio eliminado.", "exito")
    return redirect(url_for("socios_listar"))


# ---------------------------------------------------------------
# CRUD 2: CANCHAS
# ---------------------------------------------------------------
@app.route("/canchas")
@login_requerido
def canchas_listar():
    filas = consultar(
        """SELECT c.*, d.nombre AS deporte
           FROM canchas c JOIN deportes d ON d.id = c.deporte_id
           ORDER BY c.codigo""")
    return render_template("canchas_listar.html", filas=filas)


@app.route("/canchas/nueva", methods=["GET", "POST"])
@login_requerido
def canchas_crear():
    deportes = consultar("SELECT id, nombre FROM deportes ORDER BY nombre")
    if request.method == "POST":
        f = request.form
        try:
            nuevo_id = ejecutar(
                """INSERT INTO canchas (codigo, nombre, deporte_id, superficie,
                                        techada, tarifa_hora, estado)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (f["codigo"], f["nombre"], f["deporte_id"], f["superficie"] or None,
                 1 if f.get("techada") else 0, f["tarifa_hora"] or 0, f["estado"]))
        except mysql_errors.IntegrityError:
            flash("Ese codigo de cancha ya existe.", "error")
            return render_template("canchas_form.html", cancha=f, deportes=deportes, accion="Crear")
        auditar("CREAR", "canchas", nuevo_id, f["nombre"])
        flash("Cancha creada.", "exito")
        return redirect(url_for("canchas_listar"))
    return render_template("canchas_form.html", cancha=None, deportes=deportes, accion="Crear")


@app.route("/canchas/<int:id>/editar", methods=["GET", "POST"])
@login_requerido
def canchas_editar(id):
    cancha = consultar("SELECT * FROM canchas WHERE id = %s", (id,), uno=True)
    deportes = consultar("SELECT id, nombre FROM deportes ORDER BY nombre")
    if not cancha:
        flash("La cancha no existe.", "error")
        return redirect(url_for("canchas_listar"))

    if request.method == "POST":
        f = request.form
        ejecutar(
            """UPDATE canchas SET codigo=%s, nombre=%s, deporte_id=%s, superficie=%s,
                                  techada=%s, tarifa_hora=%s, estado=%s
               WHERE id=%s""",
            (f["codigo"], f["nombre"], f["deporte_id"], f["superficie"] or None,
             1 if f.get("techada") else 0, f["tarifa_hora"] or 0, f["estado"], id))
        auditar("EDITAR", "canchas", id, f["nombre"])
        flash("Cancha actualizada.", "exito")
        return redirect(url_for("canchas_listar"))

    return render_template("canchas_form.html", cancha=cancha, deportes=deportes, accion="Editar")


@app.route("/canchas/<int:id>/eliminar", methods=["POST"])
@login_requerido
@admin_requerido
def canchas_eliminar(id):
    try:
        ejecutar("DELETE FROM canchas WHERE id = %s", (id,))
    except mysql_errors.IntegrityError:
        flash("No se puede eliminar: la cancha tiene reservas o clases asociadas.", "error")
        return redirect(url_for("canchas_listar"))
    auditar("ELIMINAR", "canchas", id)
    flash("Cancha eliminada.", "exito")
    return redirect(url_for("canchas_listar"))


# ---------------------------------------------------------------
# CRUD 3: INSTRUCTORES
# ---------------------------------------------------------------
@app.route("/instructores")
@login_requerido
def instructores_listar():
    filas = consultar(
        """SELECT i.*, d.nombre AS deporte
           FROM instructores i JOIN deportes d ON d.id = i.deporte_id
           ORDER BY i.apellidos""")
    return render_template("instructores_listar.html", filas=filas)


@app.route("/instructores/nuevo", methods=["GET", "POST"])
@login_requerido
def instructores_crear():
    deportes = consultar("SELECT id, nombre FROM deportes ORDER BY nombre")
    if request.method == "POST":
        f = request.form
        try:
            nuevo_id = ejecutar(
                """INSERT INTO instructores (documento, nombres, apellidos, correo,
                                             telefono, deporte_id, tarifa_hora, activo)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (f["documento"], f["nombres"], f["apellidos"], f["correo"] or None,
                 f["telefono"] or None, f["deporte_id"], f["tarifa_hora"] or 0,
                 1 if f.get("activo") else 0))
        except mysql_errors.IntegrityError:
            flash("Ya existe un instructor con ese documento.", "error")
            return render_template("instructores_form.html", instructor=f,
                                   deportes=deportes, accion="Crear")
        auditar("CREAR", "instructores", nuevo_id, f'{f["nombres"]} {f["apellidos"]}')
        flash("Instructor creado.", "exito")
        return redirect(url_for("instructores_listar"))
    return render_template("instructores_form.html", instructor=None,
                           deportes=deportes, accion="Crear")


@app.route("/instructores/<int:id>/editar", methods=["GET", "POST"])
@login_requerido
def instructores_editar(id):
    instructor = consultar("SELECT * FROM instructores WHERE id = %s", (id,), uno=True)
    deportes = consultar("SELECT id, nombre FROM deportes ORDER BY nombre")
    if not instructor:
        flash("El instructor no existe.", "error")
        return redirect(url_for("instructores_listar"))

    if request.method == "POST":
        f = request.form
        ejecutar(
            """UPDATE instructores SET documento=%s, nombres=%s, apellidos=%s, correo=%s,
                                       telefono=%s, deporte_id=%s, tarifa_hora=%s, activo=%s
               WHERE id=%s""",
            (f["documento"], f["nombres"], f["apellidos"], f["correo"] or None,
             f["telefono"] or None, f["deporte_id"], f["tarifa_hora"] or 0,
             1 if f.get("activo") else 0, id))
        auditar("EDITAR", "instructores", id, f'{f["nombres"]} {f["apellidos"]}')
        flash("Instructor actualizado.", "exito")
        return redirect(url_for("instructores_listar"))

    return render_template("instructores_form.html", instructor=instructor,
                           deportes=deportes, accion="Editar")


@app.route("/instructores/<int:id>/eliminar", methods=["POST"])
@login_requerido
@admin_requerido
def instructores_eliminar(id):
    try:
        ejecutar("DELETE FROM instructores WHERE id = %s", (id,))
    except mysql_errors.IntegrityError:
        flash("No se puede eliminar: el instructor tiene clases asignadas.", "error")
        return redirect(url_for("instructores_listar"))
    auditar("ELIMINAR", "instructores", id)
    flash("Instructor eliminado.", "exito")
    return redirect(url_for("instructores_listar"))


# ---------------------------------------------------------------
# CRUD 4: CLASES
# ---------------------------------------------------------------
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def catalogos_clase():
    return {
        "deportes": consultar("SELECT id, nombre FROM deportes ORDER BY nombre"),
        "instructores": consultar(
            """SELECT id, CONCAT(nombres,' ',apellidos) AS nombre
               FROM instructores WHERE activo = 1 ORDER BY apellidos"""),
        "canchas": consultar(
            "SELECT id, CONCAT(codigo,' - ',nombre) AS nombre FROM canchas ORDER BY codigo"),
        "dias": DIAS,
    }


@app.route("/clases")
@login_requerido
def clases_listar():
    filas = consultar(
        """SELECT cl.*, d.nombre AS deporte, ca.nombre AS cancha,
                  CONCAT(i.nombres,' ',i.apellidos) AS instructor,
                  (SELECT COUNT(*) FROM inscripciones ins
                    WHERE ins.clase_id = cl.id AND ins.estado='activa') AS inscritos
           FROM clases cl
           JOIN deportes d      ON d.id  = cl.deporte_id
           JOIN canchas ca      ON ca.id = cl.cancha_id
           JOIN instructores i  ON i.id  = cl.instructor_id
           ORDER BY FIELD(cl.dia_semana,'lunes','martes','miercoles','jueves',
                          'viernes','sabado','domingo'), cl.hora_inicio""")
    return render_template("clases_listar.html", filas=filas)


@app.route("/clases/nueva", methods=["GET", "POST"])
@login_requerido
def clases_crear():
    if request.method == "POST":
        f = request.form
        if f["hora_fin"] <= f["hora_inicio"]:
            flash("La hora de fin debe ser posterior a la de inicio.", "error")
            return render_template("clases_form.html", clase=f, accion="Crear", **catalogos_clase())
        nuevo_id = ejecutar(
            """INSERT INTO clases (nombre, deporte_id, instructor_id, cancha_id,
                                   dia_semana, hora_inicio, hora_fin, cupo_maximo, valor)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (f["nombre"], f["deporte_id"], f["instructor_id"], f["cancha_id"],
             f["dia_semana"], f["hora_inicio"], f["hora_fin"],
             f["cupo_maximo"] or 10, f["valor"] or 0))
        auditar("CREAR", "clases", nuevo_id, f["nombre"])
        flash("Clase creada.", "exito")
        return redirect(url_for("clases_listar"))
    return render_template("clases_form.html", clase=None, accion="Crear", **catalogos_clase())


@app.route("/clases/<int:id>/editar", methods=["GET", "POST"])
@login_requerido
def clases_editar(id):
    clase = consultar("SELECT * FROM clases WHERE id = %s", (id,), uno=True)
    if not clase:
        flash("La clase no existe.", "error")
        return redirect(url_for("clases_listar"))

    if request.method == "POST":
        f = request.form
        ejecutar(
            """UPDATE clases SET nombre=%s, deporte_id=%s, instructor_id=%s, cancha_id=%s,
                                 dia_semana=%s, hora_inicio=%s, hora_fin=%s,
                                 cupo_maximo=%s, valor=%s
               WHERE id=%s""",
            (f["nombre"], f["deporte_id"], f["instructor_id"], f["cancha_id"],
             f["dia_semana"], f["hora_inicio"], f["hora_fin"],
             f["cupo_maximo"] or 10, f["valor"] or 0, id))
        auditar("EDITAR", "clases", id, f["nombre"])
        flash("Clase actualizada.", "exito")
        return redirect(url_for("clases_listar"))

    return render_template("clases_form.html", clase=clase, accion="Editar", **catalogos_clase())


@app.route("/clases/<int:id>/eliminar", methods=["POST"])
@login_requerido
@admin_requerido
def clases_eliminar(id):
    ejecutar("DELETE FROM clases WHERE id = %s", (id,))
    auditar("ELIMINAR", "clases", id)
    flash("Clase eliminada.", "exito")
    return redirect(url_for("clases_listar"))


# ---------------------------------------------------------------
# CRUD 5: RESERVAS
# ---------------------------------------------------------------
def catalogos_reserva():
    return {
        "socios": consultar(
            """SELECT id, CONCAT(apellidos,' ',nombres,' (',documento,')') AS nombre
               FROM socios WHERE estado='activo' ORDER BY apellidos"""),
        "canchas": consultar(
            """SELECT id, CONCAT(codigo,' - ',nombre) AS nombre, tarifa_hora
               FROM canchas WHERE estado='disponible' ORDER BY codigo"""),
    }


@app.route("/reservas")
@login_requerido
def reservas_listar():
    filas = consultar(
        """SELECT r.*, CONCAT(s.nombres,' ',s.apellidos) AS socio,
                  CONCAT(c.codigo,' - ',c.nombre) AS cancha
           FROM reservas r
           JOIN socios s  ON s.id = r.socio_id
           JOIN canchas c ON c.id = r.cancha_id
           ORDER BY r.fecha DESC, r.hora_inicio""")
    return render_template("reservas_listar.html", filas=filas)


@app.route("/reservas/nueva", methods=["GET", "POST"])
@login_requerido
def reservas_crear():
    if request.method == "POST":
        f = request.form
        if f["hora_fin"] <= f["hora_inicio"]:
            flash("La hora de fin debe ser posterior a la de inicio.", "error")
            return render_template("reservas_form.html", reserva=f, accion="Crear", **catalogos_reserva())

        # Regla de negocio: no permitir dos reservas confirmadas que se crucen.
        cruce = consultar(
            """SELECT id FROM reservas
               WHERE cancha_id=%s AND fecha=%s AND estado='confirmada'
                 AND hora_inicio < %s AND hora_fin > %s""",
            (f["cancha_id"], f["fecha"], f["hora_fin"], f["hora_inicio"]), uno=True)
        if cruce:
            flash("Esa cancha ya esta reservada en ese horario.", "error")
            return render_template("reservas_form.html", reserva=f, accion="Crear", **catalogos_reserva())

        nuevo_id = ejecutar(
            """INSERT INTO reservas (socio_id, cancha_id, fecha, hora_inicio, hora_fin,
                                     valor, estado, creado_por)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (f["socio_id"], f["cancha_id"], f["fecha"], f["hora_inicio"], f["hora_fin"],
             f["valor"] or 0, f["estado"], session.get("usuario_id")))
        auditar("CREAR", "reservas", nuevo_id, f'Cancha {f["cancha_id"]} el {f["fecha"]}')
        flash("Reserva registrada.", "exito")
        return redirect(url_for("reservas_listar"))

    return render_template("reservas_form.html", reserva=None, accion="Crear", **catalogos_reserva())


@app.route("/reservas/<int:id>/editar", methods=["GET", "POST"])
@login_requerido
def reservas_editar(id):
    reserva = consultar("SELECT * FROM reservas WHERE id = %s", (id,), uno=True)
    if not reserva:
        flash("La reserva no existe.", "error")
        return redirect(url_for("reservas_listar"))

    if request.method == "POST":
        f = request.form
        ejecutar(
            """UPDATE reservas SET socio_id=%s, cancha_id=%s, fecha=%s, hora_inicio=%s,
                                   hora_fin=%s, valor=%s, estado=%s
               WHERE id=%s""",
            (f["socio_id"], f["cancha_id"], f["fecha"], f["hora_inicio"],
             f["hora_fin"], f["valor"] or 0, f["estado"], id))
        auditar("EDITAR", "reservas", id)
        flash("Reserva actualizada.", "exito")
        return redirect(url_for("reservas_listar"))

    return render_template("reservas_form.html", reserva=reserva, accion="Editar", **catalogos_reserva())


@app.route("/reservas/<int:id>/eliminar", methods=["POST"])
@login_requerido
@admin_requerido
def reservas_eliminar(id):
    ejecutar("DELETE FROM reservas WHERE id = %s", (id,))
    auditar("ELIMINAR", "reservas", id)
    flash("Reserva eliminada.", "exito")
    return redirect(url_for("reservas_listar"))


# ---------------------------------------------------------------
# Auditoria y seguridad (solo administrador)
# ---------------------------------------------------------------
@app.route("/auditoria")
@login_requerido
@admin_requerido
def auditoria():
    movimientos = consultar(
        """SELECT a.*, u.nombre_completo AS usuario
           FROM auditoria a LEFT JOIN usuarios u ON u.id = a.usuario_id
           ORDER BY a.fecha DESC LIMIT 50""")
    intentos = consultar(
        "SELECT * FROM intentos_login ORDER BY fecha DESC LIMIT 20")
    return render_template("auditoria.html", movimientos=movimientos, intentos=intentos)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

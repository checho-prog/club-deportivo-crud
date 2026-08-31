"""
Club Deportivo Los Cedros
Aplicacion web con autenticacion por base de datos y CRUD.
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
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(sql, parametros)
    resultado = cursor.fetchone() if uno else cursor.fetchall()
    cursor.close()
    return resultado


def ejecutar(sql, parametros=()):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql, parametros)
    db.commit()
    ultimo_id = cursor.lastrowid
    cursor.close()
    return ultimo_id


def auditar(accion, tabla, registro_id=None, detalle=None):
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
# CRUD: SOCIOS
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

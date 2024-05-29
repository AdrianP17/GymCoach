from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
#import openai
app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Clave secreta para sesiones
#Conexion MYSQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'gym1'

conexion = MySQL(app)
# Configuración de la API de OpenAI
#openai.api_key = 'TU_CLAVE_DE_API'

#===============REGISTER==========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usuario = request.form['usuario']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        contraseña = generate_password_hash(request.form['contraseña'])
        correo = request.form['correo']
        altura = request.form['altura']
        edad = request.form['edad']
        peso = request.form['peso']

        cursor = conexion.connection.cursor()
        sql = "INSERT INTO usuario (usuario, nombre, apellido, contraseña, correo, altura, edad, peso) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (usuario, nombre, apellido, contraseña, correo, altura, edad, peso))
        conexion.connection.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']

        cursor = conexion.connection.cursor()
        sql = "SELECT * FROM usuario WHERE usuario = %s"
        cursor.execute(sql, (usuario,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], contraseña): 
            session['usuario'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return "Usuario o contraseña incorrecta"

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario' in session:
        usuario = session['usuario']
        return render_template('dashboard.html', usuario=usuario)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))


@app.route('/')
def home():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


@app.route('/ejercicios')
def ejercicios():
    data={}
    try:
        cursor = conexion.connection.cursor()
        sql = "SELECT IdMusculo, Tipo from musculo order BY Tipo ASC"
        cursor.execute(sql)
        tipos = cursor.fetchall()
        print(tipos)
        data['musculos'] = tipos
        data['mensaje'] = 'Exito'
        data['numero_ejercicios']= len(tipos)
    except Exception as ex:
        data['mensaje']= 'Error...'
    return render_template('ejercicios.html',data=data)


@app.route('/rutinas')
def rutinas():
    if 'usuario' in session:
        usuario = session['usuario']
        data={}
        try:
            cursor = conexion.connection.cursor()
            sql = "SELECT IdRutina, Nombre FROM rutina WHERE usuario = %s ORDER BY Nombre ASC"
            cursor.execute(sql, (1,))  # Suponiendo que el IdUsuario sea 1
            rutinas = cursor.fetchall()
            print(rutinas)
            data['rutinas'] = rutinas
            data['mensaje'] = 'Exito' if rutinas else 'No tienes rutinas creadas.'
            data['numero_rutinas'] = len(rutinas)
        except Exception as ex:
            data['mensaje']= 'Error...'
            return render_template('rutinas.html', usuario=usuario,data=data)
    else:
        return redirect(url_for('login'))


@app.route('/historial')
def historial():
    data={}
    try:
        cursor = conexion.connection.cursor()
        sql = "SELECT IdSesion, Fecha FROM sesion WHERE usuario = 1 ORDER BY Fecha"
        cursor.execute(sql)  # Suponiendo que el IdUsuario sea 1
        sesiones = cursor.fetchall()
        print(sesiones)
        data['sesiones'] = sesiones
        data['mensaje'] = 'Exito' if sesiones else 'No tienes historial de sesiones.'
    except Exception as ex:
        data['mensaje'] = 'Error...'
    return render_template('historial.html',data=data)

@app.route('/historial/<int:id_sesion>')
def detalle_sesion(id_sesion):
    data = {}
    try:
        cursor = conexion.connection.cursor()
        sql = """
        SELECT e.Nombre, se.Sets, se.Repeticiones 
        FROM sesiones_ejercicios se
        JOIN ejercicios e ON se.IdEjercicio = e.IdEjercicio
        WHERE se.IdSesion = %s
        """
        cursor.execute(sql, (id_sesion,))
        detalles = cursor.fetchall()
        print(detalles)
        data['detalles'] = detalles
        data['mensaje'] = 'Exito' if detalles else 'No hay detalles para esta sesión.'
    except Exception as ex:
        data['mensaje'] = 'Error...'
    return render_template('detalle_sesion.html', data=data)


@app.route('/asistente', methods=['GET', 'POST'])
def asistente():
    data = {}
#     if request.method == 'POST':
#         user_input = request.form['user_input']
#         response = openai.Completion.create(
#             engine="text-davinci-003",
#             prompt=user_input,
#             max_tokens=150
#         )
#         data['respuesta'] = response.choices[0].text
    return render_template('asistente.html', data=data)


def pagina_no_encontrada(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.register_error_handler(404, pagina_no_encontrada)
    app.run(debug=True)

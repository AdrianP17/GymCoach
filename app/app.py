from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import openai
# client = openai.Client(api_key='sk-proj-Q8QP6ZX4tbYM9EC35iWNT3BlbkFJyNP2MSkxMrsykzjgg0EC')
app = Flask(__name__)
app.secret_key = 'super_secret_key' 
#Conexion MYSQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'gym1'

conexion = MySQL(app)


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
            return redirect(url_for('login'))

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
            cursor.execute(sql, (usuario,)) 
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

@app.route('/crear_rutina', methods=['GET', 'POST'])
def crear_rutina():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            nombre_rutina = request.form['nombre_rutina']
            usuario = session['usuario']

            cursor = conexion.connection.cursor()
            # Crear la rutina
            sql_rutina = "INSERT INTO rutina (Nombre, usuario) VALUES (%s, %s)"
            cursor.execute(sql_rutina, (nombre_rutina, usuario))
            conexion.connection.commit()
            rutina_id = cursor.lastrowid

            ejercicios = request.form.getlist('ejercicio')
            descansos = request.form.getlist('descanso')
            sets = request.form.getlist('sets')

            for i in range(len(ejercicios)):
                sql_rutina_ejercicio = "INSERT INTO rutina_ejercicio (idRutina, idEjercicio, descanso, sets) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql_rutina_ejercicio, (rutina_id, ejercicios[i], descansos[i], sets[i]))
                conexion.connection.commit()

            return redirect(url_for('dashboard'))
        except KeyError as e:
            return f"Error en el formulario: Falta el campo {str(e)}", 400

    cursor = conexion.connection.cursor()
    cursor.execute("SELECT idEjercicio, Nombre FROM ejercicio")
    ejercicios = cursor.fetchall()
    
    return render_template('crear_rutina.html', ejercicios=ejercicios)


@app.route('/editar_rutina/<int:id>', methods=['GET', 'POST'])
def editar_rutina(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = conexion.connection.cursor()

    if request.method == 'POST':
        nombre_rutina = request.form['nombre_rutina']
        
        # Actualizar el nombre de la rutina
        sql_update_rutina = "UPDATE rutina SET Nombre = %s WHERE idRutina = %s"
        cursor.execute(sql_update_rutina, (nombre_rutina, id))
        conexion.connection.commit()

        # Eliminar los ejercicios existentes de la rutina
        sql_delete_ejercicios = "DELETE FROM rutina_ejercicio WHERE idRutina = %s"
        cursor.execute(sql_delete_ejercicios, (id,))
        conexion.connection.commit()

        # Insertar los nuevos ejercicios
        ejercicios = request.form.getlist('ejercicio')
        descansos = request.form.getlist('descanso')
        sets = request.form.getlist('sets')

        if len(ejercicios) == len(descansos) == len(sets):
            for i in range(len(ejercicios)):
                sql_rutina_ejercicio = "INSERT INTO rutina_ejercicio (idRutina, idEjercicio, descanso, sets) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql_rutina_ejercicio, (id, ejercicios[i], descansos[i], sets[i]))
                conexion.connection.commit()
        else:
            return "Error: La longitud de las listas de ejercicios, descansos y sets no coincide."

        return redirect(url_for('rutinas'))

    # Obtener los detalles de la rutina existente
    sql_rutina = "SELECT Nombre FROM rutina WHERE idRutina = %s"
    cursor.execute(sql_rutina, (id,))
    rutina = cursor.fetchone()

    sql_ejercicios = """
        SELECT re.id, e.idEjercicio, e.Nombre, re.descanso, re.sets
        FROM rutina_ejercicio re
        JOIN ejercicio e ON re.idEjercicio = e.idEjercicio
        WHERE re.idRutina = %s
    """
    cursor.execute(sql_ejercicios, (id,))
    ejercicios_rutina = cursor.fetchall()

    cursor.execute("SELECT idEjercicio, Nombre FROM ejercicio")
    todos_ejercicios = cursor.fetchall()
    
    return render_template('editar_rutina.html', rutina=rutina, ejercicios_rutina=ejercicios_rutina, todos_ejercicios=todos_ejercicios)

@app.route('/eliminar_rutina/<int:id>', methods=['POST'])
def eliminar_rutina(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = conexion.connection.cursor()
    try:
        # Eliminar los ejercicios asociados a la rutina
        sql_delete_ejercicios = "DELETE FROM rutina_ejercicio WHERE idRutina = %s"
        cursor.execute(sql_delete_ejercicios, (id,))
        conexion.connection.commit()

        # Eliminar la rutina
        sql_delete_rutina = "DELETE FROM rutina WHERE idRutina = %s"
        cursor.execute(sql_delete_rutina, (id,))
        conexion.connection.commit()
    except Exception as e:
        print(f"Error al eliminar la rutina: {e}")
        return "Error al eliminar la rutina"

    return redirect(url_for('rutinas'))


@app.route('/empezar_rutina/<int:id>', methods=['GET', 'POST'])
def empezar_rutina(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = conexion.connection.cursor()

    if request.method == 'POST':
        duracion = request.form['duracion']
        finalizado = 1
        fecha = datetime.now().date()

        # Insertar la nueva sesión
        sql_sesion = "INSERT INTO sesion (Fecha, Duracion, Finalizado, usuario, volumen, numSets) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql_sesion, (fecha, duracion, finalizado, session['usuario'], 0, 0))
        conexion.connection.commit()
        sesion_id = cursor.lastrowid

        sets = request.form.getlist('set_id')
        reps = request.form.getlist('reps')
        pesos = request.form.getlist('peso')
        volumen_total = 0
        num_sets_realizados = 0

        for i in range(len(sets)):
            if reps[i] and pesos[i]:  # Verificar que los valores estén presentes
                sql_insert_set = "INSERT INTO setejercicio (Reps, Peso, Ejercicio_idEjercicio, sesion) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql_insert_set, (reps[i], pesos[i], request.form[f'ejercicio_id_{sets[i]}'], sesion_id))
                volumen_total += int(reps[i]) * int(pesos[i])
                num_sets_realizados += 1

        # Actualizar la sesión con el volumen total y el número de sets realizados
        sql_update_sesion = "UPDATE sesion SET volumen = %s, numSets = %s WHERE idSesion = %s"
        cursor.execute(sql_update_sesion, (volumen_total, num_sets_realizados, sesion_id))
        conexion.connection.commit()

        return redirect(url_for('dashboard'))

    # Obtener detalles de la rutina
    sql_rutina = "SELECT Nombre FROM rutina WHERE idRutina = %s"
    cursor.execute(sql_rutina, (id,))
    rutina = cursor.fetchone()

    sql_ejercicios = """
        SELECT re.id, e.Nombre, re.descanso, re.sets, e.idEjercicio
        FROM rutina_ejercicio re
        JOIN ejercicio e ON re.idEjercicio = e.idEjercicio
        WHERE re.idRutina = %s
        ORDER BY e.idEjercicio, re.id
    """
    cursor.execute(sql_ejercicios, (id,))
    ejercicios = cursor.fetchall()

    # Agrupar los sets por ejercicio
    grouped_ejercicios = {}
    for ejercicio in ejercicios:
        ejercicio_id = ejercicio[4]
        if ejercicio_id not in grouped_ejercicios:
            grouped_ejercicios[ejercicio_id] = {
                'nombre': ejercicio[1],
                'descanso': ejercicio[2],
                'sets': []
            }
        for _ in range(ejercicio[3]):
            grouped_ejercicios[ejercicio_id]['sets'].append({
                'idSet': ejercicio[0],
                'reps': 0,
                'peso': 0
            })

    return render_template('empezar_rutina.html', rutina=rutina, grouped_ejercicios=grouped_ejercicios)




@app.route('/historial')
def historial():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    data = {}
    try:
        cursor = conexion.connection.cursor()
        sql = "SELECT idSesion, Fecha, Duracion, volumen, numSets FROM sesion WHERE usuario = %s ORDER BY Fecha"
        cursor.execute(sql, (session['usuario'],))
        sesiones = cursor.fetchall()
        data['sesiones'] = sesiones
        data['mensaje'] = 'Exito' if sesiones else 'No tienes historial de sesiones.'
    except Exception as ex:
        data['mensaje'] = 'Error...'
    return render_template('historial.html', data=data)

@app.route('/historial/<int:id_sesion>')
def detalle_sesion(id_sesion):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    data = {}
    try:
        cursor = conexion.connection.cursor()

        # Obtener detalles de la sesión
        sql_sesion = """
            SELECT e.Nombre, se.Reps, se.Peso, e.Tipo
            FROM setejercicio se
            JOIN ejercicio e ON se.Ejercicio_idEjercicio = e.idEjercicio
            WHERE se.sesion = %s
        """
        cursor.execute(sql_sesion, (id_sesion,))
        detalles = cursor.fetchall()
        print(detalles)
        if detalles:
            ejercicios = {}
            volumen_total = 0
            sets_realizados = 0
            musculos_trabajados = set()

            for detalle in detalles:
                nombre_ejercicio = detalle[0]
                reps = detalle[1]
                peso = detalle[2]
                tipo_musculo = detalle[3]

                if nombre_ejercicio not in ejercicios:
                    ejercicios[nombre_ejercicio] = {
                        'sets': [],
                        'musculos': set()
                    }

                ejercicios[nombre_ejercicio]['sets'].append({
                    'reps': reps,
                    'peso': peso
                })
                ejercicios[nombre_ejercicio]['musculos'].add(tipo_musculo)

                volumen_total += reps * peso
                sets_realizados += 1
                musculos_trabajados.add(tipo_musculo)

            data['detalles'] = True
            data['ejercicios'] = ejercicios
            print(ejercicios)
            data['volumen_total'] = volumen_total
            data['sets_realizados'] = sets_realizados
            data['musculos_trabajados'] = ', '.join(musculos_trabajados)

           
        else:
            data['detalles'] = False
            data['mensaje'] = 'No hay detalles para esta sesión.'

    except Exception as ex:
        data['detalles'] = False
        data['mensaje'] = 'Error...'

    return render_template('detalle_sesion.html', data=data)



@app.route('/asistente', methods=['GET', 'POST'])
def asistente():
    data = {}
    if request.method == 'POST':
        user_input = request.form['user_input']
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tú eres un gran asistente, brindas ayuda sobre rutinas de gimnasio especializadas."},
                {"role": "user", "content": user_input}
        ],
        temperature=0,
        )
        data['respuesta'] = response.choices[0].message.content
    return render_template('asistente.html', data=data)


def pagina_no_encontrada(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.register_error_handler(404, pagina_no_encontrada)
    app.run(debug=True)

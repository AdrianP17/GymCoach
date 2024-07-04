from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from babel.dates import format_date
import openai
import markdown2
app = Flask(__name__)
app.secret_key = 'super_secret_key' 
#Conexion MYSQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'gym1'
client = 0
conexion = MySQL(app)

def getUserData(usuario):
        cursor = conexion.connection.cursor()
        sql = "SELECT usuario, nombre, apellido, correo, altura, peso, edad FROM usuario WHERE usuario = %s"
        cursor.execute(sql, (usuario,))
        user_info = cursor.fetchone()

        if user_info:
            user_data = {
                'usuario': user_info[0],
                'nombre': user_info[1],
                'apellido': user_info[2],
                'correo': user_info[3],
                'altura': user_info[4],
                'peso': user_info[5],
                'edad': user_info[6]
            }
            return user_data



@app.route('/api/estadisticas')
def estadisticas():
    usuario = session.get('usuario')
    cursor = conexion.connection.cursor(MySQLdb.cursors.DictCursor)
    query = """
    SELECT YEARWEEK(fecha, 1) AS semana,
           COUNT(*) AS numero_de_sesiones,
           SUM(numSets) AS sets,
           SUM(volumen) AS total_volumen
    FROM Sesion
    WHERE usuario = %s
      AND YEAR(fecha) = YEAR(CURDATE())
      AND MONTH(fecha) = MONTH(CURDATE())
    GROUP BY YEARWEEK(fecha, 1)
    ORDER BY semana;
    """
    cursor.execute(query,(usuario,))
    rows = cursor.fetchall()
    
    total_sesiones = sum(row["numero_de_sesiones"] for row in rows)
    total_sets = sum(row["sets"] for row in rows)

    data = {
        "semanas": [f"Semana {i+1}" for i in range(len(rows))],
        "volumen": [row["total_volumen"] for row in rows],
        "total_sesiones": total_sesiones,
        "total_sets": total_sets
    }

    return jsonify(data)

@app.route('/api/checklist_semanal')
def checklist_semanal():
    usuario = session.get('usuario')
    cursor = conexion.connection.cursor(MySQLdb.cursors.DictCursor)
    query = """
    SELECT DATE(fecha) AS dia
    FROM Sesion
    WHERE usuario = %s
      AND YEARWEEK(fecha, 1) = YEARWEEK(CURDATE(), 1);
    """
    cursor.execute(query, (usuario,))
    rows = cursor.fetchall()
    
    dias_con_sesion = [row['dia'].strftime('%Y-%m-%d') for row in rows]
    
    # Obtener los 7 días de la semana actual
    hoy = datetime.now()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes de la semana actual
    dias_semana = [(inicio_semana + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    data = {
        "dias_semana": dias_semana,
        "dias_con_sesion": dias_con_sesion
    }

    return jsonify(data)

@app.route('/api/sets_por_sesion', methods=['GET'])
def obtener_sets_por_sesion():
    usuario = session.get('usuario')
    cursor = conexion.connection.cursor(MySQLdb.cursors.DictCursor)
    
    query = """
    SELECT Fecha, numSets
    FROM Sesion
    WHERE usuario = %s
    ORDER BY Fecha DESC
    LIMIT 10
    """
    cursor.execute(query, (usuario,))
    sets_por_sesion = cursor.fetchall()
    return jsonify(sets_por_sesion)


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
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    user_data = getUserData(usuario)
    return render_template('dashboard.html',**user_data)



@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))
@app.route('/')
def home():
        return redirect(url_for('login'))




@app.route('/rutinas')
def rutinas():
    if 'usuario' in session:
        usuario = session['usuario']
        user_data = getUserData(usuario)
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
        return render_template('rutinas.html', **user_data,data=data)
    else:
        return redirect(url_for('login'))

@app.route('/crear_rutina', methods=['GET', 'POST'])
def crear_rutina():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    cursor = conexion.connection.cursor()
    sql = "SELECT usuario, nombre, apellido, correo, altura, peso, edad FROM usuario WHERE usuario = %s"
    cursor.execute(sql, (usuario,))
    user_info = cursor.fetchone()

    if user_info:
        user_data = {
            'usuario': user_info[0],
            'nombre': user_info[1],
            'apellido': user_info[2],
            'correo': user_info[3],
            'altura': user_info[4],
            'peso': user_info[5],
            'edad': user_info[6]
        }

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
    
    return render_template('crear_rutina.html', **user_data,ejercicios=ejercicios)


@app.route('/editar_rutina/<int:id>', methods=['GET', 'POST'])
def editar_rutina(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario = session['usuario']
    cursor = conexion.connection.cursor()
    sql = "SELECT usuario, nombre, apellido, correo, altura, peso, edad FROM usuario WHERE usuario = %s"
    cursor.execute(sql, (usuario,))
    user_info = cursor.fetchone()

    if user_info:
        user_data = {
                'usuario': user_info[0],
                'nombre': user_info[1],
                'apellido': user_info[2],
                'correo': user_info[3],
                'altura': user_info[4],
                'peso': user_info[5],
                'edad': user_info[6]
            }


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
    
    return render_template('editar_rutina.html', **user_data,rutina=rutina, ejercicios_rutina=ejercicios_rutina, todos_ejercicios=todos_ejercicios)

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
    usuario = session['usuario']
    cursor = conexion.connection.cursor()
    user_data = getUserData(usuario)

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
        set_completed = request.form.getlist('set_completed')
        ejercicios_ids = [request.form.get(f'ejercicio_id_{set_id}') for set_id in sets]
        volumen_total = 0
        num_sets_realizados = 0

        for i in range(len(sets)):
            if reps[i] and pesos[i]:  # Verificar que los valores estén presentes
                 if set_completed[i] == '1':  # Verificar que el set esté marcado como completado
                    sql_insert_set = "INSERT INTO setejercicio (Reps, Peso, Ejercicio_idEjercicio, sesion) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql_insert_set, (reps[i], pesos[i], ejercicios_ids[i], sesion_id))
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
                'reps': "",
                'peso': ""
            })

    return render_template('empezar_rutina.html', **user_data, rutina=rutina, grouped_ejercicios=grouped_ejercicios)





@app.route('/historial')
def historial():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    usuario = session['usuario']
    cursor = conexion.connection.cursor()
    user_data = getUserData(usuario)
    data = {}
    try:
        sql = "SELECT idSesion, Fecha, Duracion, volumen, numSets FROM sesion WHERE usuario = %s ORDER BY Fecha DESC"
        cursor.execute(sql, (usuario,))
        sesiones = cursor.fetchall()

        # Formatear fechas
        sesiones_formateadas = []
        for sesion in sesiones:
            fecha_formateada = format_date(sesion[1], format='long', locale='es')
            sesiones_formateadas.append((sesion[0], fecha_formateada, sesion[2], sesion[3], sesion[4]))

        data['sesiones'] = sesiones_formateadas
        data['mensaje'] = 'Exito' if sesiones else 'No tienes historial de sesiones.'
    except Exception as ex:
        data['mensaje'] = 'Error...'
    return render_template('historial.html', **user_data, data=data)

@app.route('/historial/<int:id_sesion>')
def detalle_sesion(id_sesion):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario = session['usuario']
    cursor = conexion.connection.cursor()
    sql = "SELECT usuario, nombre, apellido, correo, altura, peso, edad FROM usuario WHERE usuario = %s"
    cursor.execute(sql, (usuario,))
    user_info = cursor.fetchone()

    if user_info:
        user_data = {
                'usuario': user_info[0],
                'nombre': user_info[1],
                'apellido': user_info[2],
                'correo': user_info[3],
                'altura': user_info[4],
                'peso': user_info[5],
                'edad': user_info[6]
            }
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

    return render_template('detalle_sesion.html', **user_data,data=data)



@app.route('/asistente', methods=['GET', 'POST'])
def asistente():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario = session['usuario']
    cursor = conexion.connection.cursor()
    sql = "SELECT usuario, nombre, apellido, correo, altura, peso, edad FROM usuario WHERE usuario = %s"
    cursor.execute(sql, (usuario,))
    user_info = cursor.fetchone()

    if user_info:
        user_data = {
                'usuario': user_info[0],
                'nombre': user_info[1],
                'apellido': user_info[2],
                'correo': user_info[3],
                'altura': user_info[4],
                'peso': user_info[5],
                'edad': user_info[6]
            }
        
    if 'chat_history' not in session:
        session['chat_history'] = []

    # Recuperar el historial de chats desde la base de datos
    sql_history = "SELECT role, content FROM chat_history WHERE usuario = %s ORDER BY timestamp"
    cursor.execute(sql_history, (usuario,))
    chat_history = cursor.fetchall()

    # Convertir el historial en el formato necesario para la API de OpenAI
    session['chat_history'] = [{"role": row[0], "content": row[1]} for row in chat_history]

    # Añadir mensaje de bienvenida si el historial está vacío
    if not chat_history:
        welcome_message = "Hola! Soy tu asistente virtual para rutinas de ejercicio. ¿En qué puedo ayudarte hoy?"
        session['chat_history'].append({"role": "assistant", "content": welcome_message})

        # Guardar el mensaje de bienvenida en la base de datos
        sql_insert = "INSERT INTO chat_history (usuario, role, content) VALUES (%s, %s, %s)"
        cursor.execute(sql_insert, (usuario, "assistant", welcome_message))
        conexion.connection.commit()

    data = {}
    if(client):
        if request.method == 'POST':
            user_input = request.form['user_input']
            session['chat_history'].append({"role": "user", "content": user_input})


            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "Es un asistente serio que solo ayuda con elaboración de rutinas de ejercicio.","max_tokens": 200},

            ] + session['chat_history'],
            temperature=0.2,
            max_tokens=250,
            )
            bot_response = response.choices[0].message.content
            session['chat_history'].append({"role": "assistant", "content": bot_response})

            # Guardar el nuevo mensaje en la base de datos
            sql_insert = "INSERT INTO chat_history (usuario, role, content) VALUES (%s, %s, %s)"
            cursor.execute(sql_insert, (usuario, "user", user_input))
            cursor.execute(sql_insert, (usuario, "assistant", bot_response))
            conexion.connection.commit()

            data['respuesta'] = markdown2.markdown(bot_response)
        # Convertir el historial del asistente a HTML usando markdown2
        session['chat_history'] = [{"role": message['role'], "content": markdown2.markdown(message['content'])} for message in session['chat_history']]
    
    return render_template('asistente.html', chat_history=session['chat_history'],**user_data,data=data)


def pagina_no_encontrada(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.register_error_handler(404, pagina_no_encontrada)
    app.run(debug=True)

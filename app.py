from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
import sqlite3
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'azul123'

# PIN para acceder a nominas
NOMINA_PIN = "13579"

def init_db():
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    garrafones INTEGER,
                    precio_unitario REAL,
                    metodo_pago TEXT,
                    cliente TEXT,
                    chofer TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS gastos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    descripcion TEXT,
                    monto REAL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT,
                    cantidad INTEGER,
                    unidad TEXT,
                    costo_unitario REAL,
                    actualizado TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS nominas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_pago TEXT,
                    empleado TEXT,
                    rol TEXT,
                    dias_laborados INTEGER,
                    salario_diario REAL,
                    observaciones TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS creditos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    cliente TEXT,
                    monto_total REAL,
                    saldo REAL,
                    estado TEXT)''')
    conn.commit()
    conn.close()

@app.route('/acceso_nominas', methods=['GET', 'POST'])
def acceso_nominas():
    if request.method == 'POST':
        pin = request.form['pin']
        if pin == NOMINA_PIN:
            session['autorizado_nomina'] = True
            return redirect(url_for('ver_nominas'))
        else:
            return render_template('acceso_nominas.html', error="Código incorrecto")
    return render_template('acceso_nominas.html')

@app.route('/cerrar_nominas')
def cerrar_nominas():
    session.pop('nominas_autorizado', None)
    return redirect(url_for('index'))

@app.route('/nominas', methods=['GET', 'POST'])
def ver_nominas():
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin != '13579':  # Puedes cambiar el pin aquí
            return render_template('acceso_nominas.html', error="Código incorrecto.")
        session['nominas_autorizado'] = True
        return redirect(url_for('ver_nominas'))

    if not session.get('nominas_autorizado'):
        return render_template('acceso_nominas.html')

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("SELECT * FROM nominas")
    registros = c.fetchall()
    conn.close()
    return render_template('nominas.html', registros=registros)

@app.route('/agregar_nomina', methods=['POST'])
def agregar_nomina():
    fecha_pago = request.form['fecha_pago']
    empleado = request.form['empleado']
    rol = request.form['rol']
    dias = int(request.form['dias_laborados'])
    salario_diario = float(request.form['salario_diario'])
    observaciones = request.form['observaciones']

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO nominas (fecha_pago, empleado, rol, dias_laborados, salario_diario, observaciones)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (fecha_pago, empleado, rol, dias, salario_diario, observaciones))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_nominas'))

@app.route('/editar_nomina/<int:id>', methods=['GET', 'POST'])
def editar_nomina(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    if request.method == 'POST':
        fecha_pago = request.form['fecha_pago']
        empleado = request.form['empleado']
        rol = request.form['rol']
        dias_laborados = int(request.form['dias_laborados'])
        salario_diario = float(request.form['salario_diario'])
        observaciones = request.form['observaciones']

        c.execute("""
            UPDATE nominas
            SET fecha_pago = ?, empleado = ?, rol = ?, dias_laborados = ?, salario_diario = ?, observaciones = ?
            WHERE id = ?
        """, (fecha_pago, empleado, rol, dias_laborados, salario_diario, observaciones, id))
        conn.commit()
        conn.close()
        return redirect(url_for('ver_nominas'))
    else:
        c.execute("SELECT * FROM nominas WHERE id = ?", (id,))
        registro = c.fetchone()
        conn.close()
        return render_template('editar_nomina.html', registro=registro)

@app.route('/eliminar_nomina/<int:id>')
def eliminar_nomina(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("DELETE FROM nominas WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_nominas'))

@app.route('/creditos')
def ver_creditos():
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("SELECT * FROM creditos")
    creditos = c.fetchall()
    conn.close()
    return render_template('creditos.html', creditos=creditos)

@app.route('/agregar_credito', methods=['POST'])
def agregar_credito():
    fecha = datetime.today().strftime('%Y-%m-%d')
    cliente = request.form['cliente']
    monto = float(request.form['monto'])
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("INSERT INTO creditos (fecha, cliente, monto_total, saldo, estado) VALUES (?, ?, ?, ?, ?)",
              (fecha, cliente, monto, monto, 'Pendiente'))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_creditos'))

@app.route('/abono_credito/<int:id>', methods=['GET', 'POST'])
def abono_credito(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()

    if request.method == 'POST':
        abono = float(request.form['abono'])
        # Obtener saldo actual
        c.execute("SELECT saldo FROM creditos WHERE id = ?", (id,))
        saldo_actual = c.fetchone()[0]

        # Restar abono al saldo
        nuevo_saldo = saldo_actual - abono
        estado = 'Liquidado' if nuevo_saldo <= 0 else 'Pendiente'

        c.execute("UPDATE creditos SET saldo = ?, estado = ? WHERE id = ?", (nuevo_saldo, estado, id))
        conn.commit()
        conn.close()
        return redirect(url_for('ver_creditos'))

    else:
        # GET: mostrar formulario
        c.execute("SELECT * FROM creditos WHERE id = ?", (id,))
        credito = c.fetchone()
        conn.close()
        return render_template("abono_credito.html", credito=credito)

@app.route('/liquidar_credito/<int:id>')
def liquidar_credito(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("UPDATE creditos SET saldo = 0, estado = 'Liquidado' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_creditos'))

@app.route('/eliminar_credito/<int:id>')
def eliminar_credito(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("DELETE FROM creditos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ver_creditos'))

@app.route('/')
def index():
    fecha = request.args.get('fecha')
    if not fecha:
        fecha = datetime.today().strftime('%Y-%m-%d')

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()

    c.execute("SELECT * FROM ventas WHERE fecha = ?", (fecha,))
    ventas = c.fetchall()
    total_ventas = sum(v[2] * v[3] for v in ventas)
    garrafones_vendidos = sum(v[2] for v in ventas)

    c.execute("SELECT * FROM gastos WHERE fecha = ?", (fecha,))
    gastos = c.fetchall()
    total_gastos = sum(g[3] for g in gastos)

    ganancia = total_ventas - total_gastos
    conn.close()

    return render_template('index.html',
                           ventas=ventas,
                           gastos=gastos,
                           ingresos=total_ventas,
                           garrafones=garrafones_vendidos,
                           gastos_totales=total_gastos,
                           ganancia=ganancia,
                           fecha_seleccionada=fecha)


@app.route('/agregar_venta', methods=['POST'])
def agregar_venta():
    fecha = datetime.today().strftime('%Y-%m-%d')
    garrafones = int(request.form['garrafones'])
    precio = float(request.form['precio'])
    metodo = request.form['metodo']
    cliente = request.form['cliente']
    chofer = request.form['chofer']
    
    subtotal = garrafones * precio

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("""INSERT INTO ventas (fecha, garrafones, precio_unitario, metodo_pago, cliente, chofer) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (fecha, garrafones, precio, metodo, cliente, chofer))

    # Si es crédito, registrar en tabla de créditos
    if metodo.lower() == 'credito':
        c.execute("""INSERT INTO creditos (fecha, cliente, monto_total, saldo, estado)
                     VALUES (?, ?, ?, ?, ?)""",
                  (fecha, cliente, subtotal, subtotal, 'Pendiente'))

    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/agregar_gasto', methods=['POST'])
def agregar_gasto():
    fecha = datetime.today().strftime('%Y-%m-%d')
    descripcion = request.form['descripcion']
    monto = float(request.form['monto'])

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("INSERT INTO gastos (fecha, descripcion, monto) VALUES (?, ?, ?)",
              (fecha, descripcion, monto))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/eliminar_venta/<int:id>')
def eliminar_venta(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("DELETE FROM ventas WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/editar_venta/<int:id>', methods=['GET', 'POST'])
def editar_venta(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    if request.method == 'POST':
        garrafones = int(request.form['garrafones'])
        precio = float(request.form['precio'])
        metodo = request.form['metodo']
        cliente = request.form['cliente']
        c.execute("UPDATE ventas SET garrafones = ?, precio_unitario = ?, metodo_pago = ?, cliente = ? WHERE id = ?",
                  (garrafones, precio, metodo, cliente, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        c.execute("SELECT * FROM ventas WHERE id = ?", (id,))
        venta = c.fetchone()
        conn.close()
        return render_template('editar_venta.html', venta=venta)

@app.route('/eliminar_gasto/<int:id>')
def eliminar_gasto(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("DELETE FROM gastos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/editar_gasto/<int:id>', methods=['GET', 'POST'])
def editar_gasto(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    if request.method == 'POST':
        descripcion = request.form['descripcion']
        monto = float(request.form['monto'])
        c.execute("UPDATE gastos SET descripcion = ?, monto = ? WHERE id = ?",
                  (descripcion, monto, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        c.execute("SELECT * FROM gastos WHERE id = ?", (id,))
        gasto = c.fetchone()
        conn.close()
        return render_template('editar_gasto.html', gasto=gasto)

@app.route('/inventario')
def inventario():
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("SELECT * FROM inventario")
    productos = c.fetchall()
    conn.close()
    return render_template("inventario.html", productos=productos)

@app.route('/agregar_producto', methods=['POST'])
def agregar_producto():
    producto = request.form['producto']
    cantidad = int(request.form['cantidad'])
    unidad = request.form['unidad']
    costo_unitario = float(request.form['costo_unitario'])
    actualizado = datetime.today().strftime('%Y-%m-%d')
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("INSERT INTO inventario (producto, cantidad, unidad, costo_unitario, actualizado) VALUES (?, ?, ?, ?, ?)",
              (producto, cantidad, unidad, costo_unitario, actualizado))
    conn.commit()
    conn.close()
    return redirect(url_for('inventario'))

@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("DELETE FROM inventario WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('inventario'))

@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    if request.method == 'POST':
        producto = request.form['producto']
        cantidad = int(request.form['cantidad'])
        unidad = request.form['unidad']
        costo_unitario = float(request.form['costo_unitario'])
        actualizado = datetime.today().strftime('%Y-%m-%d')
        c.execute("UPDATE inventario SET producto = ?, cantidad = ?, unidad = ?, costo_unitario = ?, actualizado = ? WHERE id = ?",
                  (producto, cantidad, unidad, costo_unitario, actualizado, id))
        conn.commit()
        conn.close()
        return redirect(url_for('inventario'))
    else:
        c.execute("SELECT * FROM inventario WHERE id = ?", (id,))
        item = c.fetchone()
        conn.close()
        if item is None:
            return "Producto no encontrado", 404
        return render_template('editar_producto.html', item=item)

@app.route('/exportar_pdf')
def exportar_pdf():
    fecha = request.args.get('fecha')
    if not fecha:
        fecha = datetime.today().strftime('%Y-%m-%d')

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()

    c.execute("SELECT * FROM ventas WHERE fecha = ?", (fecha,))
    ventas = c.fetchall()

    c.execute("SELECT * FROM gastos WHERE fecha = ?", (fecha,))
    gastos = c.fetchall()

    total_ventas = sum(v[2] * v[3] for v in ventas)
    garrafones_vendidos = sum(v[2] for v in ventas)
    total_gastos = sum(g[3] for g in gastos)
    ganancia = total_ventas - total_gastos
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("<b style='font-size:16pt;'>AGUA PURIFICADA AZZUL</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Fecha:</b> {fecha}", styles['Normal']))
    elements.append(Spacer(1, 12))

    resumen_data = [
        ['Garrafones vendidos', garrafones_vendidos],
        ['Ingresos totales', f"${total_ventas:.2f}"],
        ['Gastos del día', f"${total_gastos:.2f}"],
        ['Ganancia del día', f"${ganancia:.2f}"]
    ]
    resumen_table = Table(resumen_data, colWidths=[200, 200])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 20))

    if ventas:
        ventas_data = [['Garrafones', 'Precio', 'Método', 'Cliente']]
        for v in ventas:
            ventas_data.append([v[2], f"${v[3]:.2f}", v[4], v[5]])

        ventas_table = Table(ventas_data, colWidths=[100, 100, 100, 140])
        ventas_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(Paragraph("<b>Ventas</b>", styles['Heading3']))
        elements.append(ventas_table)
        elements.append(Spacer(1, 20))

    if gastos:
        gastos_data = [['Descripción', 'Monto']]
        for g in gastos:
            gastos_data.append([g[2], f"${g[3]:.2f}"])

        gastos_table = Table(gastos_data, colWidths=[300, 140])
        gastos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.salmon),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(Paragraph("<b>Gastos</b>", styles['Heading3']))
        elements.append(gastos_table)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"resumen_{fecha}.pdf", mimetype='application/pdf')

@app.route('/exportar_inventario')
def exportar_inventario():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>Inventario - Agua Purificada Azul</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("SELECT producto, cantidad, costo_unitario FROM inventario")
    productos = c.fetchall()
    conn.close()

    if productos:
        data = [['Producto', 'Cantidad', 'Costo Unitario', 'Subtotal']]
        total_inventario = 0
        for p in productos:
            subtotal = p[1] * p[2]
            total_inventario += subtotal
            data.append([p[0], p[1], f"${p[2]:.2f}", f"${subtotal:.2f}"])

        data.append(['', '', 'Total', f"${total_inventario:.2f}"])

        tabla = Table(data, colWidths=[150, 100, 120, 120])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ]))
        elements.append(tabla)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="inventario.pdf", mimetype='application/pdf')

@app.route('/exportar_nominas')
def exportar_nominas():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>Nóminas - Agua Purificada Azul</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("SELECT fecha_pago, empleado, rol, dias_laborados, salario_diario, observaciones FROM nominas")
    registros = c.fetchall()
    conn.close()

    if registros:
        data = [['Fecha', 'Empleado', 'Rol', 'Días', 'Salario Diario', 'Sueldo', 'Observaciones']]
        for r in registros:
            sueldo = r[3] * r[4]
            data.append([r[0], r[1], r[2], r[3], f"${r[4]:.2f}", f"${sueldo:.2f}", r[5]])

        tabla = Table(data, colWidths=[70, 100, 80, 40, 80, 80, 150])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
        ]))
        elements.append(tabla)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="nominas.pdf", mimetype='application/pdf')

@app.route('/exportar_creditos')
def exportar_creditos():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>Créditos - Agua Purificada Azul</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("SELECT fecha, cliente, monto_total, saldo, estado FROM creditos")
    creditos = c.fetchall()
    conn.close()

    if creditos:
        data = [['Fecha', 'Cliente', 'Total', 'Saldo', 'Estado']]
        for cr in creditos:
            data.append([cr[0], cr[1], f"${cr[2]:.2f}", f"${cr[3]:.2f}", cr[4]])

        tabla = Table(data, colWidths=[80, 120, 80, 80, 80])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ]))
        elements.append(tabla)

    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="creditos.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

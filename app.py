from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = Flask(__name__)
app.secret_key = 'azul123'

def init_db():
    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    garrafones INTEGER,
                    precio_unitario REAL,
                    metodo_pago TEXT,
                    cliente TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS gastos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    descripcion TEXT,
                    monto REAL)''')
    conn.commit()
    conn.close()

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

    conn = sqlite3.connect('azul.db')
    c = conn.cursor()
    c.execute("INSERT INTO ventas (fecha, garrafones, precio_unitario, metodo_pago, cliente) VALUES (?, ?, ?, ?, ?)",
              (fecha, garrafones, precio, metodo, cliente))
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

@app.route('/exportar_pdf')
def exportar_pdf():
    from flask import send_file
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from io import BytesIO

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

    # Encabezado
    title = Paragraph("<b style='font-size:16pt;'>AGUA PURIFICADA AZZUL</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Fecha:</b> {fecha}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Resumen
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

    # Ventas
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

    # Gastos
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
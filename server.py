import base64
import io
import queue

from flask import Flask, render_template, request, jsonify
from PIL import Image, UnidentifiedImageError

app = Flask(__name__)

# Cola thread-safe compartida entre el hilo de Flask y el hilo de Tkinter.
# Antes se usaba una variable global (`ultima_imagen`) leída/escrita desde dos
# hilos distintos sin ninguna protección: con una Queue nos evitamos esa
# condición de carrera sin tener que gestionar locks a mano.
imagenes_pendientes: "queue.Queue[Image.Image]" = queue.Queue()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/procesar_imagen", methods=["POST"])
def procesar_imagen():
    data = request.get_json(silent=True)
    if not data or "imagen" not in data:
        return jsonify({"error": "Falta el campo 'imagen' en el cuerpo de la petición"}), 400

    try:
        cabecera, imagen_b64 = data["imagen"].split(",", 1)
        imagen_bytes = base64.b64decode(imagen_b64)
        imagen_pil = Image.open(io.BytesIO(imagen_bytes))
        imagen_pil.load()  # fuerza la decodificación aquí para detectar errores ya
    except (ValueError, UnidentifiedImageError, OSError) as exc:
        return jsonify({"error": f"Imagen inválida: {exc}"}), 400

    imagenes_pendientes.put(imagen_pil)
    return jsonify({"resultado": "Imagen recibida"})

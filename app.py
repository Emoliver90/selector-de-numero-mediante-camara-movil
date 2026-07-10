import os
import queue
import shutil

from dotenv import load_dotenv
import qrcode
from PIL import ImageTk, ImageFilter, ImageEnhance, ImageOps
from tkinter import ttk, Tk, LabelFrame, Frame, Label, Button
from tkinter import N, S, E, W, HORIZONTAL, VERTICAL, CENTER
import pytesseract
import ngrok

import db
import server
from models import Ruleta

load_dotenv()  # carga variables definidas en un archivo .env local (si existe)

# ── Configuración por variables de entorno (antes iban "quemadas" en el código) ──
# El token de ngrok es un secreto: nunca debe vivir en el código fuente ni
# subirse al repositorio. Se lee desde el entorno (ver .env.example).
NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN")

# Ruta al ejecutable de Tesseract. Antes estaba fijada a una ruta de Windows
# ("C:\Program Files\..."), lo que rompía la app en Linux/macOS o en
# cualquier máquina con otra instalación. Ahora se intenta autodetectar en
# el PATH y solo se usa TESSERACT_CMD si el usuario lo define explícitamente.
TESSERACT_CMD = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


class VentanaPrincipal:
    def __init__(self, root):
        self.ventana = root
        self.ventana.title("App Gestor de Tiradas")
        self.ventana.resizable(True, True)
        self.ventana.geometry("1000x650")
        self.ventana.configure(bg="#1a1a2e")

        # ── Expansión responsive ──────────────────────────────
        self.ventana.columnconfigure(0, weight=1)
        self.ventana.columnconfigure(1, weight=3)
        self.ventana.rowconfigure(0, weight=1)

        # ── Panel izquierdo ───────────────────────────────────
        frame_izq = LabelFrame(
            self.ventana, text="Control", font=("Calibri", 12, "bold"),
            bg="#16213e", fg="white", bd=2, relief="groove"
        )
        frame_izq.grid(column=0, row=0, sticky=N + S + E + W, padx=10, pady=10)
        frame_izq.columnconfigure(0, weight=1)

        # Frame QR (ocultable)
        self.frame_qr = Frame(frame_izq, bg="#16213e")
        self.frame_qr.grid(column=0, row=0, sticky=E + W, pady=5)
        self.frame_qr.columnconfigure(0, weight=1)

        self.cuadro = Label(self.frame_qr, bg="#16213e")
        self.cuadro.grid(column=0, row=0)

        self.boton_ocultar = ttk.Button(
            self.frame_qr, text="✖ Ocultar QR", command=self.ocultar_qr
        )
        self.boton_ocultar.grid(column=0, row=1, sticky=E + W, pady=2)
        self.frame_qr.grid_remove()  # oculto al inicio

        # Botón generar QR
        s = ttk.Style()
        s.configure("qr.TButton", font=("Calibri", 12, "bold"))
        self.boton_qr = ttk.Button(
            frame_izq, text="📷 Generar QR",
            command=self.generar_qr, style="qr.TButton"
        )
        self.boton_qr.grid(column=0, row=1, sticky=E + W, padx=10, pady=5)

        # Separador
        ttk.Separator(frame_izq, orient=HORIZONTAL).grid(
            column=0, row=2, sticky=E + W, pady=5
        )

        # Label "Última foto recibida"
        Label(
            frame_izq, text="Última foto recibida:",
            font=("Calibri", 10), bg="#16213e", fg="#a0a0a0"
        ).grid(column=0, row=3, sticky=W, padx=10)

        self.label_imagen = Label(
            frame_izq, text="Sin foto aún", bg="#0f3460",
            fg="white", width=28, height=10, relief="sunken"
        )
        self.label_imagen.grid(column=0, row=4, padx=10, pady=5, sticky=E + W)

        # Estado OCR
        self.label_estado = Label(
            frame_izq, text="", font=("Calibri", 11),
            fg="#00ff88", bg="#16213e", wraplength=220
        )
        self.label_estado.grid(column=0, row=5, padx=10, pady=5)

        # ── Panel derecho (tabla) ─────────────────────────────
        frame_der = LabelFrame(
            self.ventana, text="Registro de Tiradas",
            font=("Calibri", 12, "bold"),
            bg="#16213e", fg="white", bd=2, relief="groove"
        )
        frame_der.grid(column=1, row=0, sticky=N + S + E + W, padx=10, pady=10)
        frame_der.columnconfigure(0, weight=1)
        frame_der.rowconfigure(0, weight=1)

        # Scrollbars
        scroll_y = ttk.Scrollbar(frame_der, orient=VERTICAL)
        scroll_x = ttk.Scrollbar(frame_der, orient=HORIZONTAL)
        scroll_y.grid(row=0, column=1, sticky=N + S)
        scroll_x.grid(row=1, column=0, sticky=E + W)

        # Estilo tabla
        style = ttk.Style()
        style.configure("mystile.Treeview",
                         font=("Calibri", 11),
                         rowheight=28,
                         background="#1a1a2e",
                         foreground="white",
                         fieldbackground="#1a1a2e")
        style.configure("mystile.Treeview.Heading",
                         font=("Calibri", 12, "bold"),
                         background="#0f3460",
                         foreground="white")
        style.map("mystile.Treeview",
                  background=[("selected", "#e94560")])

        self.tabla = ttk.Treeview(
            frame_der,
            columns=("mayor", "menor", "par", "impar", "fecha"),
            style="mystile.Treeview",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )
        self.tabla.grid(row=0, column=0, sticky=N + S + E + W)

        scroll_y.config(command=self.tabla.yview)
        scroll_x.config(command=self.tabla.xview)

        # Cabeceras y anchos
        self.tabla.heading('#0', text='Número', anchor=CENTER)
        self.tabla.heading('#1', text='Mayor',  anchor=CENTER)
        self.tabla.heading('#2', text='Menor',  anchor=CENTER)
        self.tabla.heading('#3', text='Par',    anchor=CENTER)
        self.tabla.heading('#4', text='Impar',  anchor=CENTER)
        self.tabla.heading('#5', text='Fecha',  anchor=CENTER)

        self.tabla.column('#0', width=80,  minwidth=60,  anchor=CENTER)
        self.tabla.column('#1', width=100, minwidth=70,  anchor=CENTER)
        self.tabla.column('#2', width=100, minwidth=70,  anchor=CENTER)
        self.tabla.column('#3', width=80,  minwidth=60,  anchor=CENTER)
        self.tabla.column('#4', width=80,  minwidth=60,  anchor=CENTER)
        self.tabla.column('#5', width=200, minwidth=150, anchor=CENTER)

        self.actualizar_tabla()
        self.escuchar_imagen()

    # ── OCR ───────────────────────────────────────────────────
    def preprocesar_imagen(self, imagen_pil):
        img = imagen_pil.convert('L')  # Escala de grises
        img = ImageOps.autocontrast(img)  # Contraste automático
        img = ImageEnhance.Sharpness(img).enhance(3.0)  # Más nitidez
        ancho, alto = img.size
        img = img.resize((ancho * 4, alto * 4))  # Más grande que antes (x4)
        img = img.filter(ImageFilter.SHARPEN)
        return img

    def extraer_numero(self, imagen_pil):
        img_proc = self.preprocesar_imagen(imagen_pil)
        config = '--psm 8 --oem 3 outputbase digits'
        texto = pytesseract.image_to_string(img_proc, config=config)
        limpio = texto.strip().replace('\n', '').replace(' ', '')
        print(f"OCR detectó: '{limpio}'")
        if limpio.isdigit():
            numero = int(limpio)
            if 0 <= numero <= 36:
                return numero
        return None

    # ── Base de datos ─────────────────────────────────────────
    def guardar_tirada(self, numero):
        # El 0 de la ruleta no es ni "mayor" ni "menor" ni par/impar en el
        # sentido de la apuesta (regla real de la ruleta). Antes el 0 se
        # marcaba como "menor" y como número par, lo cual es incorrecto.
        if numero == 0:
            mayor = ""
            menor = ""
            par = False
            impar = False
        else:
            mayor = "Mayor" if numero > 18 else ""
            menor = "Menor" if numero <= 18 else ""
            par = numero % 2 == 0
            impar = numero % 2 != 0

        sesion = db.nueva_sesion()
        try:
            nueva = Ruleta(numero=numero, mayor=mayor, menor=menor, par=par, impar=impar)
            sesion.add(nueva)
            sesion.commit()
            print(f"✓ Guardado: número {numero}")
        except Exception as e:
            sesion.rollback()
            print(f"✗ Error al guardar: {e}")
        finally:
            sesion.close()  # cierra la sesión siempre

    def actualizar_tabla(self):
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        sesion = db.nueva_sesion()
        try:
            registros = sesion.query(Ruleta).all()
            for r in registros:
                self.tabla.insert('', 0,
                    text=r.numero,
                    values=(r.mayor, r.menor, r.par, r.impar, r.fecha)
                )
        finally:
            sesion.close()

    # ── Escucha imágenes cada 500ms ───────────────────────────
    def escuchar_imagen(self):
        # Antes se leía/escribía una variable global (`server.ultima_imagen`)
        # desde dos hilos (Flask y Tkinter) sin ninguna protección, lo que es
        # una condición de carrera clásica. Ahora se usa una Queue
        # (thread-safe) y get_nowait() no bloquea el bucle de Tkinter.
        try:
            imagen = server.imagenes_pendientes.get_nowait()
        except queue.Empty:
            imagen = None

        if imagen is not None:
            # Mostrar foto
            img_tk = ImageTk.PhotoImage(imagen)
            self.label_imagen.config(image=img_tk, text="")
            self.label_imagen.image = img_tk

            # OCR
            numero = self.extraer_numero(imagen)
            if numero is not None:
                self.guardar_tirada(numero)
                self.actualizar_tabla()
                self.label_estado.config(
                    text=f"✓ Número {numero} guardado", fg="#00ff88"
                )
            else:
                self.label_estado.config(
                    text="✗ No se reconoció\nel número", fg="#e94560"
                )

        self.ventana.after(500, self.escuchar_imagen)

    # ── QR ────────────────────────────────────────────────────
    def generar_qr(self):
        if not NGROK_AUTHTOKEN:
            self.label_estado.config(
                text="Error: falta NGROK_AUTHTOKEN\n(ver .env.example)", fg="#e94560"
            )
            return

        listener = ngrok.forward(5000, authtoken_from_env=False, authtoken=NGROK_AUTHTOKEN)
        url = listener.url()
        if url is None:
            self.label_estado.config(text="Error: ngrok no arrancó", fg="#e94560")
            return
        qr = qrcode.make(url)
        self.img_tk = ImageTk.PhotoImage(qr)
        self.cuadro.config(image=self.img_tk)
        self.cuadro.image = self.img_tk
        self.frame_qr.grid()           # muestra el frame QR
        self.boton_qr.config(text="🔄 Regenerar QR")
        self.label_estado.config(text="✓ QR listo", fg="#00ff88")

    def ocultar_qr(self):
        self.frame_qr.grid_remove()    # oculta el frame QR
        self.boton_qr.config(text="📷 Generar QR")

import threading
from tkinter import Tk

import db
from app import VentanaPrincipal
from server import app as flask_app


def run_flask():
    """Arranca el servidor Flask en un hilo secundario (daemon)."""
    flask_app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    # 1. Crea las tablas si no existen
    db.Base.metadata.create_all(db.engine)

    # 2. Flask en hilo secundario
    hilo_flask = threading.Thread(target=run_flask, daemon=True)
    hilo_flask.start()

    # 3. Tkinter en hilo principal
    root = Tk()
    app_tk = VentanaPrincipal(root)
    root.mainloop()

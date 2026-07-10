# 🎯 App Gestor de Tiradas (Selector de Números)

Aplicación de escritorio en Python que registra tiradas de ruleta a partir de
una foto tomada desde el móvil. Combina **Tkinter** (interfaz de escritorio),
**Flask** (servidor que recibe la imagen desde el navegador del móvil),
**ngrok** (túnel público + QR para conectar el móvil sin configurar red) y
**Tesseract OCR** (lectura del número en la imagen). Los resultados se
guardan en una base de datos **SQLite** vía **SQLAlchemy**.

## ¿Cómo funciona?

1. La app de escritorio genera un código QR (túnel de ngrok) que abre una
   página web simple desde el móvil.
2. Desde el móvil se saca una foto del resultado de la ruleta y se envía al
   servidor Flask embebido en la propia app.
3. La app procesa la imagen (escala de grises, contraste, nitidez, zoom x4) y
   usa Tesseract para extraer el número.
4. Si el número es válido (0–36), se calcula mayor/menor y par/impar, se
   guarda en SQLite y se refresca la tabla en pantalla.

## Instalación

```bash
git clone <url-del-repo>
cd Selector_de_numeros
python -m venv .venv
source .venv/bin/activate      # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Además del OCR en Python, hace falta el **motor de Tesseract** instalado en
el sistema (no es un paquete de Python):

- Windows: instalador oficial de [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- macOS: `brew install tesseract`
- Linux (Debian/Ubuntu): `sudo apt install tesseract-ocr`

### Configuración de secretos

Copia `.env.example` como `.env` y completa tu propio token de ngrok:

```bash
cp .env.example .env
```

```
NGROK_AUTHTOKEN=tu_token_aqui
```

> Puedes generar tu token gratis en el [dashboard de ngrok](https://dashboard.ngrok.com/get-started/your-authtoken).

## Ejecución

```bash
python main.py
```

Esto crea la base de datos SQLite si no existe, levanta Flask en segundo
plano (puerto 5000) y abre la ventana de Tkinter.

## Estructura del proyecto

```
Selector_de_numeros/
├── main.py          # Punto de entrada: arranca Flask + Tkinter
├── app.py           # Interfaz de escritorio (Tkinter) y lógica de OCR
├── server.py         # Servidor Flask que recibe la imagen del móvil
├── models.py         # Modelo SQLAlchemy (tabla `ruleta`)
├── db.py             # Configuración del motor y sesiones de SQLAlchemy
├── templates/
│   └── index.html    # Página que se abre desde el móvil
├── requirements.txt
├── .env.example
└── .gitignore
```

## Revisión de buenas prácticas y cambios realizados

El código original funcionaba, pero tenía varios problemas de seguridad y de
diseño. Esto es lo que se corrigió:

- **🔴 Secreto expuesto en el código (crítico):** el token de autenticación
  de ngrok estaba escrito directamente en `app.py` y quedaba versionado en
  git. Ahora se lee desde una variable de entorno (`NGROK_AUTHTOKEN`) cargada
  con `python-dotenv` desde un archivo `.env` que **no** se sube al
  repositorio. **Importante:** como ese token ya quedó expuesto en el
  historial de git del proyecto original, te recomiendo regenerarlo desde el
  dashboard de ngrok — cambiar el código no invalida un token que ya fue
  público.
- **Ruta de Tesseract "quemada" para Windows:** `pytesseract.tesseract_cmd`
  apuntaba a una ruta fija de `C:\Program Files\...`, así que la app se
  rompía en Linux/macOS o en cualquier instalación distinta. Ahora se
  autodetecta con `shutil.which("tesseract")` y solo se fuerza una ruta si
  defines `TESSERACT_CMD` en `.env`.
- **Condición de carrera entre hilos:** la imagen recibida por Flask se
  guardaba en una variable global (`server.ultima_imagen`) leída y escrita
  desde dos hilos distintos (Flask y Tkinter) sin ninguna protección. Se
  reemplazó por una `queue.Queue`, que es thread-safe por diseño, así que no
  hace falta gestionar locks a mano.
- **Bug de dominio en el 0 de la ruleta:** el 0 se guardaba como "menor" y
  como número par, cuando en la ruleta real el 0 no pertenece a mayor/menor
  ni a par/impar. Se corrigió `guardar_tirada` para tratarlo como caso
  especial.
- **Bug silencioso en el modelo:** `Ruleta.__init__` aceptaba un parámetro
  `fecha`, pero lo ignoraba siempre y usaba `datetime.now()`. Ahora respeta
  `fecha` si se pasa explícitamente.
- **Código duplicado:** `__repr__` y `__str__` en `models.py` repetían
  exactamente la misma lógica dos veces. Se unificó en un solo método.
- **`from tkinter import *`:** import con comodín, que contamina el
  namespace y dificulta saber de dónde viene cada nombre. Se reemplazó por
  imports explícitos.
- **Sin manejo de errores en el endpoint Flask:** `/procesar_imagen` asumía
  que el JSON siempre traía una imagen válida en base64; una petición mal
  formada tumbaba el servidor con una excepción sin capturar. Ahora valida
  el payload y responde con un 400 controlado.
- **Sesión de SQLAlchemy sin usar:** `db.py` creaba una sesión global
  (`session = Session()`) al importar el módulo que nunca se usaba (el resto
  del código siempre llama a `nueva_sesion()`). Se eliminó por ser código
  muerto que además dejaba una conexión abierta innecesariamente.
- **Faltaban `requirements.txt` y `.gitignore`:** no había forma de
  reproducir el entorno ni de evitar subir `.venv/`, `__pycache__/`, la base
  de datos local o el propio `.env` al repositorio. Se añadieron ambos.

## 🚀 Mejoras a futuro

- **Rotar el token de ngrok** expuesto en el historial de git (ver nota de
  seguridad arriba) y, si el repositorio es público, considerar limpiar el
  historial con `git filter-repo` o BFG Repo-Cleaner.
- **Logging en vez de `print`:** sustituir los `print()` de depuración por el
  módulo `logging`, con niveles (INFO/ERROR) y salida a archivo.
- **Tests automáticos:** no hay ningún test. Se podrían cubrir con `pytest`
  al menos `guardar_tirada`, `extraer_numero` (con imágenes de prueba) y el
  endpoint `/procesar_imagen`.
- **Validación más robusta del OCR:** actualmente basta con que el texto sea
  numérico entre 0 y 36; se podría añadir un umbral de confianza de
  Tesseract o pedir confirmación manual cuando el resultado sea dudoso.
- **Separar configuración de UI y lógica:** `app.py` mezcla la construcción
  de la interfaz Tkinter con la lógica de negocio (OCR, guardado en BD). Se
  podría extraer esa lógica a un módulo aparte (p. ej. `ocr.py`,
  `repository.py`) para facilitar tests unitarios.
- **Migraciones de base de datos:** si el modelo `Ruleta` cambia en el
  futuro, no hay forma de migrar la base existente. Se podría incorporar
  `Alembic`.
- **Autenticación en el endpoint `/procesar_imagen`:** cualquiera que
  conozca la URL de ngrok mientras el túnel está activo podría enviar
  imágenes al servidor. Se podría añadir un token simple compartido entre la
  página del móvil y el servidor.
- **Historial y estadísticas:** aprovechar los datos guardados para mostrar
  estadísticas (números calientes/fríos, rachas de par/impar, etc.) en una
  vista aparte.

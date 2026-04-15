from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
from steganography import hide_message, extract_message
from forensics import full_forensic_report

# Inicializamos la aplicación FastAPI
app = FastAPI(title="Steganography & Steganalysis API")

# Configuramos CORS para que el frontend React pueda comunicarse con el backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta temporal donde guardamos las imágenes subidas
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def root():
    return {"message": "Steganography & Steganalysis API funcionando ✅"}


@app.post("/hide")
async def hide(
    image: UploadFile = File(...),
    message: str = Form(...)
):
    """
    Recibe una imagen y un mensaje, oculta el mensaje en la imagen
    y devuelve la imagen modificada.
    """
    # Guardamos la imagen original en la carpeta uploads
    input_path = os.path.join(UPLOAD_DIR, f"original_{image.filename}")
    output_path = os.path.join(UPLOAD_DIR, f"hidden_{image.filename}.png")

    with open(input_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    # Ocultamos el mensaje
    try:
        hide_message(input_path, message, output_path)
    except ValueError as e:
        return {"error": str(e)}

    # Devolvemos la imagen modificada
    return FileResponse(
        path=output_path,
        media_type="image/png",
        filename=f"hidden_{image.filename}.png"
    )


@app.post("/extract")
async def extract(
    image: UploadFile = File(...)
):
    """
    Recibe una imagen y extrae el mensaje oculto si existe.
    """
    # Guardamos la imagen en la carpeta uploads
    input_path = os.path.join(UPLOAD_DIR, f"extract_{image.filename}")

    with open(input_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    # Extraemos el mensaje
    message = extract_message(input_path)

    return {"message": message}


@app.post("/forensics")
async def forensics(
    image: UploadFile = File(...)
):
    """
    Recibe una imagen y devuelve un informe forense completo.
    """
    # Guardamos la imagen en la carpeta uploads
    input_path = os.path.join(UPLOAD_DIR, f"forensics_{image.filename}")

    with open(input_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    # Generamos el informe forense
    report = full_forensic_report(input_path)

    return report
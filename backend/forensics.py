from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np

def get_exif_metadata(image_path: str) -> dict:
    """
    Extrae los metadatos EXIF de una imagen.

    Args:
        image_path: ruta de la imagen a analizar

    Returns:
        Diccionario con los metadatos EXIF o mensaje indicando que no hay
    """
    img = Image.open(image_path)
    exif_data = {}

    # Intentamos extraer los datos EXIF
    try:
        raw_exif = img._getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = str(value)
        else:
            exif_data["info"] = "La imagen no contiene metadatos EXIF"
    except Exception:
        exif_data["info"] = "La imagen no contiene metadatos EXIF"

    return exif_data


def get_histogram(image_path: str) -> dict:
    """
    Calcula el histograma de los canales de color R, G y B.

    Args:
        image_path: ruta de la imagen a analizar

    Returns:
        Diccionario con los histogramas de cada canal
    """
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img)

    return {
        "R": pixels[:, :, 0].flatten().tolist(),
        "G": pixels[:, :, 1].flatten().tolist(),
        "B": pixels[:, :, 2].flatten().tolist()
    }


def analyze_lsb(image_path: str) -> dict:
    """
    Analiza los bits menos significativos de la imagen para detectar
    posibles mensajes ocultos.

    Args:
        image_path: ruta de la imagen a analizar

    Returns:
        Diccionario con métricas estadísticas del análisis LSB
    """
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img).flatten()

    # Extraemos los LSB de todos los píxeles
    lsbs = pixels & 1

    # Calculamos la proporción de 0s y 1s
    total = len(lsbs)
    ones = int(np.sum(lsbs))
    zeros = total - ones
    ratio_ones = round(ones / total, 4)
    ratio_zeros = round(zeros / total, 4)

    # En una imagen natural los LSB tienden a estar equilibrados
    # Una proporción muy cercana a 0.5 puede indicar manipulación LSB
    suspicion_score = round(1 - abs(ratio_ones - 0.5) * 2, 4)

    return {
        "total_pixels_analyzed": total,
        "lsb_ones": ones,
        "lsb_zeros": zeros,
        "ratio_ones": ratio_ones,
        "ratio_zeros": zeros / total,
        "suspicion_score": suspicion_score,
        "interpretation": interpret_suspicion(suspicion_score)
    }


def interpret_suspicion(score: float) -> str:
    """
    Interpreta la puntuación de sospecha del análisis LSB.
    """
    if score >= 0.95:
        return "⚠️ Alta probabilidad de mensaje oculto"
    elif score >= 0.75:
        return "🔶 Posible manipulación LSB detectada"
    elif score >= 0.50:
        return "🔵 Imagen sospechosa, análisis inconcluso"
    else:
        return "✅ Imagen aparentemente limpia"


def full_forensic_report(image_path: str) -> dict:
    """
    Genera un informe forense completo de la imagen.
    """
    img = Image.open(image_path)

    return {
        "filename": image_path.split("/")[-1],
        "format": img.format,
        "mode": img.mode,
        "size": {"width": img.size[0], "height": img.size[1]},
        "exif": get_exif_metadata(image_path),
        "lsb_analysis": analyze_lsb(image_path)
    }
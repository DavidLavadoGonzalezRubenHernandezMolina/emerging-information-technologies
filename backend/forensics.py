from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np


def get_exif_metadata(image_path: str) -> dict:
    img = Image.open(image_path)
    exif_data = {}
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
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img)
    return {
        "R": pixels[:, :, 0].flatten().tolist(),
        "G": pixels[:, :, 1].flatten().tolist(),
        "B": pixels[:, :, 2].flatten().tolist()
    }


def analyze_lsb(image_path: str) -> dict:
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img).flatten()

    # Extraemos los LSB de todos los píxeles
    lsbs = pixels & 1
    total = len(lsbs)
    ones = int(np.sum(lsbs))
    zeros = total - ones
    ratio_ones = round(ones / total, 4)
    ratio_zeros = round(zeros / total, 4)

    # Análisis de pares consecutivos
    pairs = lsbs[:-1] ^ lsbs[1:]
    pair_changes = int(np.sum(pairs))
    pair_change_ratio = round(pair_changes / (total - 1), 4)

    # Análisis de bloques de 8 bits recortando para que sea divisible
    trimmed = lsbs[:total - (total % 8)]
    block_variance = round(float(np.var(trimmed.reshape(-1, 8).mean(axis=1))), 6)

    # Combinamos las tres métricas
    score_balance = 1 - abs(ratio_ones - 0.5) * 2
    score_pairs = pair_change_ratio * 2 if pair_change_ratio > 0.5 else 0
    score_variance = min(block_variance * 1000, 1.0)

    suspicion_score = round((score_balance * 0.4 + score_pairs * 0.4 + score_variance * 0.2), 4)
    suspicion_score = min(suspicion_score, 1.0)

    return {
        "total_pixels_analyzed": total,
        "lsb_ones": ones,
        "lsb_zeros": zeros,
        "ratio_ones": ratio_ones,
        "ratio_zeros": ratio_zeros,
        "pair_change_ratio": pair_change_ratio,
        "block_variance": block_variance,
        "suspicion_score": suspicion_score,
        "interpretation": interpret_suspicion(suspicion_score)
    }


def interpret_suspicion(score: float) -> str:
    if score >= 0.95:
        return "⚠️ Alta probabilidad de mensaje oculto"
    elif score >= 0.75:
        return "🔶 Posible manipulación LSB detectada"
    elif score >= 0.50:
        return "🔵 Imagen sospechosa, análisis inconcluso"
    else:
        return "✅ Imagen aparentemente limpia"


def full_forensic_report(image_path: str) -> dict:
    img = Image.open(image_path)
    return {
        "filename": image_path.split("/")[-1],
        "format": img.format,
        "mode": img.mode,
        "size": {"width": img.size[0], "height": img.size[1]},
        "exif": get_exif_metadata(image_path),
        "histogram": get_histogram(image_path),
        "lsb_analysis": analyze_lsb(image_path)
    }
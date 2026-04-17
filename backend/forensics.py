"""
Analizador esteganográfico multicapa.

Capas:
  1. Análisis de archivo: datos tras EOF, chunks raros, tamaño anómalo.
  2. Análisis estadístico de píxeles:
     - Chi-square attack (Westfeld-Pfitzmann)
     - RS Analysis (Fridrich-Goljan-Du)
     - Ruptura de correlación espacial del LSB
  3. Puntuación combinada con veredicto por niveles.
"""
import os
import struct
import warnings
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
from scipy import stats

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ---------------------------------------------------------------------------
# CAPA 1: ANÁLISIS DEL ARCHIVO
# ---------------------------------------------------------------------------

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_STANDARD_CHUNKS = {
    b"IHDR", b"PLTE", b"IDAT", b"IEND",
    b"tRNS", b"cHRM", b"gAMA", b"iCCP", b"sBIT", b"sRGB",
    b"cICP", b"mDCv", b"cLLi",
    b"tEXt", b"zTXt", b"iTXt",
    b"bKGD", b"hIST", b"pHYs", b"sPLT", b"eXIf",
    b"tIME", b"acTL", b"fcTL", b"fdAT",
}


def analyze_png_file(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()

    result = {
        "trailing_bytes": 0,
        "unknown_chunks": [],
        "total_chunks": 0,
        "has_trailing_data": False,
        "suspicious_chunks": False,
    }

    if not data.startswith(PNG_SIGNATURE):
        return result

    offset = len(PNG_SIGNATURE)
    iend_end = None

    while offset < len(data) - 8:
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        result["total_chunks"] += 1

        if chunk_type not in PNG_STANDARD_CHUNKS:
            result["unknown_chunks"].append(
                chunk_type.decode("latin-1", errors="replace")
            )

        chunk_end = offset + 8 + length + 4
        if chunk_type == b"IEND":
            iend_end = chunk_end
            break
        offset = chunk_end
        if offset > len(data):
            break

    if iend_end is not None:
        result["trailing_bytes"] = len(data) - iend_end
        result["has_trailing_data"] = result["trailing_bytes"] > 0

    result["suspicious_chunks"] = len(result["unknown_chunks"]) > 0
    return result


def analyze_jpeg_file(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()

    result = {"trailing_bytes": 0, "has_trailing_data": False}
    if not data.startswith(b"\xff\xd8"):
        return result

    eoi_pos = data.rfind(b"\xff\xd9")
    if eoi_pos != -1:
        result["trailing_bytes"] = len(data) - (eoi_pos + 2)
        result["has_trailing_data"] = result["trailing_bytes"] > 0
    return result


def analyze_file_layer(path, width, height, img_format):
    size_bytes = os.path.getsize(path)
    pixels = width * height

    report = {
        "file_size_bytes": size_bytes,
        "pixels": pixels,
        "bytes_per_pixel": round(size_bytes / pixels, 4) if pixels > 0 else 0,
        "format": img_format,
    }

    if img_format == "PNG":
        report.update(analyze_png_file(path))
    elif img_format in ("JPEG", "JPG"):
        report.update(analyze_jpeg_file(path))

    report["size_anomaly"] = False
    if img_format == "PNG" and report["bytes_per_pixel"] > 4.0:
        report["size_anomaly"] = True
    elif img_format in ("JPEG", "JPG") and report["bytes_per_pixel"] > 1.5:
        report["size_anomaly"] = True

    file_score = 0.0
    reasons = []
    trailing = report.get("trailing_bytes", 0)
    if report.get("has_trailing_data") and trailing > 16:
        file_score = max(file_score, 0.95)
        reasons.append(f"Datos tras fin de archivo ({trailing} bytes)")
    if report.get("suspicious_chunks"):
        file_score = max(file_score, 0.55)
        reasons.append(
            f"Chunks PNG no estándar: {report['unknown_chunks']}"
        )
    if report.get("size_anomaly"):
        file_score = max(file_score, 0.4)
        reasons.append(
            f"Tamaño inusualmente grande ({report['bytes_per_pixel']} B/px)"
        )

    report["file_layer_score"] = round(file_score, 4)
    report["file_layer_reasons"] = reasons
    return report


# ---------------------------------------------------------------------------
# CAPA 2: ANÁLISIS ESTADÍSTICO
# ---------------------------------------------------------------------------

def chi_square_attack(channel: np.ndarray) -> float:
    hist = np.bincount(channel.flatten(), minlength=256).astype(float)
    observed, expected = [], []
    for i in range(0, 256, 2):
        pair_sum = hist[i] + hist[i + 1]
        if pair_sum >= 5:
            observed.append(hist[i + 1])
            expected.append(pair_sum / 2.0)
    if len(observed) < 2:
        return 0.0
    observed = np.array(observed)
    expected = np.array(expected)
    chi2 = np.sum((observed - expected) ** 2 / expected)
    df = len(observed) - 1
    return float(1.0 - stats.chi2.cdf(chi2, df))


def _rs_groups(channel, mask):
    flat = channel.flatten().astype(np.int16)
    trim = len(flat) - (len(flat) % 4)
    groups = flat[:trim].reshape(-1, 4)
    f_original = np.sum(np.abs(np.diff(groups, axis=1)), axis=1)

    flipped = groups.copy()
    pos = mask == 1
    if np.any(pos):
        flipped[:, pos] = flipped[:, pos] ^ 1
    neg = mask == -1
    if np.any(neg):
        vals = flipped[:, neg].astype(np.int16)
        vals = ((vals + 1) ^ 1) - 1
        flipped[:, neg] = vals

    f_flipped = np.sum(np.abs(np.diff(flipped, axis=1)), axis=1)
    R = int(np.sum(f_flipped > f_original))
    S = int(np.sum(f_flipped < f_original))
    total = len(groups)
    return (R / total, S / total) if total else (0, 0)


def rs_analysis(channel: np.ndarray) -> float:
    M = np.array([0, 1, 1, 0])
    minus_M = -M
    r_m, s_m = _rs_groups(channel, M)
    r_neg, s_neg = _rs_groups(channel, minus_M)
    flipped = channel ^ 1
    r_m1, s_m1 = _rs_groups(flipped, M)
    r_neg1, s_neg1 = _rs_groups(flipped, minus_M)

    d0 = r_m - s_m
    d1 = r_m1 - s_m1
    dm0 = r_neg - s_neg
    dm1 = r_neg1 - s_neg1

    a = 2.0 * (d1 + d0)
    b = dm0 - dm1 - d1 - 3.0 * d0
    c = d0 - dm0

    if abs(a) < 1e-12:
        x = -c / b if abs(b) > 1e-12 else 0.0
    else:
        disc = b * b - 4.0 * a * c
        if disc < 0:
            x = 0.0
        else:
            sqrt_disc = np.sqrt(disc)
            x1 = (-b + sqrt_disc) / (2.0 * a)
            x2 = (-b - sqrt_disc) / (2.0 * a)
            x = x1 if abs(x1) < abs(x2) else x2

    if abs(x - 0.5) < 1e-12:
        return 0.0
    p = x / (x - 0.5)
    return float(np.clip(abs(p), 0.0, 1.0))


def lsb_spatial_break(channel: np.ndarray) -> float:
    """
    Compara la correlación espacial del LSB con la del segundo bit,
    promediando correlaciones horizontales y verticales.

    En imagen natural:    ratio ~ 0.45 - 0.65
    LSB 10% modificado:   ratio ~ 0.30 - 0.40
    LSB saturado:         ratio ~ 0
    """
    arr = channel.astype(np.uint8)
    lsb = arr & 1
    bit1 = (arr >> 1) & 1

    try:
        c_lsb_h = np.corrcoef(lsb[:, :-1].flatten(), lsb[:, 1:].flatten())[0, 1]
        c_b1_h = np.corrcoef(bit1[:, :-1].flatten(), bit1[:, 1:].flatten())[0, 1]
        c_lsb_v = np.corrcoef(lsb[:-1, :].flatten(), lsb[1:, :].flatten())[0, 1]
        c_b1_v = np.corrcoef(bit1[:-1, :].flatten(), bit1[1:, :].flatten())[0, 1]
    except Exception:
        return 0.0

    vals = [c_lsb_h, c_b1_h, c_lsb_v, c_b1_v]
    if any(np.isnan(v) for v in vals):
        return 0.0

    c_lsb = (c_lsb_h + c_lsb_v) / 2.0
    c_b1 = (c_b1_h + c_b1_v) / 2.0

    # Si la imagen apenas tiene estructura (bit1 casi incorrelado),
    # no podemos inferir nada fiable de este test.
    if c_b1 < 0.03:
        return 0.0

    ratio = c_lsb / c_b1
    # 0.50+ = natural, 0.05 o menos = totalmente roto
    if ratio >= 0.50:
        return 0.0
    if ratio <= 0.05:
        return 1.0
    return float((0.50 - ratio) / 0.45)


def analyze_pixel_layer(image_path: str) -> dict:
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img)
    r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]

    chi = float(np.mean([chi_square_attack(c) for c in (r, g, b)]))
    rs = float(np.mean([rs_analysis(c) for c in (r, g, b)]))
    spc = float(np.mean([lsb_spatial_break(c) for c in (r, g, b)]))

    # Combinación equilibrada: media ponderada.
    weighted = rs * 0.40 + spc * 0.40 + chi * 0.20

    # Un único indicador muy fuerte ya debería alertar, aunque otros callen
    # (el mensaje cifrado rompe unos indicadores pero no siempre todos).
    strongest = max(rs, spc, chi)

    # Tomamos el mayor entre la media ponderada y el 0.7 × el más fuerte.
    pixel_score = max(weighted, strongest * 0.70)
    pixel_score = float(np.clip(pixel_score, 0.0, 1.0))

    flat = pixels.flatten()
    ratio_ones = float(np.sum(flat & 1)) / len(flat)

    return {
        "chi_square": round(chi, 4),
        "rs_analysis": round(rs, 4),
        "lsb_spatial_break": round(spc, 4),
        "lsb_ratio_ones": round(ratio_ones, 4),
        "pixel_layer_score": round(pixel_score, 4),
    }


# ---------------------------------------------------------------------------
# CAPA 3: COMBINACIÓN
# ---------------------------------------------------------------------------

def interpret(score: float) -> str:
    if score >= 0.75:
        return "⚠️ Alta probabilidad de contenido oculto"
    elif score >= 0.45:
        return "🔶 Imagen sospechosa — revisar manualmente"
    elif score >= 0.20:
        return "🔵 Anomalías leves, probablemente limpia"
    else:
        return "✅ Imagen aparentemente limpia"


def get_exif_metadata(image_path: str) -> dict:
    img = Image.open(image_path)
    exif_data = {}
    try:
        raw = img._getexif()
        if raw:
            for tag_id, value in raw.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = str(value)[:200]
        else:
            exif_data["info"] = "Sin metadatos EXIF"
    except Exception:
        exif_data["info"] = "Sin metadatos EXIF"
    return exif_data


def full_analysis(image_path: str) -> dict:
    img = Image.open(image_path)
    width, height = img.size
    img_format = img.format or "UNKNOWN"

    file_report = analyze_file_layer(image_path, width, height, img_format)
    pixel_report = analyze_pixel_layer(image_path)

    file_s = file_report["file_layer_score"]
    pixel_s = pixel_report["pixel_layer_score"]

    if file_s >= 0.9:
        final_score = file_s
    else:
        final_score = max(file_s, pixel_s * 0.90 + file_s * 0.10)
    final_score = round(float(final_score), 4)

    return {
        "filename": os.path.basename(image_path),
        "format": img_format,
        "size": {"width": width, "height": height},
        "exif": get_exif_metadata(image_path),
        "file_analysis": file_report,
        "pixel_analysis": pixel_report,
        "final_score": final_score,
        "verdict": interpret(final_score),
    }
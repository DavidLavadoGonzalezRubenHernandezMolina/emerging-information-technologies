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
# FIRMAS DE ARCHIVOS (magic bytes) que NO deberían aparecer dentro de una imagen
# ---------------------------------------------------------------------------

EMBEDDED_SIGNATURES = [
    # (firma, nombre) — solo firmas suficientemente largas (≥4 bytes)
    # para minimizar falsos positivos por azar
    (b"PK\x03\x04", "ZIP / JAR / DOCX / XLSX"),
    (b"PK\x05\x06", "ZIP (empty archive)"),
    (b"Rar!\x1a\x07", "RAR"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip"),
    (b"%PDF-", "PDF"),
    (b"#!/bin/bash", "Script bash"),
    (b"#!/bin/sh", "Script sh"),
    (b"#!/usr/bin/env", "Script (shebang env)"),
    (b"#!/usr/bin/python", "Script Python"),
    (b"#!/usr/bin/perl", "Script Perl"),
    (b"<?php", "Código PHP"),
    (b"<html", "HTML"),
    (b"<!DOCTYPE", "HTML / XML"),
    (b"<script", "JavaScript"),
    (b"\x7fELF", "Ejecutable Linux (ELF)"),
    (b"\xca\xfe\xba\xbe", "Java class"),
    (b"-----BEGIN RSA PRIVATE KEY", "Clave privada RSA"),
    (b"-----BEGIN OPENSSH PRIVATE KEY", "Clave privada SSH"),
    (b"-----BEGIN CERTIFICATE-----", "Certificado"),
]


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


# ---------------------------------------------------------------------------
# CAPA B: Magic bytes embebidos
# ---------------------------------------------------------------------------

def _png_idat_ranges(data: bytes):
    """Devuelve lista de (start, end) de cada chunk IDAT para excluirlos
    de la búsqueda de firmas. Los datos comprimidos de IDAT pueden contener
    cualquier secuencia por azar y producen falsos positivos."""
    ranges = []
    if not data.startswith(PNG_SIGNATURE):
        return ranges
    offset = len(PNG_SIGNATURE)
    while offset < len(data) - 8:
        try:
            length = struct.unpack(">I", data[offset:offset + 4])[0]
            chunk_type = data[offset + 4:offset + 8]
            data_start = offset + 8
            data_end = data_start + length
            if chunk_type == b"IDAT":
                ranges.append((data_start, data_end))
            if chunk_type == b"IEND":
                break
            offset = data_end + 4
        except Exception:
            break
    return ranges


def _in_any_range(pos: int, ranges) -> bool:
    for s, e in ranges:
        if s <= pos < e:
            return True
    return False


def search_embedded_signatures(path: str, img_format: str) -> dict:
    """Busca firmas de archivos conocidos dentro del contenido del fichero.
    Excluye la cabecera de imagen y, para PNG, los chunks IDAT comprimidos
    donde pueden aparecer falsos positivos por azar."""
    with open(path, "rb") as f:
        data = f.read()

    # Zonas a excluir de la búsqueda
    excluded_ranges = []
    if img_format == "PNG":
        excluded_ranges = _png_idat_ranges(data)
    # Siempre se excluyen los primeros bytes (cabecera)
    header_skip = 16

    findings = []
    for sig, desc in EMBEDDED_SIGNATURES:
        start = header_skip
        while True:
            pos = data.find(sig, start)
            if pos == -1:
                break
            if not _in_any_range(pos, excluded_ranges):
                findings.append({
                    "signature": desc,
                    "offset": pos,
                    "bytes": sig.hex(),
                })
                # Una única aparición por firma basta para demo
                break
            start = pos + 1

    return {
        "embedded_findings": findings,
        "embedded_count": len(findings),
    }


# ---------------------------------------------------------------------------
# CAPA C: Cadenas ASCII imprimibles sospechosas
# ---------------------------------------------------------------------------

# Caracteres ASCII imprimibles: 32 (espacio) a 126 (~), más tab (9), LF (10), CR (13)
_PRINTABLE_SET = set(range(32, 127)) | {9, 10, 13}


def search_printable_strings(path: str, img_format: str,
                             min_length: int = 30,
                             max_samples: int = 5) -> dict:
    """Busca cadenas largas de ASCII imprimible dentro del archivo.

    En una imagen binaria no deberían aparecer cadenas ASCII de 30+
    caracteres consecutivos fuera de zonas EXIF legítimas.
    Excluye zonas EXIF conocidas y chunks IDAT (PNG) para evitar falsos
    positivos.
    """
    with open(path, "rb") as f:
        data = f.read()

    # Zonas a excluir (igual que firmas, más cabecera EXIF si hay)
    excluded_ranges = []
    if img_format == "PNG":
        excluded_ranges = _png_idat_ranges(data)
    # En JPEG excluimos los segmentos APP (FF E0 .. FF EF) donde suele
    # ir el EXIF, JFIF, ICC, etc. — son texto legítimo de la cámara.
    if img_format in ("JPEG", "JPG"):
        excluded_ranges = _jpeg_app_ranges(data)

    # Escaneo de runs de ASCII imprimible
    strings_found = []
    current_start = None
    current_bytes = bytearray()

    for i, byte in enumerate(data):
        if byte in _PRINTABLE_SET and not _in_any_range(i, excluded_ranges):
            if current_start is None:
                current_start = i
            current_bytes.append(byte)
        else:
            if current_start is not None and len(current_bytes) >= min_length:
                strings_found.append({
                    "offset": current_start,
                    "length": len(current_bytes),
                    "preview": current_bytes[:80].decode("ascii",
                                                         errors="replace"),
                })
            current_start = None
            current_bytes = bytearray()

    # Cadena final si el archivo termina en run
    if current_start is not None and len(current_bytes) >= min_length:
        strings_found.append({
            "offset": current_start,
            "length": len(current_bytes),
            "preview": current_bytes[:80].decode("ascii", errors="replace"),
        })

    # Ordenamos por longitud descendente y nos quedamos con las más largas
    strings_found.sort(key=lambda s: s["length"], reverse=True)
    samples = strings_found[:max_samples]

    return {
        "printable_strings_count": len(strings_found),
        "printable_strings_samples": samples,
    }


def _jpeg_app_ranges(data: bytes):
    """Zonas APP (EXIF, JFIF, ICC...) de un JPEG que contienen texto legítimo
    y deben excluirse del escaneo de ASCII."""
    ranges = []
    if not data.startswith(b"\xff\xd8"):
        return ranges
    i = 2
    while i < len(data) - 4:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # Start of Scan (FFDA) marca el fin de segmentos, a partir de ahí
        # ya son datos comprimidos
        if marker == 0xDA or marker == 0xD9:
            # Excluimos también los datos comprimidos hasta el final
            ranges.append((i, len(data)))
            break
        # Segmentos APPn (E0-EF) y COM (FE) con longitud
        if (0xE0 <= marker <= 0xEF) or marker == 0xFE:
            try:
                seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
                ranges.append((i, i + 2 + seg_len))
                i += 2 + seg_len
                continue
            except Exception:
                break
        # Otros segmentos con longitud (DHT, DQT, SOF, etc.)
        # También los excluimos porque pueden contener secuencias que
        # parecen ASCII por azar (tablas Huffman, cuantización...).
        if 0xC0 <= marker <= 0xFE and marker not in (0xD8, 0xD9):
            try:
                seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
                ranges.append((i, i + 2 + seg_len))
                i += 2 + seg_len
                continue
            except Exception:
                break
        i += 1
    return ranges


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

    # Búsqueda de magic bytes embebidos (aplica a cualquier formato)
    report.update(search_embedded_signatures(path, img_format))
    # Búsqueda de cadenas ASCII imprimibles sospechosas
    report.update(search_printable_strings(path, img_format))

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
    # Firmas embebidas: alerta muy fuerte
    if report.get("embedded_count", 0) > 0:
        file_score = max(file_score, 0.95)
        found_names = [f["signature"] for f in report["embedded_findings"]]
        reasons.append(
            f"Archivos embebidos detectados: {', '.join(found_names)}"
        )
    # Cadenas ASCII largas fuera de zonas EXIF = sospechoso
    n_strings = report.get("printable_strings_count", 0)
    if n_strings >= 3:
        file_score = max(file_score, 0.80)
        reasons.append(
            f"{n_strings} cadenas ASCII largas fuera de metadatos"
        )
    elif n_strings == 1 or n_strings == 2:
        file_score = max(file_score, 0.55)
        reasons.append(
            f"{n_strings} cadena(s) ASCII sospechosa(s) detectada(s)"
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


# ---------------------------------------------------------------------------
# CAPA D: Correlación LSB local por bloques
# ---------------------------------------------------------------------------

def _block_lsb_correlation(block_lsb: np.ndarray) -> float:
    """Correlación espacial horizontal promedio del LSB de un bloque.
    Imagen natural: ~0.10-0.20. Mensaje cifrado embebido: ~0.
    """
    if block_lsb.shape[1] < 2:
        return 0.0
    left = block_lsb[:, :-1].flatten().astype(np.float32)
    right = block_lsb[:, 1:].flatten().astype(np.float32)
    if left.std() < 1e-9 or right.std() < 1e-9:
        return 0.0
    c = np.corrcoef(left, right)[0, 1]
    if np.isnan(c):
        return 0.0
    return float(c)


def local_entropy_anomaly(channel: np.ndarray,
                          block_size: int = 32) -> dict:
    """
    Divide el canal en bloques y mide la correlación espacial del LSB
    en cada bloque.

    En un bloque natural la correlación LSB ronda 0.10-0.20 porque los
    píxeles vecinos comparten estructura (aunque sea en ruido).
    En un bloque con mensaje cifrado embebido la correlación cae a ~0
    porque los LSBs pasan a ser pseudoaleatorios.

    Un bloque es "sospechoso" cuando su correlación cae muy por debajo
    de la mediana de toda la imagen.
    """
    h, w = channel.shape
    if h < block_size * 2 or w < block_size * 2:
        return {"suspicious_blocks": 0,
                "total_blocks": 0,
                "median_correlation": 0.0,
                "min_correlation": 0.0,
                "suspicion": 0.0}

    lsb = (channel & 1).astype(np.uint8)

    corrs = []
    for y in range(0, h - block_size + 1, block_size):
        for x in range(0, w - block_size + 1, block_size):
            block = lsb[y:y + block_size, x:x + block_size]
            corrs.append(_block_lsb_correlation(block))

    corrs = np.array(corrs)
    if corrs.size == 0:
        return {"suspicious_blocks": 0,
                "total_blocks": 0,
                "median_correlation": 0.0,
                "min_correlation": 0.0,
                "suspicion": 0.0}

    median_c = float(np.median(corrs))
    min_c = float(np.min(corrs))
    p75 = float(np.percentile(corrs, 75))

    # Caso 1: toda la imagen tiene correlación LSB baja (LSB_FULL o imagen
    # casi plana). Este caso lo cogen otras capas (chi², SPC), no es trabajo
    # de esta métrica.
    if p75 < 0.05:
        return {"suspicious_blocks": 0,
                "total_blocks": int(corrs.size),
                "median_correlation": round(median_c, 4),
                "min_correlation": round(min_c, 4),
                "suspicion": 0.0}

    # Caso 2: la imagen en general tiene correlación normal (p75 >= 0.05)
    # pero hay bloques con correlación cercana a 0 (consistente con datos
    # aleatorios localizados). El umbral absoluto es 0.02.
    suspicious = int(np.sum(corrs < 0.02))
    total = int(corrs.size)
    frac = suspicious / total if total else 0.0

    # Esperamos que una imagen natural tenga pocos bloques con corr<0.02.
    # Mapeo a sospecha:
    #   <2% de bloques raros  -> 0.0 (ruido normal en zonas uniformes)
    #   5% bloques raros      -> 0.5
    #   >12% bloques raros    -> 1.0
    if frac <= 0.02:
        suspicion = 0.0
    elif frac >= 0.12:
        suspicion = 1.0
    else:
        suspicion = (frac - 0.02) / 0.10

    return {
        "suspicious_blocks": suspicious,
        "total_blocks": total,
        "median_correlation": round(median_c, 4),
        "min_correlation": round(min_c, 4),
        "suspicion": round(float(suspicion), 4),
    }


def analyze_pixel_layer(image_path: str) -> dict:
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img)
    r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]

    chi = float(np.mean([chi_square_attack(c) for c in (r, g, b)]))
    rs = float(np.mean([rs_analysis(c) for c in (r, g, b)]))
    spc = float(np.mean([lsb_spatial_break(c) for c in (r, g, b)]))

    # Capa D: métrica informativa de correlación LSB local por bloques.
    # No participa en el score final porque los bloques de 32×32 en
    # imágenes naturales son demasiado ruidosos para dar una señal fiable;
    # queda expuesta para inspección manual.
    entropy_r = local_entropy_anomaly(r)
    ent_blocks_total = entropy_r["total_blocks"]
    ent_blocks_susp = entropy_r["suspicious_blocks"]
    ent_median_corr = entropy_r["median_correlation"]

    # Combinación equilibrada: media ponderada.
    weighted = rs * 0.40 + spc * 0.40 + chi * 0.20

    # Un único indicador muy fuerte ya debería alertar, aunque otros callen.
    strongest = max(rs, spc, chi)

    pixel_score = max(weighted, strongest * 0.70)
    pixel_score = float(np.clip(pixel_score, 0.0, 1.0))

    flat = pixels.flatten()
    ratio_ones = float(np.sum(flat & 1)) / len(flat)

    return {
        "chi_square": round(chi, 4),
        "rs_analysis": round(rs, 4),
        "lsb_spatial_break": round(spc, 4),
        "local_blocks_low_correlation": ent_blocks_susp,
        "local_blocks_total": ent_blocks_total,
        "local_median_correlation": ent_median_corr,
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
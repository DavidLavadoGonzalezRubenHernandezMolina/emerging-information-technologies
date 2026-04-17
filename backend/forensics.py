from PIL import Image
from PIL.ExifTags import TAGS
import numpy as np
from scipy import stats


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


def chi_square_attack(channel: np.ndarray) -> float:
    """
    Chi-square attack: detecta si los pares de valores (2k, 2k+1)
    tienen frecuencias anormalmente similares, lo que indica LSB embedding.
    En imágenes naturales estos pares son distintos.
    En imágenes con LSB embedding tienden a igualarse.
    """
    hist = np.bincount(channel.flatten(), minlength=256).astype(float)

    # Agrupamos en pares (0,1), (2,3), (4,5)...
    observed = []
    expected = []
    for i in range(0, 255, 2):
        pair_sum = hist[i] + hist[i + 1]
        if pair_sum > 0:
            observed.append(hist[i])
            expected.append(pair_sum / 2)

    observed = np.array(observed)
    expected = np.array(expected)

    # Evitamos división por cero
    mask = expected > 0
    observed = observed[mask]
    expected = expected[mask]

    if len(observed) == 0:
        return 0.0

    chi2 = np.sum((observed - expected) ** 2 / expected)
    df = len(observed) - 1

    # p-value: cuanto más bajo más sospechoso
    p_value = 1 - stats.chi2.cdf(chi2, df)

    # Convertimos a puntuación de sospecha (inverso del p-value)
    suspicion = round(1 - min(p_value, 1.0), 4)
    return suspicion


def rs_analysis(channel: np.ndarray) -> float:
    """
    RS Analysis: compara grupos de píxeles regulares (R),
    singulares (S) e irregulares (I) antes y después de flipear LSBs.
    Es uno de los métodos más precisos para detectar LSB embedding.
    """
    def discrimination(group):
        return np.sum(np.abs(np.diff(group.astype(float))))

    def flip_lsb(pixels):
        return pixels ^ 1

    def flip_lsb_neg(pixels):
        result = pixels.copy()
        result[result % 2 == 0] += 1
        result[result % 2 == 1] -= 1
        return np.clip(result, 0, 255)

    flat = channel.flatten()
    # Recortamos para que sea divisible entre 4
    trim = len(flat) - (len(flat) % 4)
    flat = flat[:trim].reshape(-1, 4)

    R, S, I = 0, 0, 0
    Rm, Sm, Im = 0, 0, 0

    for group in flat:
        f = discrimination(group)
        f_flip = discrimination(flip_lsb(group))
        f_flip_neg = discrimination(flip_lsb_neg(group))

        if f_flip > f:
            R += 1
        elif f_flip < f:
            S += 1
        else:
            I += 1

        if f_flip_neg > f:
            Rm += 1
        elif f_flip_neg < f:
            Sm += 1
        else:
            Im += 1

    total = len(flat)
    if total == 0:
        return 0.0

    r = R / total
    s = S / total
    rm = Rm / total
    sm = Sm / total

    # Si R ≈ Rm y S ≈ Sm la imagen es sospechosa
    diff = abs(r - rm) + abs(s - sm)
    suspicion = round(1 - min(diff * 2, 1.0), 4)
    return suspicion


def analyze_lsb(image_path: str) -> dict:
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img)

    r_channel = pixels[:, :, 0]
    g_channel = pixels[:, :, 1]
    b_channel = pixels[:, :, 2]

    flat = pixels.flatten()
    lsbs = flat & 1
    total = len(lsbs)
    ones = int(np.sum(lsbs))
    zeros = total - ones
    ratio_ones = round(ones / total, 4)
    ratio_zeros = round(zeros / total, 4)

    # Chi-square attack en los tres canales
    chi_r = chi_square_attack(r_channel)
    chi_g = chi_square_attack(g_channel)
    chi_b = chi_square_attack(b_channel)
    chi_score = round((chi_r + chi_g + chi_b) / 3, 4)

    # RS Analysis en canal rojo (el más usado para LSB)
    rs_score = rs_analysis(r_channel)

    # Puntuación de equilibrio LSB básica
    balance_score = round(1 - abs(ratio_ones - 0.5) * 2, 4)

    # Puntuación final combinada
    # Chi-square y RS tienen más peso por ser más precisos
    suspicion_score = round(
        chi_score * 0.45 +
        rs_score * 0.45 +
        balance_score * 0.10,
        4
    )
    suspicion_score = min(suspicion_score, 1.0)

    return {
        "total_pixels_analyzed": total,
        "lsb_ones": ones,
        "lsb_zeros": zeros,
        "ratio_ones": ratio_ones,
        "ratio_zeros": ratio_zeros,
        "chi_square_score": chi_score,
        "rs_analysis_score": rs_score,
        "suspicion_score": suspicion_score,
        "interpretation": interpret_suspicion(suspicion_score)
    }


def interpret_suspicion(score: float) -> str:
    if score >= 0.90:
        return "⚠️ Alta probabilidad de mensaje oculto"
    elif score >= 0.70:
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
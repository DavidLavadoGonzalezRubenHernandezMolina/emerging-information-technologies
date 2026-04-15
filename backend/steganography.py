from PIL import Image   #libreria para abrir y guardar imagenes
import numpy as np      #libreria para tratar pixeles como array 

# Delimitador que marca el fin del mensaje oculto
DELIMITER = "###FIN###"

def hide_message(image_path: str, message: str, output_path: str) -> None:
    """
    Oculta un mensaje de texto dentro de una imagen usando LSB.
    
    Args:
        image_path: ruta de la imagen original
        message: mensaje a ocultar
        output_path: ruta donde guardar la imagen modificada
    """
    # Abrimos la imagen y la convertimos a RGB
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img)

    # Añadimos el delimitador al final del mensaje
    full_message = message + DELIMITER

    # Convertimos el mensaje a binario
    binary_message = ''.join(format(ord(c), '08b') for c in full_message)

    # Comprobamos que la imagen tiene suficientes píxeles
    max_bits = pixels.size  # filas * columnas * 3 canales
    if len(binary_message) > max_bits:
        raise ValueError("El mensaje es demasiado largo para esta imagen")

    # Ocultamos los bits en los LSB de los píxeles
    flat_pixels = pixels.flatten()
    for i, bit in enumerate(binary_message):
        flat_pixels[i] = (flat_pixels[i] & 0b11111110) | int(bit)

    # Reconstruimos la imagen y la guardamos
    result = flat_pixels.reshape(pixels.shape)
    output_img = Image.fromarray(result.astype(np.uint8))
    output_img.save(output_path, format="PNG")


def extract_message(image_path: str) -> str:
    """
    Extrae un mensaje oculto de una imagen usando LSB.
    
    Args:
        image_path: ruta de la imagen a analizar
    
    Returns:
        El mensaje oculto si se encuentra, o un mensaje indicando que no hay nada
    """
    # Abrimos la imagen y la convertimos a RGB
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img).flatten()

    # Extraemos los LSB de cada píxel
    bits = [str(pixel & 1) for pixel in pixels]

    # Agrupamos los bits en grupos de 8 y convertimos a caracteres
    chars = []
    for i in range(0, len(bits) - 7, 8):
        byte = ''.join(bits[i:i+8])
        char = chr(int(byte, 2))
        chars.append(char)

        # Comprobamos si hemos llegado al delimitador
        current_text = ''.join(chars)
        if current_text.endswith(DELIMITER):
            return current_text[:-len(DELIMITER)]

    return "No se encontró ningún mensaje oculto en esta imagen"
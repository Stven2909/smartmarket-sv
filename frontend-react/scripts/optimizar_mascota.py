import os
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "public", "mascota"))
ANCHO_MAX = 600
CALIDAD = 80
FAVICON_TAM = 64
MAPEO = {
    "Smarty_waving.png": "Smarty_waving.webp",
    "Smarty_404.png": "Smarty_404.webp",
    "Smarty_favicon-sinfondo.png": "favicon-64.png",
    "Smarty_sinfondo.png": "Smarty_sinfondo.webp",
}


def redimensionar(img, ancho_max):
    ancho, alto = img.size
    if ancho > ancho_max:
        proporcion = ancho_max / float(ancho)
        nuevo_alto = int(round(alto * proporcion))
        img = img.resize((ancho_max, nuevo_alto), Image.Resampling.LANCZOS)
    return img


def a_webp(ruta_origen, ruta_destino):
    with Image.open(ruta_origen) as img:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        img = redimensionar(img, ANCHO_MAX)
        img.save(ruta_destino, format="WEBP", quality=CALIDAD, method=6)


def a_favicon_cuadrado(ruta_origen, ruta_destino):
    with Image.open(ruta_origen) as img:
        ancho, alto = img.size
        lado = min(ancho, alto)
        izq = (ancho - lado) // 2
        sup = (alto - lado) // 2
        cuadrado = img.crop((izq, sup, izq + lado, sup + lado))
        cuadrado = cuadrado.resize((FAVICON_TAM, FAVICON_TAM), Image.Resampling.LANCZOS)
        cuadrado.save(ruta_destino, format="PNG")


def main():
    if not os.path.isdir(CARPETA):
        raise SystemExit(f"No existe la carpeta: {CARPETA}")
    for origen, destino in MAPEO.items():
        ruta_origen = os.path.join(CARPETA, origen)
        ruta_destino = os.path.join(CARPETA, destino)
        if not os.path.isfile(ruta_origen):
            print(f"[skip] no existe {origen}")
            continue
        if destino.endswith(".webp"):
            a_webp(ruta_origen, ruta_destino)
        else:
            a_favicon_cuadrado(ruta_origen, ruta_destino)
        peso_kb = os.path.getsize(ruta_destino) / 1024
        print(f"[ok] {origen} -> {destino} ({peso_kb:.0f} KB)")


if __name__ == "__main__":
    main()

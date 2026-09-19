import cv2
import numpy as np


def resize_720p(img):
    """
    Reduce la imagen a una altura máxima de 720 píxeles
    manteniendo la proporción.
    """
    h, w = img.shape[:2]
    target_h = 720

    if h > target_h:
        scale = target_h / h
        target_w = int(w * scale)

        img = cv2.resize(
            img,
            (target_w, target_h),
            interpolation=cv2.INTER_AREA
        )

    return img


# ============================================================
# 1. CARGAR IMÁGENES
# ============================================================

img1 = cv2.imread("imagen1.jpg")
img2 = cv2.imread("imagen2.jpg")

if img1 is None or img2 is None:
    print("Error: no se pudieron cargar las imágenes.")
    exit()


# ============================================================
# 2. REDUCIR A 720p
# ============================================================

img1 = resize_720p(img1)
img2 = resize_720p(img2)

# Asegurar que ambas imágenes tengan exactamente el mismo tamaño
if img1.shape[:2] != img2.shape[:2]:
    img2 = cv2.resize(
        img2,
        (img1.shape[1], img1.shape[0]),
        interpolation=cv2.INTER_AREA
    )


# ============================================================
# 3. CONVERTIR A ESCALA DE GRISES
# ============================================================

gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)


# ============================================================
# 4. NORMALIZAR ILUMINACIÓN CON CLAHE
# ============================================================

clahe = cv2.createCLAHE(
    clipLimit=2.0,
    tileGridSize=(8, 8)
)

gray1 = clahe.apply(gray1)
gray2 = clahe.apply(gray2)


# ============================================================
# 5. SUAVIZAR PARA REDUCIR RUIDO
# ============================================================

gray1 = cv2.GaussianBlur(gray1, (5, 5), 0)
gray2 = cv2.GaussianBlur(gray2, (5, 5), 0)


# ============================================================
# 6. CALCULAR GRADIENTES
# ============================================================

# Imagen 1
grad1_x = cv2.Sobel(gray1, cv2.CV_32F, 1, 0)
grad1_y = cv2.Sobel(gray1, cv2.CV_32F, 0, 1)

# Imagen 2
grad2_x = cv2.Sobel(gray2, cv2.CV_32F, 1, 0)
grad2_y = cv2.Sobel(gray2, cv2.CV_32F, 0, 1)


# ============================================================
# 7. CALCULAR MAGNITUD DE LOS GRADIENTES
# ============================================================

mag1 = cv2.magnitude(grad1_x, grad1_y)
mag2 = cv2.magnitude(grad2_x, grad2_y)


# ============================================================
# 8. CALCULAR DIFERENCIA ENTRE LAS DOS IMÁGENES
# ============================================================

diff = cv2.absdiff(mag1, mag2)


# ============================================================
# 9. CREAR MÁSCARA DE MOVIMIENTO
# ============================================================

threshold = 10

_, mask = cv2.threshold(
    diff,
    threshold,
    255,
    cv2.THRESH_BINARY
)

mask = mask.astype(np.uint8)


# ============================================================
# 10. LIMPIAR RUIDO DE LA MÁSCARA
# ============================================================

kernel = np.ones((5, 5), np.uint8)

# Eliminar pequeños puntos
mask = cv2.morphologyEx(
    mask,
    cv2.MORPH_OPEN,
    kernel
)

# Unir zonas cercanas
mask = cv2.dilate(
    mask,
    kernel,
    iterations=2
)


# ============================================================
# 11. SUPERPONER LA MÁSCARA SOBRE LA IMAGEN 1
# ============================================================

# Copia de la imagen original
overlay = img1.copy()

# Pintar de rojo las zonas donde hay movimiento
overlay[mask > 0] = (0, 0, 255)

# Mezclar imagen original y zonas rojas
resultado = cv2.addWeighted(
    img2,
    0.7,
    overlay,
    0.3,
    0
)


# ============================================================
# 12. MOSTRAR RESULTADOS
# ============================================================

cv2.imshow("Imagen 1", img1)
cv2.imshow("Imagen 2", img2)
cv2.imshow("Mascara de movimiento", mask)
cv2.imshow("Movimiento superpuesto", resultado)

cv2.waitKey(0)
cv2.destroyAllWindows()

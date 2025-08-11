from sentence_transformers import SentenceTransformer
import numpy as np

# Cargar el modelo de embeddings
model = SentenceTransformer("./models/all-MiniLM-L6-v2")

# 3 frases de ejemplo
sentences = [
    "El router no enciende.",
    "El internet es muy lento.",
    "¿Cómo reinicio el router?"
]

# Generar embeddings
embeddings = model.encode(sentences)

print("Forma de la matriz:", embeddings.shape)
print("Primer vector (primer chunk):")
print(embeddings[0])


# Ejemplo conceptual

# [Chunk 1] "El router no enciende."
# [Chunk 2] "El internet es muy lento."
# [Chunk 3] "¿Cómo reinicio el router?"

# Conversion a vectores
# Chunk 1 → [ 0.0164, 0.0376, -0.0234, ..., 0.0127 ]   # 384 valores
# Chunk 2 → [ 0.0451, -0.0043,  0.0782, ..., -0.0198 ]  # 384 valores
# Chunk 3 → [-0.0347, 0.0281,  0.0125, ..., 0.0452 ]    # 384 valores


# Forma de la matriz: (3, 384)
# 3 → número de frases
# 384 → número de dimensiones (columnas)

# El usuario pregunta "Mi router esta apagado"
# Esto se convierte en otro chunk de 384 dimensiones

# Faiss mide la distancia del vector pregunta con los vectores del indice faiss
# Devuelve el vector mas cercano

#            (Chunk 2)
#              •
#    (consulta)✱
#        \
#         \
#          • (Chunk 1)   ← Más cercano

# Texto → Embedding → FAISS Index → Consulta → Vector → Búsqueda → Chunk relevante → Respuesta


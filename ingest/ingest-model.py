import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


#Config
BASE_DATA_PATH = "./manuales/"
BASE_INDEX_DIR = "./faiss_indexes/"
EMBEDDING_MODEL = "./models/all-MiniLM-L6-v2"

#Cargar modelo
model = SentenceTransformer(EMBEDDING_MODEL)


#Funcion para cargar datos
def load_data(folder_path):
    """Carga los documentos desde un directorio. 
       Args:
           folder_path (str): Ruta al directorio que contiene los documentos.
       Returns:
           list: Lista de documentos.
    """
    documents = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".md"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                documents.append(f.read())
    return documents

#Funcion para dividir texto en fragmentos
def chunk_text(text, chunk_size=250, chunk_overlap=50):
    """Divide el texto en fragmentos.
       Args:
           text (str): Texto a dividir.
           chunk_size (int): Tamaño de cada fragmento. Si es muy corto la informacion puede ser prolija
           chunk_overlap (int): Overlap entre fragmentos. Si es muy alto puede ser redundante si es muy bajo se corta la informacion
       Returns:
           list: Lista de fragmentos.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - chunk_overlap
    return chunks

def chunk_text_smart(text, chunk_size=250, chunk_overlap=50):
    """Divide el texto en fragmentos respetando párrafos cuando es posible.
       Args:
           text (str): Texto a dividir.
           chunk_size (int): Tamaño de cada fragmento.
           chunk_overlap (int): Overlap entre fragmentos.
       Returns:
           list: Lista de fragmentos.
    """
    # parrafos se dividen con "---"
    paragraphs = text.split('---')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_words = para.split()
        para_size = len(para_words)
        
        # Si el párrafo es muy grande, dividirlo
        if para_size > chunk_size:
            # Usar el método anterior para este párrafo grande
            para_chunks = chunk_text(para, chunk_size, chunk_overlap)
            for chunk in para_chunks:
                chunks.append(chunk)
        # Si cabe en el chunk actual
        elif current_size + para_size <= chunk_size:
            current_chunk.append(para)
            current_size += para_size
        # Si no cabe, guardar el chunk actual y empezar uno nuevo
        else:
            if current_chunk:
                chunks.append('---'.join(current_chunk))
            current_chunk = [para]
            current_size = para_size
    
    # Añadir el último chunk si existe
    if current_chunk:
        chunks.append('---'.join(current_chunk))
    
    return chunks

#Funcion para crear index de faiss
def create_faiss_index(chunks):
    """Crea un index de faiss para los fragmentos.
       Args:
           chunks (list): Lista de fragmentos.
       Returns:
           tuple: (faiss.Index, dict) Index de faiss y datos de chunks.
    """
    # Crear embeddings
    embeddings = model.encode(chunks) #Convertimos el texto en embeddings (matriz de vectores Numpy)
    
    # Normalizar los vectores para mejorar la búsqueda por similitud de coseno
    faiss.normalize_L2(embeddings)
    
    dimension = embeddings.shape[1] #Es la dimension del vector de embedding ejemplo embedding.shape = (10,384) dimesion = 384, cantidad de vectores (chunks) = 10
    
    # Usar IndexFlatIP para similitud de coseno con vectores normalizados
    index = faiss.IndexFlatIP(dimension) #IP = Inner Product (para vectores normalizados = similitud coseno)
    
    index.add(embeddings)
    
    # Guardar también los chunks junto con el índice
    chunk_data = {
        "chunks": chunks,
        "embeddings": embeddings
    }
    
    return index, chunk_data

#Funcion para procesar carpeta de un router
def process_router_folder(router_folder):
    """Procesa carpeta de un router y guarda índice FAISS y chunks"""
    texts = load_data(router_folder)
    all_chunks = []
    for t in texts:
        all_chunks.extend(chunk_text_smart(t))

    index, chunk_data = create_faiss_index(all_chunks)

    router_name = os.path.basename(router_folder.rstrip("/"))
    index_path = os.path.join(BASE_INDEX_DIR, f"{router_name}.index")
    chunks_path = os.path.join(BASE_INDEX_DIR, f"{router_name}_chunks.pkl")
    
    os.makedirs(BASE_INDEX_DIR, exist_ok=True)

    # Guardar índice
    faiss.write_index(index, index_path)
    
    # Guardar chunks
    import pickle
    with open(chunks_path, 'wb') as f:
        pickle.dump(chunk_data["chunks"], f)

    print(f"[OK] Índice FAISS creado para {router_name} con {len(all_chunks)} chunks.")

if __name__ == "__main__":
    for router_folder in os.listdir(BASE_DATA_PATH):
        print(router_folder)
        folder_path = os.path.join(BASE_DATA_PATH, router_folder)
        if os.path.isdir(folder_path):
            process_router_folder(folder_path)
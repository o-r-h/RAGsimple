import os
import faiss
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer

# ==== CONFIG ====
BASE_INDEX_DIR = "faiss_indexes"
TINY_LLAMA_PATH = "./models/TinyLlama"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Verificar si es necesario regenerar índices
def check_chunks_files():
    """Verifica si los archivos de chunks existen y sugiere regenerar índices si no."""
    router_types = {
        "A": {"index": "XLM22.index", "chunks": "XLM22_chunks.pkl"},
        "B": {"index": "XYZ12.index", "chunks": "XYZ12_chunks.pkl"}
    }
    
    missing_files = []
    for router, files in router_types.items():
        chunks_path = os.path.join(BASE_INDEX_DIR, files["chunks"])
        if not os.path.exists(chunks_path):
            missing_files.append(f"Router {router}: {files['chunks']}")
    
    if missing_files:
        print("ADVERTENCIA: No se encontraron los siguientes archivos de chunks:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nEs necesario regenerar los índices FAISS ejecutando:")
        print("  python ingest/ingest-model.py")
        print("\nEsto es necesario debido a cambios en el formato de los índices.")
        return False
    return True

# ==== FUNCIONES ====
def search_faiss(query, index_file, chunks_file, k=5):
    """Busca en el índice FAISS los documentos más relevantes."""
    try:
        # Cargar embeddings model
        embedder = SentenceTransformer(EMBED_MODEL)

        # Cargar índice FAISS
        index_path = os.path.join(BASE_INDEX_DIR, index_file)
        index = faiss.read_index(index_path)

        # Cargar chunks guardados
        import pickle
        chunks_path = os.path.join(BASE_INDEX_DIR, chunks_file)
        with open(chunks_path, 'rb') as f:
            chunks = pickle.load(f)

        # Generar embedding de la consulta y normalizarlo
        query_vec = embedder.encode([query])
        query_vec = query_vec.astype("float32")  # Asegurar que sea float32 para FAISS
        
        # Normalizar el vector para similitud de coseno (compatible con IndexFlatIP)
        faiss.normalize_L2(query_vec)

        # Buscar los k documentos más relevantes
        distances, indices = index.search(query_vec, k=k)
        
        # Validar resultados y combinar contexto
        context_parts = []
        for i in range(min(k, len(indices[0]))):
            idx = indices[0][i]
            # Verificar que el índice sea válido
            if idx >= 0 and idx < len(chunks):
                # Añadir información de relevancia
                score = float(distances[0][i])
                context_parts.append(f"[Relevancia: {score:.2f}]\n{chunks[idx]}")
        
        # Si no se encontraron resultados, devolver mensaje
        if not context_parts:
            return "No se encontró información relevante."
            
        # Combinar los resultados en un solo contexto
        return "\n\n---\n\n".join(context_parts)
    except Exception as e:
        print(f"Error en la búsqueda: {e}")
        return f"Error al buscar información: {str(e)}"

def load_tiny_llama():
    print("Cargando TinyLlama...")
    tokenizer = AutoTokenizer.from_pretrained(TINY_LLAMA_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        TINY_LLAMA_PATH,
        torch_dtype=torch.float16
    )
    model.to("cpu")
    return tokenizer, model


def generate_response(tokenizer, model, context, question, max_tokens=150, temperature=0.3):
    """Genera una respuesta usando el modelo."""
    prompt = f"""
# Instrucción
Eres un asistente experto en routers. Tu tarea es responder preguntas técnicas sobre configuración e instalación de routers.

# Contexto
A continuación tienes fragmentos de documentación técnica ordenados por relevancia:

{context}

# Reglas importantes
1. Usa ÚNICAMENTE la información del contexto proporcionado.
2. Si la información no está en el contexto, responde "No tengo suficiente información para responder esa pregunta."
3. No inventes información que no esté en el contexto.
4. Proporciona respuestas precisas y concisas.
5. Si hay instrucciones paso a paso en el contexto, preséntalas de forma clara y numerada.

# Pregunta
{question}

# Respuesta
"""

    try:
        inputs = tokenizer(prompt, return_tensors="pt").to("cpu")
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=(temperature > 0),
            top_p=0.9,
            repetition_penalty=1.2
        )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        print(f"Error en la generación: {e}")
        return f"Lo siento, hubo un error al generar la respuesta: {str(e)}"


# ==== MAIN ====
if __name__ == "__main__":
    # Verificar si es necesario regenerar índices
    indices_ok = check_chunks_files()
    if not indices_ok:
        response = input("\n¿Desea continuar de todos modos? (s/n): ").strip().lower()
        if response != 's':
            print("Ejecute primero 'python ingest/ingest-model.py' y luego vuelva a intentarlo.")
            exit()
    
    # Preguntar tipo de router
    router_type = input("¿Qué router tienes? (A/B): ").strip().upper()

    if router_type == "A":
        index_file = "XLM22.index"
        chunks_file = "XLM22_chunks.pkl"
    elif router_type == "B":
        index_file = "XYZ12.index"
        chunks_file = "XYZ12_chunks.pkl"
    else:
        print("Opción no válida.")
        exit()
    
    # Verificar si existe el archivo de chunks específico
    chunks_path = os.path.join(BASE_INDEX_DIR, chunks_file)
    if not os.path.exists(chunks_path):
        print(f"ADVERTENCIA: No se encontró el archivo {chunks_file}.")
        print("Es posible que necesite regenerar los índices ejecutando 'python ingest/ingest-model.py'")
        response = input("¿Desea continuar de todos modos? (s/n): ").strip().lower()
        if response != 's':
            exit()

    # Preguntar consulta
    question = input("Escribe tu pregunta: ")
    
    # Configurar parámetros de búsqueda y generación
    k_results = 5 
    
    # Permitir al usuario ajustar la longitud de la respuesta
    try:
        max_tokens = int(input("Longitud máxima de respuesta (50-500 tokens, Enter para usar 150): ") or "150")
        max_tokens = max(50, min(500, max_tokens))
    except ValueError:
        print("Valor no válido, usando 150 tokens.")
        max_tokens = 150
    
    # Buscar contexto en FAISS
    print("Buscando información relevante...")
    context = search_faiss(question, index_file, chunks_file, k=k_results)
    
    # Cargar modelo
    tokenizer, model = load_tiny_llama()

    # Generar respuesta
    print("Generando respuesta...")
    answer = generate_response(tokenizer, model, context, question, max_tokens=max_tokens, temperature=0.3)

    print("\n=== RESPUESTA DEL MODELO ===")
    print(answer)
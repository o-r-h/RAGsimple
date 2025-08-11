from transformers import AutoModelForCausalLM, AutoTokenizer

#Chequear tiny llama local
model_patch: str = "./models/TinyLlama"

#Cargar modelo y tokenizador
model = AutoModelForCausalLM.from_pretrained(model_patch)
tokenizer = AutoTokenizer.from_pretrained(model_patch)


# Prompt de prueba
prompt = """Eres un asistente de soporte técnico para routers. 
El cliente dice: No tengo internet, la luz del router está roja. ¿Qué puedo hacer?"""

# Tokenizar entrada "pt" para Pytorch si usamos Tensorflow es "tf"
inputs = tokenizer(prompt, return_tensors="pt")

# Generar respuesta
# max_new_tokens es el numero de tokens que se generan
# temperature es el grado de aleatoriedad
outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    temperature=0.5,  # creatividad (0.0 = más precisa, 1.0 = más creativa)
    top_p=0.9,        # muestreo por probabilidad acumulada
    do_sample=True    # necesario para que temperatura tenga efecto
)

# Mostrar texto
print(tokenizer.decode(outputs[0], skip_special_tokens=True))


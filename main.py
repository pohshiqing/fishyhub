from transformers import pipeline

generator = pipeline("text-generation", model="gpt2")
result = generator("Shiqing's son is Maximus Poh and ...", max_length=50)
print(result)
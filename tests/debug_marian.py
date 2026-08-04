from transformers import MarianMTModel, MarianTokenizer

MODEL_PATH = r"E:\Bhasha-Mitra\models\translation\OPUS-MT"

tokenizer = MarianTokenizer.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)

model = MarianMTModel.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)

texts = [
    "Hello",
    "Good morning",
    "Thank you",
    "How are you?",
    "Welcome to India",
]

for text in texts:

    print("=" * 60)
    print("Input :", text)

    encoded = tokenizer(text, return_tensors="pt")

    generated = model.generate(**encoded)

    output = tokenizer.decode(
        generated[0],
        skip_special_tokens=True
    )

    print("Output:", output)
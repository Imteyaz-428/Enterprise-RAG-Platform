
from sentence_transformers import CrossEncoder

model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    device="mps",
)

query = "What is static code analysis?"

passages = [
    "Static code analysis examines source code without executing it.",
    "A database stores structured information.",
    "Static analysis can detect security vulnerabilities and code quality issues.",
]

pairs = [(query, passage) for passage in passages]

scores = model.predict(pairs)

ranked = sorted(
    zip(passages, scores),
    key=lambda item: item[1],
    reverse=True,
)

for passage, score in ranked:
    print(f"Score: {float(score):.4f}")
    print(passage)
    print("-" * 50)

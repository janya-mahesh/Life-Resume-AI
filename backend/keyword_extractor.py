from keybert import KeyBERT

# Load model once
kw_model = KeyBERT(model="all-MiniLM-L6-v2")

def extract_keywords(text):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 3), stop_words="english", top_n=5)
    return [kw for kw, _ in keywords]

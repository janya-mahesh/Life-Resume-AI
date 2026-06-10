# keyword_extractor.py — Lightweight keyword extraction (no heavy ML models)
# Uses TF-IDF from sklearn instead of KeyBERT/sentence-transformers
# RAM usage: ~5MB vs ~400MB+ for the old KeyBERT approach

import re

# Common English stop words
STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her",
    "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs",
    "themselves", "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "at", "by", "for", "with",
    "about", "against", "between", "through", "during", "before", "after", "above",
    "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s",
    "t", "can", "will", "just", "don", "should", "now", "d", "ll", "m", "o", "re",
    "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn", "haven",
    "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren",
    "won", "wouldn", "also", "get", "got", "like", "want", "know", "think", "make",
    "go", "going", "would", "could", "really", "im", "ive", "dont", "cant", "lot",
    "much", "many", "well", "still", "thing", "things", "something", "anything",
    "everything", "nothing", "always", "never", "sometimes", "often", "usually",
    "sure", "even", "take", "come", "put", "give", "keep", "let", "begin", "seem",
    "help", "show", "hear", "play", "run", "move", "live", "believe", "bring",
    "happen", "write", "provide", "sit", "stand", "try", "ask", "work", "call",
}

# Domain-relevant boosted terms for better extraction
DOMAIN_BOOST = {
    "ai", "machine", "learning", "python", "data", "science", "design", "art",
    "coding", "programming", "robotics", "engineering", "research", "writing",
    "music", "photography", "psychology", "counseling", "business", "startup",
    "finance", "marketing", "healthcare", "biology", "chemistry", "physics",
    "mathematics", "education", "teaching", "sports", "fitness", "cooking",
    "gaming", "animation", "filmmaking", "architecture", "sustainability",
    "environment", "law", "medicine", "journalism", "technology", "software",
    "hardware", "networking", "cybersecurity", "blockchain", "web", "mobile",
    "cloud", "devops", "analytics", "statistics", "modeling", "visualization",
    "creative", "innovation", "entrepreneurship", "leadership", "communication",
    "guitar", "piano", "singing", "dancing", "painting", "drawing", "reading",
    "volunteering", "mentoring", "public", "speaking", "debate", "chess",
}


def extract_keywords(text, top_n=5):
    """
    Extract keywords from text using simple frequency + relevance scoring.
    Lightweight alternative to KeyBERT — uses ~5MB RAM instead of ~400MB.
    """
    if not text or not isinstance(text, str):
        return []

    # Normalize text
    text = text.lower().strip()
    
    # Tokenize: extract words and bigrams
    words = re.findall(r'[a-z]+', text)
    
    # Filter stop words and very short words
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    
    if not meaningful:
        return []
    
    # Score words: frequency + domain relevance boost
    word_scores = {}
    for word in meaningful:
        word_scores[word] = word_scores.get(word, 0) + 1
        if word in DOMAIN_BOOST:
            word_scores[word] += 2  # Boost domain-relevant terms
    
    # Extract bigrams for multi-word keywords
    bigram_scores = {}
    for i in range(len(meaningful) - 1):
        bigram = f"{meaningful[i]} {meaningful[i+1]}"
        bigram_scores[bigram] = bigram_scores.get(bigram, 0) + 1.5
        # Boost if either word is domain-relevant
        if meaningful[i] in DOMAIN_BOOST or meaningful[i+1] in DOMAIN_BOOST:
            bigram_scores[bigram] += 2
    
    # Combine and sort
    all_scores = {**word_scores, **bigram_scores}
    sorted_keywords = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Deduplicate: remove single words if they appear in a selected bigram
    selected = []
    selected_words = set()
    for keyword, score in sorted_keywords:
        if len(selected) >= top_n:
            break
        # Skip single words that are part of already-selected bigrams
        parts = keyword.split()
        if len(parts) == 1 and keyword in selected_words:
            continue
        selected.append(keyword)
        for part in parts:
            selected_words.add(part)
    
    return selected

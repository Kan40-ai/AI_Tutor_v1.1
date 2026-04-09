import re
import spacy
from nltk.corpus import stopwords

# Load spaCy model once at module level (shared across all calls)
nlp = spacy.load("en_core_web_sm")

def preprocess_query(raw_query: str) -> str:
    """
    EXACT preprocessing match for corpus pipeline:
    spaCy → lemma → custom stopwords → regex clean
    """
    # NLTK stopwords with custom exclusions (negations preserved)
    # stop_words = set(stopwords.words('english'))
    # exclude_wordslist = ['no', 'not', 'never', 'can', "wouldn't", "mustn't", 
    #                     "weren't", "shouldn't", "didn't", "don't", 'could', 
    #                     'may', 'might', 'before', 'after', 'during']
    # custom_wordlist = [word for word in stop_words if word not in exclude_wordslist]
    
    # spaCy processing
    # doc = nlp(raw_query.lower())
    # processed_tokens = []
    
    # for token in doc:
    #     # Skip custom stopwords only
    #     # if token.text in custom_wordlist:
    #     #     continue
        
    #     # Skip punctuation/spaces
    #     if token.is_punct or token.is_space:
    #         continue
        
    #     # Lemma + clean
    #     lemma = token.lemma_
    #     cleaned_lemma = re.sub('[^a-zA-Z0-9]', '', lemma)
        
    #     if cleaned_lemma:
    #         processed_tokens.append(cleaned_lemma)
    
    # cleaned_query = ' '.join(processed_tokens)

    # Minimal preprocessing for dense vector embeddings.
    # Only cleans up messy whitespace while preserving natural grammar.
    # Remove leading/trailing whitespace
    cleaned_query = raw_query.strip()
    
    # Replace multiple spaces or newlines with a single space
    cleaned_query = re.sub(r'\s+', ' ', cleaned_query)
    return cleaned_query

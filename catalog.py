import os
import json
import math
import re

# Resolve catalog.json relative to the directory of this file
_current_dir = os.path.dirname(os.path.abspath(__file__))
_catalog_path = os.path.join(_current_dir, "catalog.json")

# 1. Load catalog.json at startup into CATALOG
CATALOG = []
try:
    if os.path.exists(_catalog_path):
        with open(_catalog_path, "r", encoding="utf-8") as _f:
            CATALOG = json.load(_f)
    else:
        # Fallback to local working directory if relative path lookup fails
        with open("catalog.json", "r", encoding="utf-8") as _f:
            CATALOG = json.load(_f)
except Exception:
    CATALOG = []

# 2. Advanced TF-IDF BM25 Search function
def search(query: str, top_k: int = 15) -> list[dict]:
    """
    Retrieves the top_k catalog items using a lightweight TF-IDF BM25-like ranker.
    Boosts matches in assessment names by giving them double frequency weight.
    """
    def tokenize(text: str) -> list[str]:
        # Split on non-alphanumeric characters, ignoring empty terms
        return [w.strip() for w in re.split(r"[^\w\+]+", text.lower()) if w.strip()]

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    N = len(CATALOG)
    if N == 0:
        return []

    # Precompute tokens and document frequencies (DF) for matching tokens
    DF = {}
    doc_tokens_list = []
    
    for item in CATALOG:
        name = item.get("name", "") or ""
        desc = item.get("description", "") or ""
        # Boost name matches by doubling name tokens frequency
        tokens = tokenize(name) * 2 + tokenize(desc)
        doc_tokens_list.append(tokens)
        
        unique_tokens = set(tokens)
        for token in unique_tokens:
            DF[token] = DF.get(token, 0) + 1

    # Compute IDF with smoothing
    IDF = {}
    for token in query_tokens:
        df = DF.get(token, 0)
        IDF[token] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

    # Score documents
    scored_results = []
    avg_doc_len = sum(len(d) for d in doc_tokens_list) / N if N > 0 else 1.0
    
    for idx, item in enumerate(CATALOG):
        tokens = doc_tokens_list[idx]
        if not tokens:
            continue
        
        doc_len = len(tokens)
        score = 0.0
        for token in query_tokens:
            tf = tokens.count(token)
            if tf > 0:
                # BM25-style scoring: tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))
                k1 = 1.5
                b = 0.75
                term_score = IDF[token] * tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))
                score += term_score
                
        if score > 0.0:
            scored_results.append((score, item))

    # Sort items by relevance score descending
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    return [item for _, item in scored_results[:top_k]]


# 3. Get by names function
def get_by_names(names: list[str]) -> list[dict]:
    """
    For each name in the list, find matching item in CATALOG by name (case insensitive).
    Return list of matched catalog items.
    Skip names not found, do not crash.
    """
    matched = []
    for name in names:
        if not name:
            continue
        name_lower = name.lower().strip()
        for item in CATALOG:
            item_name = item.get("name", "") or ""
            if item_name.lower().strip() == name_lower:
                matched.append(item)
                break
    return matched

# 4. Get all function
def get_all() -> list[dict]:
    """
    Returns full CATALOG list.
    """
    return CATALOG

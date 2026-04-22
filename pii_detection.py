import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
import re

# Initialize Presidio Analyzer
analyzer = AnalyzerEngine()

# Custom regex for Financial Data / NDA patterns (to classify as CONFIDENTIAL)
nda_pattern = Pattern(name="nda_pattern", regex=r"(?i)\b(NDA|Non-Disclosure Agreement)\b", score=0.8)
nda_recognizer = PatternRecognizer(supported_entity="NDA_TERM", patterns=[nda_pattern])
analyzer.registry.add_recognizer(nda_recognizer)

financial_pattern = Pattern(name="financial_keyword", regex=r"(?i)\b(revenue|profit|loss|salary|bonus|balance)\b\s*\$?\d+", score=0.5)
financial_recognizer = PatternRecognizer(supported_entity="FINANCIAL_DATA", patterns=[financial_pattern])
analyzer.registry.add_recognizer(financial_recognizer)

# Health & System Patterns
health_pattern = Pattern(name="health_id", regex=r"(?i)(Patient\s*ID|Biometric\s*Identifier|Health\s*Record\s*Attachments|Hospital_ID|Doctor_ID|D\*{3}r_ID):\s*([0-9a-zA-Z*\-]+)", score=0.85)
health_recognizer = PatternRecognizer(supported_entity="HEALTH_SYSTEM_ID", patterns=[health_pattern])
analyzer.registry.add_recognizer(health_recognizer)

system_pattern = Pattern(name="sys_id", regex=r"(?i)(Record_Version|Access_Level|System_Log_ID):\s*([0-9a-zA-Z*\-]+)", score=0.85)
system_recognizer = PatternRecognizer(supported_entity="SYSTEM_DATA", patterns=[system_pattern])
analyzer.registry.add_recognizer(system_recognizer)

age_pattern = Pattern(name="age_val", regex=r"(?i)Age:\s*([0-9*]+)", score=0.85)
age_recognizer = PatternRecognizer(supported_entity="AGE_DATA", patterns=[age_pattern])
analyzer.registry.add_recognizer(age_recognizer)

# Custom Email Recognizer to handle noisy OCR spaces
email_pattern = Pattern(name="noisy_email", regex=r"(?i)\S+@\s*[a-z0-9.-]+\.[a-z]{2,}", score=0.9)
email_recognizer = PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[email_pattern])
analyzer.registry.add_recognizer(email_recognizer)

# Custom Phone Recognizer to bypass UK_NHS overlap
phone_pattern = Pattern(name="noisy_phone", regex=r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b", score=0.9)
phone_recognizer = PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[phone_pattern])
analyzer.registry.add_recognizer(phone_recognizer)

# Custom Credit Card Recognizer to bypass strict Luhn checks on fake/noisy data
cc_pattern = Pattern(name="noisy_cc", regex=r"\b(?:\d{4}[-\s]?){3}\d{4}\b", score=0.9)
cc_recognizer = PatternRecognizer(supported_entity="CREDIT_CARD", patterns=[cc_pattern])
analyzer.registry.add_recognizer(cc_recognizer)

def determine_sensitivity(entity_type: str) -> str:
    """Map detected entity type to DB sensitivity tier."""
    personal_entities = ["PERSON", "DATE_TIME", "TIMESTAMP", "PHONE_NUMBER", "EMAIL_ADDRESS", "AGE_DATA"]
    confidential_entities = [
        "US_SSN", "UK_NHS", "CREDIT_CARD", "IBAN_CODE", "US_BANK_NUMBER", 
        "ORGANIZATION", "NDA_TERM", "FINANCIAL_DATA", "HEALTH_SYSTEM_ID", 
        "SYSTEM_DATA", "US_DRIVER_LICENSE", "MEDICAL_LICENSE"
    ]
    
    if entity_type in personal_entities:
        return "PERSONAL"
    elif entity_type in confidential_entities:
        return "CONFIDENTIAL"
    else:
        # Default fallback
        return "NON_SENSITIVE"

# List of known common terms (tech, academics, corporate jargon)
JARGON_WORDS = {
    "ai", "ml", "streamlit", "jupyter", "scikit", "tensorflow", "keras", 
    "pandas", "numpy", "python", "java", "sql", "react", "node", "aws", 
    "azure", "gcp", "semester", "cgpa", "gpa", "b.tech", "m.tech", "b.sc", 
    "m.sc", "b.e", "m.e", "phd", "developer", "intern", "engineer", "framework",
    "scikit-learn", "matplotlib", "mysql", "github", "linkedin", "html", "css",
    "nit", "iit", "srm", "vit", "trichy", "chennai", "coimbatore",
    "personnel", "personnei", "emergency", "incident", "thai", "catholic",
    "smartsummary", "summarizer", "quicksum", "autosummarize", "pro"
}

def analyze_text(text: str):
    # Utilize a slightly stricter score threshold to filter out weak inferences
    results = analyzer.analyze(text=text, entities=[], language='en', score_threshold=0.55)
    
    entities_found = []
    seen = set()
    
    for result in results:
        entity_text = text[result.start:result.end]
        
        if entity_text not in seen:
            seen.add(entity_text)
            
            text_clean = entity_text.strip().lower()
            words_in_text = set(re.findall(r'\b\w+\b', text_clean))
            
            # Reclassify domains/tech jargon as Non-Sensitive instead of filtering them out
            if words_in_text & JARGON_WORDS:
                sensitivity = "NON_SENSITIVE"
            elif result.entity_type in ["DATE_TIME", "TIMESTAMP"] and any(k in text_clean for k in ["semester", "yesterday", "today", "tomorrow"]):
                sensitivity = "NON_SENSITIVE"
            elif result.entity_type == "PERSON" and len(text_clean) > 30:
                # Catch Spacy incorrectly grouping massive sequences of words into a single PERSON name
                sensitivity = "NON_SENSITIVE"
            elif len(text_clean) <= 2:
                sensitivity = "NON_SENSITIVE"
            else:
                sensitivity = determine_sensitivity(result.entity_type)
                
            entities_found.append({
                "entity_text": entity_text,
                "entity_type": result.entity_type,
                "sensitivity": sensitivity
            })
            
    return entities_found

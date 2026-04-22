import os
import hashlib
from cryptography.fernet import Fernet
from env_setup import load_environment

# Ensure environment is loaded and we have our master key
load_environment()
MASTER_KEY = os.getenv("MASTER_KEY")
fernet = Fernet(MASTER_KEY.encode()) if MASTER_KEY else None

def update_master_key(new_key: str):
    """Dynamically rotate the active fernet instance in memory."""
    global fernet
    fernet = Fernet(new_key.encode())

def encrypt_text(text: str) -> str:
    """Encrypts text using AES (Fernet)."""
    if not fernet:
        raise ValueError("Fernet key not initialized. Check MASTER_KEY.")
    return fernet.encrypt(text.encode()).decode()

def decrypt_text(cipher_text: str) -> str:
    """Decrypts text using AES (Fernet)."""
    if not fernet:
        raise ValueError("Fernet key not initialized. Check MASTER_KEY.")
    return fernet.decrypt(cipher_text.encode()).decode()

def mask_text(text: str) -> str:
    """Masks a string, exposing only first and last character. (e.g., 'Jason' -> 'J***n')"""
    # For custom keys like "Patient ID: 123", we want to mask just the value if possible.
    if ":" in text:
        key, val = text.split(":", 1)
        val = val.strip()
        if len(val) <= 2:
            masked_val = "*" * len(val)
        else:
            masked_val = val[0] + "*" * (len(val) - 2) + val[-1]
        return f"{key}: {masked_val}"
        
    if len(text) <= 2:
        return "*" * len(text)
    
    return text[0] + "*" * (len(text) - 2) + text[-1]

def tokenize_text(token_id: int) -> str:
    """Replaces text with a formal token structure."""
    return f"[TOKEN_{token_id}]"

def hash_text(text: str) -> str:
    """Produces SHA-256 hash for exact match lookup without revealing data."""
    return hashlib.sha256(text.encode()).hexdigest()

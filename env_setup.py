import os
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet

ENV_FILE = ".env"

def generate_master_key():
    """Generates a new Fernet key and saves it to .env if missing."""
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f:
            pass # Create empty .env file
            
    load_dotenv(ENV_FILE)
    
    master_key = os.getenv("MASTER_KEY")
    if not master_key:
        print("MASTER_KEY not found. Generating a new one...")
        master_key = Fernet.generate_key().decode()
        set_key(ENV_FILE, "MASTER_KEY", master_key)
        
    return master_key

def load_environment():
    """Loads all environment variables, auto-generating MASTER_KEY if missing."""
    generate_master_key()
    load_dotenv(ENV_FILE)
    
    # Ensuring required keys exist
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY is not set in .env")
        
    if not os.getenv("OPENAI_MODEL"):
        # Defaulting if not set
        set_key(ENV_FILE, "OPENAI_MODEL", "gpt-3.5-turbo")
        load_dotenv(ENV_FILE)

if __name__ == "__main__":
    load_environment()
    print("Environment setup complete.")

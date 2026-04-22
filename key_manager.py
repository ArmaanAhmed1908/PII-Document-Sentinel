import os
import json
import threading
import time
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from dotenv import set_key
from env_setup import ENV_FILE
import encryption

LOG_FILE = "key_rotation_log.json"
ROTATION_INTERVAL = 300  # 5 minutes in seconds

class KeyManager:
    def __init__(self):
        # Pre-generate the next key that will rotate in the upcoming cycle
        self.next_key = Fernet.generate_key().decode()
        self.timer = None

    def rotate_key(self):
        try:
            current_time = datetime.now()
            
            # The pre-generated 'next_key' becomes the active 'current_key'
            new_current_key = self.next_key
            
            # Update encryption module inside fastapi memory
            encryption.update_master_key(new_current_key)
            
            # Persist it into the .env file
            set_key(ENV_FILE, "MASTER_KEY", new_current_key)
            
            # Generate the new 'next' key
            self.next_key = Fernet.generate_key().decode()
            
            next_rotation_time = current_time + timedelta(seconds=ROTATION_INTERVAL)
            
            # Dump JSON Log
            log_data = {
                "status": "Rotated",
                "current_rotation_timestamp": current_time.isoformat(),
                "current_update_timestamp": current_time.isoformat(),
                "next_key_to_be_generated": self.next_key,
                "next_rotation_scheduled_for": next_rotation_time.isoformat()
            }
            
            with open(LOG_FILE, "w") as f:
                json.dump(log_data, f, indent=4)
                
            print(f"\n[KEY MANAGER] ✅ Master Key Rotated successfully at {current_time.strftime('%H:%M:%S')}. Next rotation in 5 minutes.")
        except Exception as e:
            print(f"\n[KEY MANAGER] ❌ Key rotation failed: {e}")
        finally:
            self.schedule_next()

    def schedule_next(self):
        self.timer = threading.Timer(ROTATION_INTERVAL, self.rotate_key)
        self.timer.daemon = True
        self.timer.start()

    def start(self):
        print(f"[KEY MANAGER] Starting {ROTATION_INTERVAL//60}-Minute Master Key Rotation Scheduler...")
        # Optionally perform an immediate run to populate the JSON directly on startup
        self.rotate_key()

key_manager_service = KeyManager()

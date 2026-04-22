import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import openai
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
import threading

import database
import pii_detection
import encryption
from document_sentinel_pipeline import process_pdf
from env_setup import load_environment
from key_manager import key_manager_service
import requests

# Load Env
load_environment()

# Start Dynamic Key Rotation Daemon
key_manager_service.start()

app = FastAPI(title="PII Document Protection API")

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    document_id: int
    question: str

class RequestAuthModel(BaseModel):
    document_id: int

auth_requests = {}

@app.post("/login")
def login(req: LoginRequest):
    role = database.authenticate_user(req.username, req.password)
    if role:
        user_id = database.get_user_id(req.username)
        return {"status": "success", "role": role, "user_id": user_id}
    else:
        return {"status": "error", "message": "INVALID CREDENTIALS"}


@app.post("/upload")
def upload_document(user_id: int = Form(...), file: UploadFile = File(...)):
    docs_dir = "uploaded_pdfs"
    os.makedirs(docs_dir, exist_ok=True)
    
    file_path = os.path.join(docs_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        raw_text = process_pdf(file_path)
        doc_id = database.save_document(user_id, file.filename, raw_text)
        found_entities = pii_detection.analyze_text(raw_text)
        
        token_counter = 1
        for entity in found_entities:
            text_val = entity["entity_text"]
            ent_type = entity["entity_type"]
            sens = entity["sensitivity"]
            
            enc_val = None
            if ent_type in ["PERSON", "DATE_TIME", "TIMESTAMP"]:
                enc_val = encryption.tokenize_text(token_counter)
                token_counter += 1
            elif ent_type in ["US_SSN", "UK_NHS", "PHONE_NUMBER", "EMAIL_ADDRESS"]:
                enc_val = encryption.encrypt_text(text_val)
            elif sens == "CONFIDENTIAL":
                enc_val = encryption.mask_text(text_val)
            else:
                enc_val = text_val
                
            database.save_pii_entity(doc_id, text_val, ent_type, sens, enc_val)
            
        return {"status": "success", "document_id": doc_id, "message": "Document processed and entities saved with advanced formatting."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{user_id}")
def user_documents(user_id: int):
    return {"documents": database.get_documents_by_user(user_id)}

@app.get("/documents")
def all_documents():
    return {"documents": database.get_all_documents()}

@app.get("/document/{document_id}")
def get_document_info(document_id: int):
    raw_text = database.get_document_text(document_id)
    entities = database.get_pii_entities(document_id)
    return {"raw_text": raw_text, "entities": entities}

@app.post("/chat")
def chat_with_document(req: ChatRequest):
    raw_text = database.get_document_text(req.document_id)
    if not raw_text:
        raise HTTPException(status_code=404, detail="Document not found")
        
    openai.api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL", "gptnano5")
    api_base = os.getenv("OPENAI_API_BASE")
    
    try:
        client = openai.OpenAI(
            api_key=openai.api_key,
            base_url=api_base if api_base else "https://api.openai.com/v1"
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant answering questions based on the provided document. Use the document text to answer the question."},
                {"role": "user", "content": f"Document Text:\n{raw_text}\n\nQuestion: {req.question}"}
            ]
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"Simulated LLM response for testing purposes. [OpenAI Error: {str(e)}]"

    entities = database.get_pii_entities(req.document_id)
    safe_answer = answer
    
    entities.sort(key=lambda x: len(x['entity_text']), reverse=True)
    
    for ent in entities:
        if ent['entity_text'] in safe_answer:
            if ent['sensitivity'] in ['PERSONAL', 'CONFIDENTIAL']:
                if ent['encrypted_value']:
                    safe_answer = safe_answer.replace(ent['entity_text'], ent['encrypted_value'])

    return {"answer": safe_answer, "original_answer": answer}

@app.post("/request_auth")
def request_auth(req: RequestAuthModel):
    auth_id = str(uuid.uuid4())
    auth_requests[auth_id] = "pending"
    
    yes_link = f"http://127.0.0.1:8000/auth_callback?auth_id={auth_id}&decision=yes"
    no_link = f"http://127.0.0.1:8000/auth_callback?auth_id={auth_id}&decision=no"
    
    emailjs_payload = {
        "service_id": "service_wq48jxi",
        "template_id": "template_dtd0ccp",
        "user_id": "QrVBO91mCe_yfhIlF",
        "template_params": {
            "to_email": "balaspt287@gmail.com",
            "doc_id": str(req.document_id),
            "yes_link": yes_link,
            "no_link": no_link
        }
    }
    
    try:
        resp = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send", 
            json=emailjs_payload,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://localhost:8000"
            }
        )
        if resp.status_code not in [200, 201]:
            auth_requests[auth_id] = "error"
            raise HTTPException(status_code=500, detail=f"EmailJS Error: {resp.text}")
    except Exception as e:
        auth_requests[auth_id] = "error"
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "auth_id": auth_id}

@app.get("/auth_callback", response_class=HTMLResponse)
def auth_callback(auth_id: str, decision: str):
    if auth_id in auth_requests:
        auth_requests[auth_id] = decision
        color = "green" if decision == "yes" else "red"
        return f"<html><body style='font-family: Arial; text-align:center; margin-top:50px;'><h1 style='color:{color}'>Response Recorded: {decision.upper()}</h1><p>You may now close this tab.</p></body></html>"
    return "<html><body><h1>Invalid Auth ID</h1></body></html>"

@app.get("/auth_status/{auth_id}")
def get_auth_status(auth_id: str):
    status = auth_requests.get(auth_id, "unknown")
    return {"auth_id": auth_id, "status": status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

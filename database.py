import mysql.connector
from mysql.connector import Error
import os

def get_db_connection():
    """Establish a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host='localhost',          # Change to your DB host if not localhost
            user='root',               # Change to your DB username
            password='keershaa',       # Change to your DB password
            database='pii_project'     # As requested
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def authenticate_user(username, password):
    """Authenticate user and return role if successful, else None."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT role FROM users WHERE username=%s AND password=%s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            return user['role']
    return None

def save_document(user_id, file_name, raw_text):
    """Save document metadata and raw text. Return document_id."""
    conn = get_db_connection()
    doc_id = None
    if conn:
        cursor = conn.cursor()
        query = "INSERT INTO documents (user_id, file_name, raw_text) VALUES (%s, %s, %s)"
        cursor.execute(query, (user_id, file_name, raw_text))
        conn.commit()
        doc_id = cursor.lastrowid
        cursor.close()
        conn.close()
    return doc_id

def save_pii_entity(document_id, entity_text, entity_type, sensitivity, encrypted_value):
    """Save a detected PII entity."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = '''
            INSERT INTO pii_entities 
            (document_id, entity_text, entity_type, sensitivity, encrypted_value) 
            VALUES (%s, %s, %s, %s, %s)
        '''
        cursor.execute(query, (document_id, entity_text, entity_type, sensitivity, encrypted_value))
        conn.commit()
        cursor.close()
        conn.close()

def get_documents_by_user(user_id):
    """Fetch all documents for a specific user."""
    conn = get_db_connection()
    docs = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, file_name FROM documents WHERE user_id=%s"
        cursor.execute(query, (user_id,))
        docs = cursor.fetchall()
        cursor.close()
        conn.close()
    return docs

def get_all_documents():
    """Fetch all documents (for third party)."""
    conn = get_db_connection()
    docs = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, file_name FROM documents"
        cursor.execute(query)
        docs = cursor.fetchall()
        cursor.close()
        conn.close()
    return docs

def get_document_text(document_id):
    """Fetch raw text of a document."""
    conn = get_db_connection()
    text = ""
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT raw_text FROM documents WHERE id=%s"
        cursor.execute(query, (document_id,))
        doc = cursor.fetchone()
        cursor.close()
        conn.close()
        if doc:
            text = doc['raw_text']
    return text

def get_pii_entities(document_id):
    """Fetch PII entities for a document."""
    conn = get_db_connection()
    entities = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT entity_text, entity_type, sensitivity, encrypted_value FROM pii_entities WHERE document_id=%s"
        cursor.execute(query, (document_id,))
        entities = cursor.fetchall()
        cursor.close()
        conn.close()
    return entities

def get_user_id(username):
    """Helper method to get user_id from username."""
    conn = get_db_connection()
    user_id = None
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id FROM users WHERE username=%s"
        cursor.execute(query, (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        if user_data:
            user_id = user_data['id']
    return user_id

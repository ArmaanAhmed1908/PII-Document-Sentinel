import streamlit as st
import requests
import os
import pandas as pd
from metrics_engine import generate_performance_metrics
import concurrent.futures
import json
from fpdf import FPDF

API_URL = "http://127.0.0.1:8000"

import textwrap

def generate_pdf_report(entities, mode="encrypted"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.cell(200, 10, "Sentinelled PII Extraction Report", 0, 1, 'C')
    pdf.set_font("helvetica", size=10)
    pdf.ln(10)
    
    for entity in entities:
        if mode == "decrypted":
            line = f"[{entity['sensitivity']}] {entity['entity_type']}: {entity['entity_text']}"
        else:
            val = entity.get('encrypted_value') or "***"
            line = f"[{entity['sensitivity']}] {entity['entity_type']} -> Encrypted: {val}"
        
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        wrapped_line = "\n".join(textwrap.wrap(safe_line, width=90))
        pdf.multi_cell(0, 7, wrapped_line)

    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode('latin-1')
    return bytes(output)

def create_download_buttons(doc_data, document_id, mode="encrypted"):
    st.markdown("---")
    st.subheader("📥 Export Data")
    
    entities = doc_data.get('entities', [])
    
    export_entities = []
    for e in entities:
        if mode == "decrypted":
            export_entities.append({
                "Sensitivity": e['sensitivity'],
                "Entity_Type": e['entity_type'],
                "Original_Text": e['entity_text']
            })
        else:
            export_entities.append({
                "Sensitivity": e['sensitivity'],
                "Entity_Type": e['entity_type'],
                "Encrypted_Token": e.get('encrypted_value') or "***"
            })
            
    json_data = json.dumps(export_entities, indent=2)
    df = pd.DataFrame(export_entities)
    csv_data = df.to_csv(index=False).encode('utf-8') if not df.empty else b""
    pdf_data = generate_pdf_report(entities, mode=mode)
    
    file_prefix = "decrypted_data" if mode == "decrypted" else "encrypted_data"
    label_prefix = "Decrypted" if mode == "decrypted" else "Encrypted"
    
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    with dl_col1:
        st.download_button(label=f"Download {label_prefix} JSON", data=json_data, file_name=f"{file_prefix}_{document_id}.json", mime="application/json", key=f"dl_json_{document_id}_{mode}")
    with dl_col2:
        st.download_button(label=f"Download {label_prefix} CSV", data=csv_data, file_name=f"{file_prefix}_{document_id}.csv", mime="text/csv", key=f"dl_csv_{document_id}_{mode}")
    with dl_col3:
        st.download_button(label=f"Download {label_prefix} PDF", data=pdf_data, file_name=f"{file_prefix}_{document_id}.pdf", mime="application/pdf", key=f"dl_pdf_{document_id}_{mode}")

st.set_page_config(page_title="PII Document Sentinel", layout="wide")

def login():
    st.title("Login to PII Sentinel")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            resp = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
            data = resp.json()
            if data.get("status") == "success":
                st.session_state["role"] = data["role"]
                st.session_state["username"] = username
                st.session_state["user_id"] = data["user_id"]
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid Credentials. Please try again.")

def display_doc_results(document_id):
    # Retrieve the specific uploaded document's encryption details
    doc_resp = requests.get(f"{API_URL}/document/{document_id}")
    if doc_resp.status_code == 200:
        doc_data = doc_resp.json()
        st.subheader("Extracted Text")
        st.text_area("Raw Text", doc_data['raw_text'], height=200, key=f"text_up_{document_id}")
        
        st.subheader("PII Entities")
        entities = doc_data['entities']
        personal = [e for e in entities if e['sensitivity'] == "PERSONAL"]
        confidential = [e for e in entities if e['sensitivity'] == "CONFIDENTIAL"]
        non_sensitive = [e for e in entities if e['sensitivity'] == "NON_SENSITIVE"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 🟢 Personal")
            for p in personal:
                obfuscated = p['encrypted_value'] if len(p['encrypted_value']) < 60 else p['encrypted_value'][:15] + "..."
                st.write(f"- {p['entity_text']} ({p['entity_type']}) → `{obfuscated}`")
        with col2:
            st.markdown("### 🔴 Confidential")
            for c in confidential:
                obfuscated = c['encrypted_value'] if len(c['encrypted_value']) < 60 else c['encrypted_value'][:15] + "..."
                st.write(f"- {c['entity_text']} ({c['entity_type']}) → `{obfuscated}`")
        with col3:
            st.markdown("### ⚪ Non-Sensitive")
            for ns in non_sensitive:
                st.write(f"- {ns['entity_text']} ({ns['entity_type']})")
        
        st.markdown("---")
        st.subheader("🛡️ Risk Analyzer")
        if len(confidential) > 0:
            st.error("🚨 **HIGHLY CRITICAL:** This document contains highly sensitive confidential data and presents a significant data exposure risk.")
        elif len(personal) > 0:
            st.warning("⚠️ **MODERATE RISK:** This document contains personal identifying data. Handle with controlled access.")
        else:
            st.success("✅ **LOW RISK:** No critical or personal sensitive data detected. Document is safe for general handling.")
            
        create_download_buttons(doc_data, document_id, mode="encrypted")
    
    st.markdown("---")
    st.subheader("📊 Document Processing Performance")
    st.write("Real-time statistical validation of the NLP Classifiers against this document's extraction set:")
    
    metrics_df = generate_performance_metrics()
    
    st.write("**Tabulated Classifier Accuracies**")
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    st.write("**Visualized Performance Thresholds**")
    chart_df = metrics_df[["Category", "Precision", "Recall", "F1-Score"]].set_index("Category")
    st.bar_chart(chart_df)
    st.markdown("---")

def process_and_display_doc(uploaded_file):
    with st.spinner(f"Processing document {uploaded_file.name} (OCR & PII Detection)..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        data = {"user_id": st.session_state["user_id"]}
        resp = requests.post(f"{API_URL}/upload", files=files, data=data)
        
        if resp.status_code == 200:
            res_data = resp.json()
            st.success(res_data["message"])
            display_doc_results(res_data['document_id'])
        else:
            st.error(f"Error processing: {resp.text}")

def user_dashboard():
    st.title(f"User Dashboard - Welcome {st.session_state['username']}")
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.header("Upload Document(s)")
    upload_mode = st.radio("Select Upload Mode", ["Single File", "Multiple Files (Folder)"])
    
    if upload_mode == "Single File":
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
        if uploaded_file is not None:
            if st.button("Process PDF"):
                process_and_display_doc(uploaded_file)
    else:
        uploaded_files = st.file_uploader("Choose multiple PDF files", type=["pdf"], accept_multiple_files=True)
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} file(s) selected.**")
            
            if st.button("Process all files inside the folder"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                processed_docs = []
                
                user_id = st.session_state["user_id"]
                file_data = [(f.name, f.getvalue()) for f in uploaded_files]

                def process_file_req(name, content, uid):
                    files_payload = {"file": (name, content, "application/pdf")}
                    data = {"user_id": uid}
                    try:
                        resp = requests.post(f"{API_URL}/upload", files=files_payload, data=data)
                        if resp.status_code == 200:
                            return {"name": name, "id": resp.json()['document_id']}
                    except Exception as e:
                        pass
                    return None

                status_text.text("Processing files in parallel (up to 10 at a time)...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(process_file_req, name, content, user_id): name for name, content in file_data}
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        result = future.result()
                        if result:
                            processed_docs.append(result)
                        progress_bar.progress((i + 1) / len(uploaded_files))
                        status_text.text(f"Processed {i+1}/{len(uploaded_files)} files...")
                
                status_text.text("✅ All files processed successfully!")
                st.session_state['processed_folder_docs'] = processed_docs
                
            if 'processed_folder_docs' in st.session_state and st.session_state['processed_folder_docs']:
                docs = st.session_state['processed_folder_docs']
                doc_options = {d["name"]: d["id"] for d in docs}
                selected_name = st.selectbox("Select a processed file to view its encryption result", [""] + list(doc_options.keys()))
                if selected_name:
                    display_doc_results(doc_options[selected_name])

    st.header("Your Previously Uploaded Documents")
    resp = requests.get(f"{API_URL}/documents/{st.session_state['user_id']}")
    if resp.status_code == 200:
        documents = resp.json().get("documents", [])
        if not documents:
            st.info("No documents uploaded yet.")
        for doc in documents:
            with st.expander(f"📄 {doc['file_name']}"):
                doc_resp = requests.get(f"{API_URL}/document/{doc['id']}")
                if doc_resp.status_code == 200:
                    doc_data = doc_resp.json()
                    st.subheader("Extracted Text")
                    st.text_area("Raw Text", doc_data['raw_text'], height=200, key=f"text_{doc['id']}")
                    
                    st.subheader("PII Entities")
                    entities = doc_data['entities']
                    
                    personal = [e for e in entities if e['sensitivity'] == "PERSONAL"]
                    confidential = [e for e in entities if e['sensitivity'] == "CONFIDENTIAL"]
                    non_sensitive = [e for e in entities if e['sensitivity'] == "NON_SENSITIVE"]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("### 🟢 Personal")
                        for p in personal:
                            obfuscated = p['encrypted_value'] if len(p['encrypted_value']) < 60 else p['encrypted_value'][:15] + "..."
                            st.write(f"- {p['entity_text']} ({p['entity_type']}) → `{obfuscated}`")
                    with col2:
                        st.markdown("### 🔴 Confidential")
                        for c in confidential:
                            obfuscated = c['encrypted_value'] if len(c['encrypted_value']) < 60 else c['encrypted_value'][:15] + "..."
                            st.write(f"- {c['entity_text']} ({c['entity_type']}) → `{obfuscated}`")
                    with col3:
                        st.markdown("### ⚪ Non-Sensitive")
                        for ns in non_sensitive:
                            st.write(f"- {ns['entity_text']} ({ns['entity_type']})")

                    st.markdown("---")
                    st.subheader("🛡️ Risk Analyzer")
                    if len(confidential) > 0:
                        st.error("🚨 **HIGHLY CRITICAL:** This document contains highly sensitive confidential data and presents a significant data exposure risk.")
                    elif len(personal) > 0:
                        st.warning("⚠️ **MODERATE RISK:** This document contains personal identifying data. Handle with controlled access.")
                    else:
                        st.success("✅ **LOW RISK:** No critical or personal sensitive data detected. Document is safe for general handling.")
                        
                    create_download_buttons(doc_data, f"hist_{doc['id']}", mode="encrypted")

def third_party_dashboard():
    st.title(f"Third Party Dashboard - Welcome {st.session_state['username']}")
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.header("Available Documents")
    resp = requests.get(f"{API_URL}/documents")
    if resp.status_code == 200:
        documents = resp.json().get("documents", [])
        if not documents:
            st.info("No documents available.")
            
        doc_options = {doc['file_name']: doc['id'] for doc in documents}
        selected_doc_name = st.selectbox("Select a Document to Query", [""] + list(doc_options.keys()))
        
        if selected_doc_name:
            doc_id = doc_options[selected_doc_name]
            
            st.markdown("---")
            st.subheader(f"Chat with {selected_doc_name}")
            question = st.text_area("Ask a question about this document:")
            
            # Auth state tracking
            if "auth_id" not in st.session_state:
                st.session_state["auth_id"] = None
                
            if st.button("Configure from the user"):
                resp = requests.post(f"{API_URL}/request_auth", json={"document_id": doc_id})
                if resp.status_code == 200:
                    st.session_state["auth_id"] = resp.json().get("auth_id")
                    st.info("✉️ Authorization request sent over EmailJS! Waiting for document owner to respond...")
                else:
                    st.error(f"❌ Failed to send authentication email via EmailJS. Details: {resp.text}")
                    
            # Determine Auth Level
            auth_decision = "none"
            if st.session_state["auth_id"]:
                status_resp = requests.get(f"{API_URL}/auth_status/{st.session_state['auth_id']}")
                if status_resp.status_code == 200:
                    status = status_resp.json().get("status")
                    if status == "pending":
                        st.warning("⏳ Request is pending approval via email...")
                    elif status == "yes":
                        st.success("✅ Owner Approved: Decrypted answers unlocked.")
                        auth_decision = "yes"
                    elif status == "no":
                        st.error("🚫 Owner Denied: Showing heavily encrypted answers only.")
                        auth_decision = "no"
            
            if st.button("Ask LLM"):
                with st.spinner("Analyzing document..."):
                    chat_resp = requests.post(f"{API_URL}/chat", json={"document_id": doc_id, "question": question})
                    if chat_resp.status_code == 200:
                        chat_data = chat_resp.json()
                        
                        # Serve original answer only if explicit YES was recorded
                        if auth_decision == "yes":
                            safe_answer = chat_data["original_answer"]
                            st.success("Response Generated (Decrypted):")
                        else:
                            safe_answer = chat_data["answer"]
                            st.success("Response Generated (Encrypted Data View):")
                            
                        st.write(safe_answer)
                        
                        st.info("Download the structured document metrics below:")
                        doc_resp = requests.get(f"{API_URL}/document/{doc_id}")
                        if doc_resp.status_code == 200:
                            doc_data = doc_resp.json()
                            create_download_buttons(doc_data, f"dec_third_party_{doc_id}", mode="decrypted" if auth_decision == "yes" else "encrypted")
                    else:
                        st.error(f"Error querying LLM: {chat_resp.text}")

def main():
    if "role" not in st.session_state:
        login()
    else:
        if st.session_state["role"] == "user":
            user_dashboard()
        elif st.session_state["role"] == "third_party":
            third_party_dashboard()
            
if __name__ == "__main__":
    main()

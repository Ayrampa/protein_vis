import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from langchain_core.messages import HumanMessage
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
import requests
from pymongo import MongoClient

import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
client = MongoClient(MONGO_URI)
database = client['mongo_db']
kw_collection = database["keywords"]

model_name = os.environ.get("MODEL_NAME", "llama3.2")
chat = ChatOllama(model=model_name, base_url="http://ollama:11434", temperature=0)

app = Flask(__name__)

prompt_template = PromptTemplate.from_template(
    """
    You are a translation assistant. 
    Extract the 2 the most important keyword from the following user prompt and translate them only to english. 
    Only return the translated keywords as a comma-separated list with no explanation.
    Do not use extra words.
    Prompt: "{user_prompt}"
    """
)

@app.route('/')
def home():
    return redirect(url_for('get_prompt'))

@app.route('/index', methods=['GET', 'POST'])
def get_prompt():
    user_prompt = None
    keywords = None
    if request.method == 'POST':
        user_prompt = request.form.get('prompt')
        if not user_prompt:
            return jsonify({"error": "Missing 'prompt' field"}), 400
        
        instruction = prompt_template.format(user_prompt=user_prompt)
        response = chat.invoke([HumanMessage(content=instruction)])
        keyword_string = response.content.strip()
        keywords = [kw.strip() for kw in keyword_string.split(',') if kw.strip()]
        known_protein_names = fetch_protein_names(limit=20000)    
        # Ask LLaMA3.2 to filter keywords
        relevant_keywords = filter_keywords_with_llama(keywords, known_protein_names)
        # new
        if relevant_keywords:
            all_data = query_uniprot_with_keywords(relevant_keywords)
            first_entry = all_data[0] if isinstance(all_data, list) and all_data else None
            user_data = {"prompt": user_prompt, "keywords": relevant_keywords, "uniprot_result": first_entry}
            kw_collection.insert_one(user_data)
            return render_template('index.html', prompt=user_prompt, response=relevant_keywords, uniprot_result=first_entry)

    return render_template('index.html', prompt=user_prompt)

# Get list of all protein names from datbase uniprot
def fetch_protein_names(limit=20000):
    base_url = "https://www.uniprot.org/uniprotkb?query=*&facets=reviewed%3Atrue"
    params = {
        "query": "* AND organism_id:9606",
        "format": "json",
        "fields": "protein_name",
        "size": limit
    }
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return []
    
    data = response.json().get("results", [])
    names = []
    for entry in data:
        name = entry.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value')
        if name:
            names.append(name.lower())
    return names

filter_prompt = PromptTemplate.from_template("""
You are a bioinformatics assistant. The user provided some keywords possibly related to proteins.
Your task is to check which of these keywords match or partially match real protein names.

Only return the relevant keywords that best match the given protein names as a comma-separated list with no explanation.
Do not use extra words. 

Protein Names:
{names}

Keywords:
{keywords}
""")

def filter_keywords_with_llama(keywords, names):
    names_text = "\n".join(names[:20000])  
    instruction = filter_prompt.format(
        keywords=", ".join(keywords),
        names=names_text
    )
    response = chat.invoke([HumanMessage(content=instruction)])
    return [kw.strip() for kw in response.content.strip().split(',') if kw.strip()]

def query_uniprot_with_keywords(relevant_keywords):
    if not relevant_keywords:
        return {"error": "No relevant keywords matched known protein names."}
    
    base_url = "https://rest.uniprot.org/uniprotkb/search"    
    query = " AND ".join([f"{kw}" for kw in relevant_keywords]) + " AND organism_id:9606"
    params = {
        "query": query,
        "format": "json",
        "fields": "accession,id,sequence,protein_name,organism_name,xref_pdb"
    }
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return {"error": f"UniProt API failed with status {response.status_code}"}
    
    data = response.json().get("results", [])
    if not data:
        return {"error": "No matching proteins found for keywords."}

    results = []
    for entry in data:
        protein_info = {
            "Entry": entry.get("uniProtkbId"),
            "Accession": entry.get("primaryAccession"),
            "Protein Name": entry.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value'),
            "Sequence": entry.get("sequence", {}).get("value"),
            "pdbId": entry.get("uniProtKBCrossReferences", [])
        }
        pdb_refs = [ref['id'] for ref in protein_info["pdbId"] if ref.get('database') == 'PDB']
        protein_info["pdbId"] = pdb_refs
        results.append(protein_info)

    return results


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050)

### Display the protein structure via user request
In this project we can display the 3D structure of protein by passing our request to llama3.2 language model, where it extract keywords from request, check if they are in protein names from the UniProt database, and return accession ID and 3D structure of the first mached entry from PDB database. Results are stored in MongoDb, they include: user request, keywords, and UniProt request result.

This project is built with the use of python, mongodb, Docker, flask, ollama (llama3.2 model). Interaction with llama is realised with LangChain python library.

## Build Docker containers
```bash
docker-compose up --build
```
## Run local website
```
http://127.0.0.1:5050
```
## Get access to the database
``` bash
docker compose exec mongo_db mongosh 
```
The following are the MongoDB query language commands that should be run after we entered the mongo.
```
show dbs
```
```
use mongo_db
```
```
show collections
```
```
db.users.find().pretty()
```
```
exit
```
## Example of the user request to rhe llama3.2 model via text area
```
What is the structure of the human insulin?
```
```
What is the structure of the human hemoglobin?
```
```
How does LGALS8 protein look like?
```
```
Provide me with the structure of heat shock proteins, please.
```
```
what is the structure of the KLRF2 protein?
```
```
what is the structure of ARHGAP10?
```

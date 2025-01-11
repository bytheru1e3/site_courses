from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_gigachat import GigaChat  # Updated import
from langchain.chains import create_retrieval_chain
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.faiss import FAISS
import requests
import uuid
import json
import urllib3
from file_processing import process_file
import faiss
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
auth = "MDMzOWVhYTgtMzBlZi00OTVhLTk2OTAtYjgyYjY0ODQzNTk3Ojg1YzcwM2ZhLTUzN2QtNDFhYi05ZjNkLTgzZTliNzQyMDY5NQ=="
client_id = "0339eaa8-30ef-495a-9690-b82b64843597"
secret = "85c703fa-537d-41ab-9f3d-83e9b7420695"

def get_token(auth_token, scope='GIGACHAT_API_PERS'):
    rq_uid = str(uuid.uuid4())

    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': rq_uid,
        'Authorization': f'Basic {auth_token}'
    }

    payload = {
        'scope': scope
    }

    try:
        response = requests.post(url, headers=headers, data=payload, verify=False)
        return response
    except requests.RequestException as e:
        print(f"Ошибка: {str(e)}")
        return -1

def add_file_to_vector_db(file_path, save_path, model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
    split_docs = process_file(file_path, 500, 100)
    print(f"Количество документов: {len(split_docs)}")

    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    embedding = HuggingFaceEmbeddings(model_name=model_name,
                                      model_kwargs=model_kwargs,
                                      encode_kwargs=encode_kwargs)

    # Load existing vector store or create a new one
    if os.path.exists(save_path):
        vector_store = FAISS.load_local(save_path, embedding, allow_dangerous_deserialization=True)
        print(f"Загружена существующая векторная база данных из: {save_path}")
    else:
        embedding_size = len(embedding.embed_query("test"))  # Determine the embedding size
        index = faiss.IndexFlatL2(embedding_size)  # Create a new FAISS index
        docstore = {}  # Initialize an empty docstore
        index_to_docstore_id = {}  # Initialize an empty index_to_docstore_id
        vector_store = FAISS(embedding_function=embedding, index=index, docstore=docstore, index_to_docstore_id=index_to_docstore_id)
        print(f"Создана новая векторная база данных.")

    # Add new documents to the vector store
    vector_store.add_documents(split_docs)
    vector_store.save_local(save_path)
    print(f"Векторная база данных обновлена и сохранена по пути: {save_path}")

def answer_question(query, vector_db_path, model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    embedding = HuggingFaceEmbeddings(model_name=model_name,
                                      model_kwargs=model_kwargs,
                                      encode_kwargs=encode_kwargs)

    vector_store = FAISS.load_local(vector_db_path, embedding, allow_dangerous_deserialization=True)
    embedding_retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    llm = GigaChat(credentials=auth,
                   model='GigaChat:latest',
                   verify_ssl_certs=False,
                   profanity_check=False)
    prompt = ChatPromptTemplate.from_template('''Ответь на вопрос пользователя. \
Используй при этом только информацию из контекста. Если в контексте нет \
информации для ответа, сообщи об этом пользователю.
Контекст: {context}
Вопрос: {input}
Ответ:'''
    )

    document_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=prompt
    )

    retrieval_chain = create_retrieval_chain(embedding_retriever, document_chain)

    print("Executing retrieval chain...")
    response = retrieval_chain.invoke(
        {'input': query}
    )

    print("Response received from retrieval chain.")
    return response

if __name__ == "__main__":
    file_path = "/Users/leonidstepanov/Desktop/site 2/Uploads/Вебинар №1 О правильном содержании собаки.docx"
    vector_db_path = "/Users/leonidstepanov/Desktop/site 2/vector_store_index"

    # Add file to vector database
    add_file_to_vector_db(file_path, vector_db_path)

    # Answer a question
    query = 'Какие проблемы могут возникнуть у собаки, если она не умеет успокаиваться сама?'
    response = answer_question(query, vector_db_path)
    print("Final response:", response)
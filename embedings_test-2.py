# -*- coding: utf-8 -*-
"""Embedings_test.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1tSEP87DOam2kyXpolaT7FYRWLan1AY-T
"""

pip install langchain sentence_transformers faiss-cpu langchain-community gigachat

from google.colab import drive
import langchain
from langchain.text_splitter import RecursiveCharacterTextSplitter

with  open('vvodniy_urok.txt', encoding='utf-8') as f:
  doc_text = f.read()

len(doc_text)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 500,
    chunk_overlap  = 100,
    length_function = len,
    is_separator_regex=True,  # Используем регулярное выражение
    separators= ["\n"] #разделяет по одинарному переводу строки (текст специально заранее разделил переносами, где заголовки и смысловой текст идут без переносов)
    #separators=["\d{2}:\d{2}:\d{2} - \d{2}:\d{2}:\d{2}\s+"]  # Регулярное выражение для временной метки (это пробовал для текста, который был транскрибирован с видоса, регулярка норм отрабатывает)
)

texts = text_splitter.create_documents([doc_text])

len(texts)

print(texts[2].page_content)

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': True}
model_name="deepvk/USER-bge-m3" #данная модель заточена только для русского языка
embeddings = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs)

vector_db = FAISS.from_documents(texts, embeddings)

query = 'как пользоваться маркерами'

docs = vector_db.similarity_search(query)

len(docs)

print(docs[1].page_content)

from langchain.retrievers import BM25Retriever, EnsembleRetriever

#BM25
bm25_retriever = BM25Retriever.from_documents(texts)
bm25_retriever.k = 10

#получаем документы из текстового файла, релевантные поисковому запросу
test_search_bm25_retriever = bm25_retriever.get_relevant_documents(query)

test_search_bm25_retriever

#Зададим параметры извлечения.
#В нашем случае установим, что на запрос должны возвращаться 5 фрагментов, наиболее близких по смыслу.
faiss_retriever = vector_db.as_retriever(search_kwargs={"k": 5})

#получаем документы из векторной базы, релевантные поисковому запросу
test_search_faiss_retriever = faiss_retriever.get_relevant_documents(query)

#test_search_faiss_retriever

#объединяю bm25_retriever и faiss_retriever
# Больший вес векторному поиску
ensemble_retriever = EnsembleRetriever(retrievers=[bm25_retriever, faiss_retriever], weights=[0.4, 0.6])

#используя ансамбль ретриверов производим поиск. bm25 находит 10 документов из текста, а faiss_retriever - 5.
result_doc = ensemble_retriever.get_relevant_documents(query)
result_doc

#установим Cross Encoder для дополнительного ранжирования полученных документов
#от ретривера
from sentence_transformers import CrossEncoder

cross_encoder = CrossEncoder('DiTy/cross-encoder-russian-msmarco')

#отранжируем полученные документы

documents = [doc.page_content for doc in result_doc]  # Извлекаем тексты документов

# Создаем пары "запрос-документ"
pairs = [[query, doc] for doc in documents]

# Вычисляем оценки релевантности
scores = cross_encoder.predict(pairs)

# Сортируем и фильтруем документы
sorted_pairs = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
# отбрасываем документы у которых score < 0.01
filtered_pairs = [(score, doc) for score, doc in sorted_pairs if score >= 0.01]

# Сортируем документы по убыванию оценок
#ranked_docs = [doc for _, doc in sorted(zip(scores, documents), reverse=True)]
#ranked_scores = sorted(scores, reverse=True)

# Разделяем на оценки и документы
ranked_scores = [score for score, _ in filtered_pairs]
ranked_docs = [doc for _, doc in filtered_pairs] #этот список мы используем как контекст

# Выводим результаты
for i, (doc, score) in enumerate(zip(ranked_docs, ranked_scores)):
    print(f"Рейтинг {i+1} (Оценка: {score:.4f}):")
    print(doc)
    print("-" * 40)

#Используем авторизационные данные для подключения к GigaChat API.
from google.colab import userdata
auth = userdata.get('SBER_AUTH')

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models.gigachat import GigaChat
from langchain.chains import LLMChain

#контекст
context_list = ranked_docs #отранжированные и отфилтрованные данные

# Шаблон с контекстом
template = '''Ответь на вопрос пользователя. \
Используй при этом только информацию из контекста. Если в контексте нет \
информации для ответа, сообщи об этом пользователю.
Контекст: {context}
Вопрос: {question}
Ответ:'''

prompt = ChatPromptTemplate.from_template(template)

#Создадим объект GigaChat и подготовим промпт для вопросно-ответной системы.
llm = GigaChat(credentials=auth,
              model='GigaChat:latest',
               verify_ssl_certs=False,
               profanity_check=False)

chain = LLMChain(llm=llm, prompt=prompt)

formatted_context = "\n".join([f"- {item}" for item in context_list])

resp1 = chain.invoke({
    'context': formatted_context,
    'question': query,
})

print(f'Вопрос: ==={resp1["question"]}===\n')
print(f'===Контекст:===\n {resp1["context"]}')
print(f'\n===Ответ:===\n {resp1["text"]}')

!pip-compile requirements.in
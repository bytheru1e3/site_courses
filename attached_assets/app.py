import os
from llama_cpp import Llama
from file_processing import process_file
from vector_db import VectorDB
import openai
from openai.error import OpenAIError

openai.api_key = "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"

# Инициализация Llama
MODEL_PATH = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=8)

# Системный промпт
SYSTEM_PROMPT = (
    "Ты — интеллектуальный помощник. "
    "Отвечай на вопросы точно и подробно, используя только текст из предоставленного контекста. "
    "Если ответа нет в контексте, скажи 'Информация не найдена в контексте'."
)

vector_db = VectorDB()
documents = []

def add_to_vector_db(file_path, chunk_size=4000):
    print(f"Обработка файла: {file_path}")
    try:
        vector_db.add_document(file_path)
    except Exception as e:
        print(f"Произошла ошибка при обработке файла: {e}")

def retrieve_context(question, top_k=3):
    results = vector_db.search(question, top_k=top_k)
    if not results:
        return ["Информация не найдена в контексте."]
    return results

def answer_question(question, max_tokens=4000):
    relevant_chunks = retrieve_context(question)
    if not relevant_chunks:
        return "Информация не найдена в контексте."
    
    context = "\n\n".join(relevant_chunks)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Контекст:\n{context}\n\n"
        f"Вопрос: {question}\nОтвет:"
    )

    response = llm(prompt, max_tokens=max_tokens, stop=["\n"])
    return response["choices"][0]["text"].strip()

def answer_question_ai(question, max_tokens=4000):
    relevant_chunks = retrieve_context(question)
    if not relevant_chunks:
        return "Информация не найдена в контексте."
    
    context = "\n\n".join(relevant_chunks)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Контекст:\n{context}\n\n"
        f"Вопрос: {question}\nОтвет:"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,  # Ограничьте максимальное количество токенов
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except openai.error.OpenAIError as e:
        return f"Ошибка при обращении к API OpenAI: {e}"

if __name__ == "__main__":
    vector_db = VectorDB()

    while True:
        print("\nВыберите действие:")
        print("1. Добавить файл в базу")
        print("2. Задать вопрос(локально)")
        print("3. Задать вопрос (API OPENAI)")
        print("4. Сохранить и выйти")
        choice = input("Ваш выбор: ").strip()

        if choice == "1":
            file_path = input("Введите путь к файлу (PDF, DOCX или TXT): ").strip()
            vector_db.add_document(file_path)
        elif choice == "2":
            query = input("Введите ваш вопрос: ").strip()
            answer = answer_question(query)
            print("Ответ:")
            print(answer)
        elif choice == "3":
            query = input("Введите ваш вопрос: ").strip()
            answer = answer_question_ai(query)
            print("Ответ:")
            print(answer)
        elif choice == "4":
            vector_db.save()
            print("Индекс и документы сохранены. Завершение программы.")
            break
        else:
            print("Неверный выбор. Попробуйте снова.")
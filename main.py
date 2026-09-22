from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI()

# Дозволяємо запити з будь-якого сайту (в тому числі з GitHub Pages 10 класу)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Рядок підключення з Neon.tech (Database URL)
DATABASE_URL = "postgresql://neondb_owner:npg_tkvyQ5SGXg6a@ep-cool-leaf-b2kb1p43-pooler.c-6.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Модель даних від 10 класу
class QuizResult(BaseModel):
    student_name: str
    class_name: str
    score: int
    time_seconds: int

# Ендпоінт для прийому результатів
@app.post("/api/submit")
def submit_result(data: QuizResult):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    insert_query = """
    INSERT INTO quiz_results (student_name, class_name, score, time_seconds)
    VALUES (%s, %s, %s, %s);
    """
    cursor.execute(insert_query, (data.student_name, data.class_name, data.score, data.time_seconds))
    conn.commit()
    
    cursor.close()
    conn.close()
    return {"status": "success", "message": "Результат збережено!"}

# Ендпоінт для отримання рейтингу (Leaderboard)
@app.get("/api/leaderboard")
def get_leaderboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Топ учнів
    cursor.execute("""
        SELECT student_name, class_name, score, time_seconds 
        FROM quiz_results 
        ORDER BY score DESC, time_seconds ASC 
        LIMIT 10;
    """)
    top_students = cursor.fetchall()
    
    # Топ класів
    cursor.execute("""
        SELECT class_name, ROUND(AVG(score), 2) AS avg_score 
        FROM quiz_results 
        GROUP BY class_name 
        ORDER BY avg_score DESC;
    """)
    top_classes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "top_students": [
            {"name": r[0], "class": r[1], "score": r[2], "time": r[3]} for r in top_students
        ],
        "top_classes": [
            {"class": r[0], "avg_score": float(r[1])} for r in top_classes
        ]
    }

# Допоміжний ендпоінт для розігріву сервера та БД
@app.get("/api/ping")
def ping_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1;") # Мінімальний запит для пробудження БД
    cursor.close()
    conn.close()
    return {"status": "awake"}
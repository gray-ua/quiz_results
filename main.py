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
DATABASE_URL = "postgresql://user_name:my_password@ep-cool-leaf-b2kb1p43-pooler.c-6.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
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
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO quiz_results (student_name, class_name, score, time_seconds)
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(insert_query, (data.student_name, data.class_name, data.score, data.time_seconds))
        conn.commit()
        
        cursor.close()
        return {"status": "success", "message": "Результат збережено!"}
    
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Помилка сервера/БД: {e}")
        # Повертаємо HTTPException, щоб FastAPI наклав CORS-заголовки на відповідь з помилкою
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# Ендпоінт для отримання рейтингу (Leaderboard)
@app.get("/api/leaderboard")
def get_leaderboard():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Переконуємося, що таблиця існує, аби SQL-запити нижче не падали
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id SERIAL PRIMARY KEY,
                student_name VARCHAR(100) NOT NULL,
                class_name VARCHAR(10) NOT NULL,
                score INT NOT NULL,
                time_seconds INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
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
            SELECT class_name, COALESCE(ROUND(AVG(score), 2), 0) AS avg_score 
            FROM quiz_results 
            GROUP BY class_name 
            ORDER BY avg_score DESC;
        """)
        top_classes = cursor.fetchall()
        
        cursor.close()
        
        return {
            "top_students": [
                {"name": r[0], "class": r[1], "score": r[2], "time": r[3]} for r in top_students
            ],
            "top_classes": [
                {"class": r[0], "avg_score": float(r[1])} for r in top_classes
            ]
        }
    except Exception as e:
        print(f"Помилка отримання рейтингу: {e}")
        # Якщо таблиця порожня або сталася помилка, повертаємо порожній список замість падіння 500
        return {"top_students": [], "top_classes": []}
    finally:
        if conn:
            conn.close()

# Допоміжний ендпоінт для розігріву сервера та БД
@app.get("/api/ping")
def ping_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1;") # Мінімальний запит для пробудження БД
    cursor.close()
    conn.close()
    return {"status": "awake"}
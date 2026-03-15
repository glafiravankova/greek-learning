from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import timedelta, datetime, date
import random
import re
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.permanent_session_lifetime = timedelta(days=30)

# ===== КОНСТАНТЫ ДЛЯ ТРЕНИРОВОК =====
STATUS_INTERVALS = {
    'new': 0,
    'to_learn': 0,
    'to_check': 0,
    '1_day': timedelta(days=1),
    '2_day': timedelta(days=2),
    '3_day': timedelta(days=3),
    '5_day': timedelta(days=5),
    '7_day': timedelta(days=7),
    '12_day': timedelta(days=12),
    '20_day': timedelta(days=20),
    '30_day': timedelta(days=30),
    '60_day': timedelta(days=60)
}

STATUS_ORDER = ['new', 'to_learn', 'to_check', '1_day', '2_day', '3_day', '5_day', '7_day', '12_day', '20_day', '30_day', '60_day']
DAILY_NEW_WORDS_LIMIT = 10

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def clean_text_for_comparison(text):
    """Удаляет все, кроме букв"""
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'\<[^>]*\>', '', text)
    text = re.sub(r'[^a-zA-Zα-ωΑ-ΩёЁ]', '', text)
    text = text.lower().strip()
    return text

# ===== РАБОТА С БАЗОЙ ДАННЫХ =====
def get_db_connection():
    conn = sqlite3.connect('database.db', timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

@contextmanager
def db_connection():
    conn = None
    try:
        conn = get_db_connection()
        yield conn
        if conn:
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_db():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                term TEXT NOT NULL,
                definition TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                last_reviewed DATE,
                next_review_date DATE,
                created_at DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
        ''')
        
        cursor.execute("SELECT * FROM user WHERE username = 'admin'")
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO user (username, password) VALUES (?, ?)", ('admin', 'admin'))

def upgrade_db():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(word)")
        columns = cursor.fetchall()
        column_names = [col['name'] for col in columns]
        
        if 'last_reviewed' not in column_names:
            cursor.execute("ALTER TABLE word ADD COLUMN last_reviewed DATE")
            print("Добавлена колонка last_reviewed")
        
        if 'next_review_date' not in column_names:
            cursor.execute("ALTER TABLE word ADD COLUMN next_review_date DATE")
            print("Добавлена колонка next_review_date")
        
        if 'created_at' not in column_names:
            cursor.execute("ALTER TABLE word ADD COLUMN created_at DATE DEFAULT CURRENT_DATE")
            print("Добавлена колонка created_at")

def daily_update(user_id):
    """Обновляет статусы слов в начале дня"""
    with db_connection() as conn:
        today = date.today()
        
        # Слова в статусе to_check, которые не были повторены сегодня -> to_learn
        conn.execute("""
            UPDATE word 
            SET status = 'to_learn', next_review_date = ?
            WHERE user_id = ? AND status = 'to_check' AND last_reviewed < ?
        """, (today, user_id, today))
        
        # Сколько слов уже переведено в to_learn сегодня
        already_promoted = conn.execute("""
            SELECT COUNT(*) as count FROM word 
            WHERE user_id = ? AND status = 'to_learn' AND last_reviewed = ?
        """, (user_id, today)).fetchone()['count']
        
        # Добавляем новые слова до лимита
        if already_promoted < DAILY_NEW_WORDS_LIMIT:
            limit = DAILY_NEW_WORDS_LIMIT - already_promoted
            words_to_update = conn.execute("""
                SELECT id FROM word 
                WHERE user_id = ? AND status = 'new'
                ORDER BY created_at ASC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            
            for word in words_to_update:
                conn.execute("""
                    UPDATE word 
                    SET status = 'to_learn', last_reviewed = ?, next_review_date = ?
                    WHERE id = ?
                """, (today, today, word['id']))

# Инициализация
init_db()
upgrade_db()

# ===== ОСНОВНЫЕ СТРАНИЦЫ =====

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with db_connection() as conn:
            user = conn.execute("SELECT * FROM user WHERE username = ? AND password = ?", (username, password)).fetchone()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Неверный логин или пароль")
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    daily_update(session['user_id'])
    
    with db_connection() as conn:
        words_count = conn.execute("SELECT COUNT(*) as count FROM word WHERE user_id = ?", (session['user_id'],)).fetchone()['count']
        
        # Считаем количество карточек на сегодня
        today = date.today()
        
        to_learn = conn.execute("SELECT COUNT(*) as count FROM word WHERE user_id = ? AND status = 'to_learn'", (session['user_id'],)).fetchone()['count']
        to_check = conn.execute("SELECT COUNT(*) as count FROM word WHERE user_id = ? AND status = 'to_check'", (session['user_id'],)).fetchone()['count']
        
        overdue = conn.execute("""
            SELECT COUNT(*) as count FROM word 
            WHERE user_id = ? 
            AND next_review_date < ? 
            AND status IN ('1_day', '2_day', '3_day', '5_day', '7_day', '12_day', '20_day', '30_day', '60_day')
        """, (session['user_id'], today)).fetchone()['count']
        
        due_today = conn.execute("""
            SELECT COUNT(*) as count FROM word 
            WHERE user_id = ? 
            AND next_review_date = ?
            AND status IN ('1_day', '2_day', '3_day', '5_day', '7_day', '12_day', '20_day', '30_day', '60_day')
        """, (session['user_id'], today)).fetchone()['count']
        
        # Считаем карточки: to_learn дает 2 карточки, остальные по 1
        cards_count = (to_learn * 2) + to_check + overdue + due_today
    
    return render_template('dashboard.html', words_count=words_count, cards_count=cards_count)

@app.route('/dictionary')
def dictionary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    with db_connection() as conn:
        words = conn.execute("SELECT * FROM word WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    
    return render_template('dictionary.html', words=words)

@app.route('/add', methods=['GET', 'POST'])
def add_word():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        terms = request.form.getlist('term[]')
        definitions = request.form.getlist('definition[]')
        today = date.today()
        
        with db_connection() as conn:
            for term, definition in zip(terms, definitions):
                if term and definition:
                    conn.execute("""
                        INSERT INTO word (user_id, term, definition, status, last_reviewed, next_review_date, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, term, definition, 'new', None, None, today))
        
        return redirect(url_for('dictionary'))
    
    return render_template('add_word.html')

@app.route('/delete_word/<int:word_id>', methods=['POST'])
def delete_word(word_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    with db_connection() as conn:
        word = conn.execute("SELECT * FROM word WHERE id = ? AND user_id = ?", (word_id, user_id)).fetchone()
        
        if word:
            conn.execute("DELETE FROM word WHERE id = ?", (word_id,))
            return redirect(url_for('dictionary'))
        else:
            return "Слово не найдено или у вас нет прав на его удаление", 403

@app.route('/edit_word', methods=['POST'])
def edit_word():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    word_id = request.form['word_id']
    term = request.form['term']
    definition = request.form['definition']
    
    with db_connection() as conn:
        word = conn.execute("SELECT * FROM word WHERE id = ? AND user_id = ?", (word_id, user_id)).fetchone()
        
        if word:
            conn.execute("""
                UPDATE word 
                SET term = ?, definition = ? 
                WHERE id = ? AND user_id = ?
            """, (term, definition, word_id, user_id))
            return redirect(url_for('dictionary'))
        else:
            return "Слово не найдено или у вас нет прав на его редактирование", 403

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== МАРШРУТЫ ДЛЯ ТРЕНИРОВОК =====

@app.route('/practice')
def practice():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    today = date.today()
    
    daily_update(user_id)
    
    with db_connection() as conn:
        to_learn = conn.execute("""
            SELECT * FROM word 
            WHERE user_id = ? AND status = 'to_learn'
        """, (user_id,)).fetchall()
        
        to_check = conn.execute("""
            SELECT * FROM word 
            WHERE user_id = ? AND status = 'to_check'
        """, (user_id,)).fetchall()
        
        overdue = conn.execute("""
            SELECT * FROM word 
            WHERE user_id = ? 
            AND next_review_date < ? 
            AND status IN ('1_day', '2_day', '3_day', '5_day', '7_day', '12_day', '20_day', '30_day', '60_day')
            ORDER BY next_review_date ASC
        """, (user_id, today)).fetchall()
        
        due_today = conn.execute("""
            SELECT * FROM word 
            WHERE user_id = ? 
            AND next_review_date = ?
            AND status IN ('1_day', '2_day', '3_day', '5_day', '7_day', '12_day', '20_day', '30_day', '60_day')
        """, (user_id, today)).fetchall()
    
    # СОЗДАЕМ КАРТОЧКИ ДЛЯ to_learn
    to_learn_cards = []
    for word in to_learn:
        # Первая карточка to_learn
        to_learn_cards.append({
            'word_id': word['id'],
            'type': 'to_learn_first',
            'term': word['term'],
            'definition': word['definition']
        })
        # Вторая карточка to_learn
        to_learn_cards.append({
            'word_id': word['id'],
            'type': 'to_learn_second',
            'term': word['term'],
            'definition': word['definition']
        })
    
    # ПЕРЕМЕШИВАЕМ КАРТОЧКИ to_learn
    random.shuffle(to_learn_cards)
    
    # СОЗДАЕМ КАРТОЧКИ ДЛЯ ОСТАЛЬНЫХ СТАТУСОВ
    other_cards = []
    
    # to_check - 1 карточка
    for word in to_check:
        other_cards.append({
            'word_id': word['id'],
            'type': 'to_check',
            'term': word['term'],
            'definition': word['definition']
        })
    
    # Остальные статусы - 1 карточка
    for word in overdue + due_today:
        other_cards.append({
            'word_id': word['id'],
            'type': 'regular',
            'term': word['term'],
            'definition': word['definition']
        })
    
    # ПЕРЕМЕШИВАЕМ ОСТАЛЬНЫЕ КАРТОЧКИ
    random.shuffle(other_cards)
    
    # ОБЪЕДИНЯЕМ: сначала перемешанные to_learn, потом перемешанные остальные
    cards = to_learn_cards + other_cards
    
    if not cards:
        return render_template('practice.html', no_words=True)
    
    session['cards'] = cards
    session['current_index'] = 0
    session['direction'] = random.choice(['term_to_def', 'def_to_term'])
    
    return render_template('practice.html', 
                         card=cards[0],
                         direction=session['direction'],
                         total_cards=len(cards))

@app.route('/check_answer', methods=['POST'])
def check_answer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cards = session.get('cards', [])
    current_index = session.get('current_index', 0)
    direction = session.get('direction')
    
    if not cards or current_index >= len(cards):
        return redirect(url_for('practice'))
    
    current_card = cards[current_index]
    word_id = current_card['word_id']
    card_type = current_card['type']
    
    user_answer = request.form['answer']
    
    with db_connection() as conn:
        word = conn.execute("SELECT * FROM word WHERE id = ? AND user_id = ?", (word_id, user_id)).fetchone()
        
        if not word:
            return redirect(url_for('practice'))
        
        if direction == 'term_to_def':
            correct_answer = word['definition']
        else:
            correct_answer = word['term']
        
        cleaned_user = clean_text_for_comparison(user_answer)
        cleaned_correct = clean_text_for_comparison(correct_answer)
        
        is_correct = (cleaned_user == cleaned_correct)
        
        today = date.today()
        
        # Сохраняем информацию о последнем ответе
        session['last_answer'] = {
            'word_id': word_id,
            'direction': direction,
            'user_answer': user_answer,
            'card_type': card_type
        }
        
        if is_correct:
            if card_type == 'to_learn_second':
                # Вторая карточка to_learn - переводим в to_check
                conn.execute("""
                    UPDATE word 
                    SET status = 'to_check', last_reviewed = ?, next_review_date = ?
                    WHERE id = ?
                """, (today, today, word_id))
                print(f"Слово {word_id}: to_learn_second правильно -> to_check")  # для отладки
            elif card_type == 'to_check':
                # to_check правильно - в 1_day
                conn.execute("""
                    UPDATE word 
                    SET status = '1_day', last_reviewed = ?, next_review_date = ?
                    WHERE id = ?
                """, (today, today + timedelta(days=1), word_id))
                print(f"Слово {word_id}: to_check правильно -> 1_day")
            elif card_type == 'regular':
                # Обычный статус - повышаем
                current_status = word['status']
                if current_status in STATUS_ORDER:
                    current_idx = STATUS_ORDER.index(current_status)
                    if current_idx < len(STATUS_ORDER) - 1:
                        new_status = STATUS_ORDER[current_idx + 1]
                    else:
                        new_status = current_status
                    
                    if new_status in ['1_day', '2_day', '3_day', '5_day', '7_day', '12_day', '20_day', '30_day', '60_day']:
                        days = int(new_status.split('_')[0])
                        next_date = today + timedelta(days=days)
                    else:
                        next_date = today
                    
                    conn.execute("""
                        UPDATE word 
                        SET status = ?, last_reviewed = ?, next_review_date = ?
                        WHERE id = ?
                    """, (new_status, today, next_date, word_id))
                    print(f"Слово {word_id}: {current_status} правильно -> {new_status}")
            # to_learn_first - не меняем статус, но отмечаем что был повтор
            elif card_type == 'to_learn_first':
                # Просто обновляем дату последнего повторения
                conn.execute("""
                    UPDATE word 
                    SET last_reviewed = ?
                    WHERE id = ?
                """, (today, word_id))
                print(f"Слово {word_id}: to_learn_first правильно (первый повтор)")
            
            result = 'correct'
        else:
            # Неправильно - сбрасываем в to_learn
            conn.execute("""
                UPDATE word 
                SET status = 'to_learn', last_reviewed = ?, next_review_date = ?
                WHERE id = ?
            """, (today, today, word_id))
            print(f"Слово {word_id}: неправильно -> сброс в to_learn")
            result = 'incorrect'
    
    # Удаляем текущую карточку
    cards.pop(current_index)
    session['cards'] = cards
    
    return render_template('practice_result.html', 
                         result=result,
                         word=word,
                         direction=direction,
                         user_answer=user_answer,
                         correct_answer=correct_answer,
                         remaining=len(cards))

@app.route('/skip_word', methods=['POST'])
def skip_word():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return redirect(url_for('practice'))

@app.route('/mark_as_correct', methods=['POST'])
def mark_as_correct():
    """Отмечает слово как правильное, даже если система посчитала ошибкой"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    last_answer = session.get('last_answer')
    
    if not last_answer:
        return redirect(url_for('practice'))
    
    word_id = last_answer['word_id']
    direction = last_answer['direction']
    card_type = last_answer['card_type']
    
    with db_connection() as conn:
        word = conn.execute("SELECT * FROM word WHERE id = ? AND user_id = ?", (word_id, user_id)).fetchone()
        
        if not word:
            return redirect(url_for('practice'))
        
        today = date.today()
        
        # Применяем логику правильного ответа
        if card_type == 'to_learn_second':
            # Вторая карточка to_learn - переводим в to_check
            conn.execute("""
                UPDATE word 
                SET status = 'to_check', last_reviewed = ?, next_review_date = ?
                WHERE id = ?
            """, (today, today, word_id))
        elif card_type == 'to_check':
            # to_check правильно - в 1_day
            conn.execute("""
                UPDATE word 
                SET status = '1_day', last_reviewed = ?, next_review_date = ?
                WHERE id = ?
            """, (today, today + timedelta(days=1), word_id))
        elif card_type == 'regular':
            # Обычный статус - повышаем
            current_status = word['status']
            if current_status in STATUS_ORDER:
                current_idx = STATUS_ORDER.index(current_status)
                if current_idx < len(STATUS_ORDER) - 1:
                    new_status = STATUS_ORDER[current_idx + 1]
                else:
                    new_status = current_status
                
                if new_status in ['1_day', '2_day', '3_day', '5_day', '7_day', '12_day', '20_day', '30_day', '60_day']:
                    days = int(new_status.split('_')[0])
                    next_date = today + timedelta(days=days)
                else:
                    next_date = today
                
                conn.execute("""
                    UPDATE word 
                    SET status = ?, last_reviewed = ?, next_review_date = ?
                    WHERE id = ?
                """, (new_status, today, next_date, word_id))
        # to_learn_first - ничего не меняем в БД
    
    # Удаляем последний ответ из сессии
    session.pop('last_answer', None)
    
    return redirect(url_for('practice'))

if __name__ == '__main__':
    app.run(debug=True)
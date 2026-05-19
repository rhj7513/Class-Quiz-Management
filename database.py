import sqlite3
import uuid
import pandas as pd
from datetime import datetime
from server.scoring import calculate_speed_score

DB_PATH = "class_quiz.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        class_code TEXT PRIMARY KEY,
        class_name TEXT,
        is_started INTEGER DEFAULT 0,
        is_ranking_open INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    cur.execute("PRAGMA table_info(classes)")
    class_columns = [row[1] for row in cur.fetchall()]

    if "active_worksheet_id" not in class_columns:
        cur.execute("ALTER TABLE classes ADD COLUMN active_worksheet_id INTEGER")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_code TEXT,
        team_name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS worksheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_code TEXT,
        worksheet_title TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_code TEXT,
        student_key TEXT,
        student_name TEXT,
        team_name TEXT,
        joined_at TEXT,
        UNIQUE(class_code, student_key)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_code TEXT,
        worksheet_id INTEGER,
        question_title TEXT,
        question_text TEXT,
        question_type TEXT,
        choice_1 TEXT,
        choice_2 TEXT,
        choice_3 TEXT,
        choice_4 TEXT,
        choice_5 TEXT,
        correct_answer TEXT,
        score INTEGER,
        image_data BLOB,
        created_at TEXT
    )
    """)

    cur.execute("PRAGMA table_info(questions)")
    question_columns = [row[1] for row in cur.fetchall()]

    if "worksheet_id" not in question_columns:
        cur.execute("ALTER TABLE questions ADD COLUMN worksheet_id INTEGER")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_code TEXT,
        worksheet_id INTEGER,
        student_key TEXT,
        student_name TEXT,
        team_name TEXT,
        answers_text TEXT,
        submitted_at TEXT,
        accuracy_score INTEGER,
        UNIQUE(class_code, worksheet_id, student_key)
    )
    """)

    cur.execute("PRAGMA table_info(submissions)")
    submission_columns = [row[1] for row in cur.fetchall()]

    if "worksheet_id" not in submission_columns:
        cur.execute("ALTER TABLE submissions RENAME TO submissions_old")

        cur.execute("""
        CREATE TABLE submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_code TEXT,
            worksheet_id INTEGER,
            student_key TEXT,
            student_name TEXT,
            team_name TEXT,
            answers_text TEXT,
            submitted_at TEXT,
            accuracy_score INTEGER,
            UNIQUE(class_code, worksheet_id, student_key)
        )
        """)

        cur.execute("""
        INSERT OR IGNORE INTO submissions (
            class_code, worksheet_id, student_key, student_name, team_name,
            answers_text, submitted_at, accuracy_score
        )
        SELECT
            class_code, 0, student_key, student_name, team_name,
            answers_text, submitted_at, accuracy_score
        FROM submissions_old
        """)

        cur.execute("DROP TABLE submissions_old")

    conn.commit()
    conn.close()


def create_class(class_name):
    class_code = str(uuid.uuid4())[:6].upper()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO classes (
        class_code, class_name, is_started, is_ranking_open, created_at, active_worksheet_id
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (class_code, class_name, 0, 0, datetime.now().isoformat(), None))

    conn.commit()
    conn.close()
    return class_code


def get_classes():
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM classes ORDER BY created_at DESC",
        conn
    )
    conn.close()
    return df


def add_team(class_code, team_name):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO teams (class_code, team_name)
    VALUES (?, ?)
    """, (class_code, team_name))

    conn.commit()
    conn.close()


def get_teams(class_code):
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM teams
        WHERE class_code=?
        ORDER BY id ASC
        """,
        conn,
        params=(class_code,)
    )
    conn.close()
    return df


def create_worksheet(class_code, worksheet_title):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO worksheets (class_code, worksheet_title, created_at)
    VALUES (?, ?, ?)
    """, (class_code, worksheet_title, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_worksheets(class_code):
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM worksheets
        WHERE class_code=?
        ORDER BY id ASC
        """,
        conn,
        params=(class_code,)
    )
    conn.close()
    return df


def set_active_worksheet(class_code, worksheet_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    UPDATE classes
    SET active_worksheet_id=?
    WHERE class_code=?
    """, (worksheet_id, class_code))

    conn.commit()
    conn.close()


def get_active_worksheet(class_code):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT w.*
    FROM classes c
    JOIN worksheets w ON c.active_worksheet_id = w.id
    WHERE c.class_code=?
    """, (class_code,))

    row = cur.fetchone()
    conn.close()
    return row


def start_class(class_code):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE classes SET is_started=1 WHERE class_code=?",
        (class_code,)
    )
    conn.commit()
    conn.close()


def reset_class_start(class_code):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE classes SET is_started=0 WHERE class_code=?",
        (class_code,)
    )
    conn.commit()
    conn.close()


def is_class_started(class_code):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT is_started FROM classes WHERE class_code=?",
        (class_code,)
    )
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0] == 1)


def open_ranking(class_code):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE classes SET is_ranking_open=1 WHERE class_code=?",
        (class_code,)
    )
    conn.commit()
    conn.close()


def close_ranking(class_code):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE classes SET is_ranking_open=0 WHERE class_code=?",
        (class_code,)
    )
    conn.commit()
    conn.close()


def is_ranking_open(class_code):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT is_ranking_open FROM classes WHERE class_code=?",
        (class_code,)
    )
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0] == 1)


def join_class(class_code, student_key, student_name, team_name):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO participants (
        class_code, student_key, student_name, team_name, joined_at
    )
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(class_code, student_key)
    DO UPDATE SET
        student_name=excluded.student_name
    """, (
        class_code,
        student_key,
        student_name,
        team_name,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_participant(class_code, student_key):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM participants
    WHERE class_code=? AND student_key=?
    """, (class_code, student_key))

    row = cur.fetchone()
    conn.close()
    return row


def get_participants(class_code):
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM participants
        WHERE class_code=?
        ORDER BY joined_at ASC
        """,
        conn,
        params=(class_code,)
    )
    conn.close()
    return df


def save_question(
    class_code,
    worksheet_id,
    question_title,
    question_text,
    question_type,
    choices,
    correct_answer,
    score,
    image_data
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO questions (
        class_code, worksheet_id, question_title, question_text, question_type,
        choice_1, choice_2, choice_3, choice_4, choice_5,
        correct_answer, score, image_data, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        class_code,
        worksheet_id,
        question_title,
        question_text,
        question_type,
        choices.get("choice_1", ""),
        choices.get("choice_2", ""),
        choices.get("choice_3", ""),
        choices.get("choice_4", ""),
        choices.get("choice_5", ""),
        correct_answer,
        score,
        image_data,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_questions(class_code, worksheet_id):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM questions
    WHERE class_code=? AND worksheet_id=?
    ORDER BY id ASC
    """, (class_code, worksheet_id))

    rows = cur.fetchall()
    conn.close()
    return rows


def delete_question(question_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id=?", (question_id,))
    conn.commit()
    conn.close()


def grade_answers(class_code, worksheet_id, student_answers):
    questions = get_questions(class_code, worksheet_id)
    accuracy_score = 0
    answer_lines = []

    for q in questions:
        qid = str(q["id"])
        student_answer = str(student_answers.get(qid, "")).strip()
        correct_answer = str(q["correct_answer"]).strip()

        if student_answer.lower() == correct_answer.lower():
            accuracy_score += int(q["score"])
            result = "정답"
        else:
            result = "오답"

        answer_lines.append(
            f"{q['question_title']} | 학생 답: {student_answer} | 정답: {correct_answer} | {result}"
        )

    return accuracy_score, "\n".join(answer_lines)


def already_submitted(class_code, worksheet_id, student_key):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*)
    FROM submissions
    WHERE class_code=? AND worksheet_id=? AND student_key=?
    """, (class_code, worksheet_id, student_key))

    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def submit_answers(class_code, worksheet_id, student_key, student_name, team_name, student_answers):
    questions = get_questions(class_code, worksheet_id)

    if len(questions) == 0:
        return False, "아직 문제가 생성되지 않았습니다."

    if already_submitted(class_code, worksheet_id, student_key):
        return False, "이미 제출했습니다."

    accuracy_score, answers_text = grade_answers(class_code, worksheet_id, student_answers)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO submissions (
        class_code, worksheet_id, student_key, student_name, team_name,
        answers_text, submitted_at, accuracy_score
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        class_code,
        worksheet_id,
        student_key,
        student_name,
        team_name,
        answers_text,
        datetime.now().isoformat(),
        accuracy_score
    ))

    conn.commit()
    conn.close()

    return True, "제출 완료!"


def get_submissions(class_code, worksheet_id):
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT *
        FROM submissions
        WHERE class_code=? AND worksheet_id=?
        ORDER BY submitted_at ASC
        """,
        conn,
        params=(class_code, worksheet_id)
    )
    conn.close()
    return df


def get_team_ranking(class_code, worksheet_id):
    submissions = get_submissions(class_code, worksheet_id)

    if len(submissions) == 0:
        return pd.DataFrame()

    team_order = (
        submissions
        .groupby("team_name")["submitted_at"]
        .max()
        .sort_values()
        .reset_index()
    )

    speed_map = {}

    for idx, row in team_order.iterrows():
        order = idx + 1
        speed_map[row["team_name"]] = calculate_speed_score(order)

    team_scores = (
        submissions
        .groupby("team_name")
        .agg(
            제출인원=("student_name", "count"),
            정확도점수=("accuracy_score", "mean"),
            마지막제출시간=("submitted_at", "max")
        )
        .reset_index()
    )

    team_scores["속도점수"] = team_scores["team_name"].map(speed_map)
    team_scores["총점"] = team_scores["정확도점수"] + team_scores["속도점수"]

    team_scores = team_scores.sort_values(
        by=["총점", "마지막제출시간"],
        ascending=[False, True]
    ).reset_index(drop=True)

    team_scores["순위"] = team_scores.index + 1

    return team_scores

def get_submission(class_code, worksheet_id, student_key):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM submissions
    WHERE class_code=? AND worksheet_id=? AND student_key=?
    """, (class_code, worksheet_id, student_key))

    row = cur.fetchone()
    conn.close()
    return row
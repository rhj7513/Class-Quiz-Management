import os
import uuid
import pandas as pd
import streamlit as st
from datetime import datetime
from sqlalchemy import create_engine, text
from server.scoring import calculate_speed_score

DB_PATH = ""


def get_database_url():
    database_url = st.secrets.get("DATABASE_URL", None)

    if not database_url:
        database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL이 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return database_url


def get_engine():
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_recycle=300,
    )


def row_to_dict(row):
    data = dict(row)

    if "image_data" in data and isinstance(data["image_data"], memoryview):
        data["image_data"] = bytes(data["image_data"])

    return data


def init_db():
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS classes (
            class_code TEXT PRIMARY KEY,
            class_name TEXT,
            is_started INTEGER DEFAULT 0,
            is_ranking_open INTEGER DEFAULT 0,
            active_worksheet_id INTEGER,
            created_at TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            class_code TEXT,
            team_name TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS worksheets (
            id SERIAL PRIMARY KEY,
            class_code TEXT,
            worksheet_title TEXT,
            created_at TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS participants (
            id SERIAL PRIMARY KEY,
            class_code TEXT,
            student_key TEXT,
            student_name TEXT,
            team_name TEXT,
            joined_at TEXT,
            UNIQUE(class_code, student_key)
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
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
            image_data BYTEA,
            created_at TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
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
        """))


def create_class(class_name):
    class_code = str(uuid.uuid4())[:6].upper()
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO classes (
            class_code, class_name, is_started, is_ranking_open,
            active_worksheet_id, created_at
        )
        VALUES (
            :class_code, :class_name, :is_started, :is_ranking_open,
            :active_worksheet_id, :created_at
        )
        """), {
            "class_code": class_code,
            "class_name": class_name,
            "is_started": 0,
            "is_ranking_open": 0,
            "active_worksheet_id": None,
            "created_at": datetime.now().isoformat(),
        })

    return class_code


def get_classes():
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            text("SELECT * FROM classes ORDER BY created_at DESC"),
            conn
        )

    return df


def add_team(class_code, team_name):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO teams (class_code, team_name)
        VALUES (:class_code, :team_name)
        """), {
            "class_code": class_code,
            "team_name": team_name,
        })


def get_teams(class_code):
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            text("""
            SELECT *
            FROM teams
            WHERE class_code=:class_code
            ORDER BY id ASC
            """),
            conn,
            params={"class_code": class_code}
        )

    return df


def create_worksheet(class_code, worksheet_title):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO worksheets (class_code, worksheet_title, created_at)
        VALUES (:class_code, :worksheet_title, :created_at)
        """), {
            "class_code": class_code,
            "worksheet_title": worksheet_title,
            "created_at": datetime.now().isoformat(),
        })


def get_worksheets(class_code):
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            text("""
            SELECT *
            FROM worksheets
            WHERE class_code=:class_code
            ORDER BY id ASC
            """),
            conn,
            params={"class_code": class_code}
        )

    return df


def set_active_worksheet(class_code, worksheet_id):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE classes
        SET active_worksheet_id=:worksheet_id
        WHERE class_code=:class_code
        """), {
            "worksheet_id": int(worksheet_id),
            "class_code": class_code,
        })


def get_active_worksheet(class_code):
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(text("""
        SELECT w.*
        FROM classes c
        JOIN worksheets w ON c.active_worksheet_id = w.id
        WHERE c.class_code=:class_code
        """), {
            "class_code": class_code,
        }).mappings().fetchone()

    return row_to_dict(row) if row else None


def start_class(class_code):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE classes
        SET is_started=1
        WHERE class_code=:class_code
        """), {
            "class_code": class_code,
        })


def reset_class_start(class_code):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE classes
        SET is_started=0
        WHERE class_code=:class_code
        """), {
            "class_code": class_code,
        })


def is_class_started(class_code):
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(text("""
        SELECT is_started
        FROM classes
        WHERE class_code=:class_code
        """), {
            "class_code": class_code,
        }).fetchone()

    return bool(row and row[0] == 1)


def open_ranking(class_code):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE classes
        SET is_ranking_open=1
        WHERE class_code=:class_code
        """), {
            "class_code": class_code,
        })


def close_ranking(class_code):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE classes
        SET is_ranking_open=0
        WHERE class_code=:class_code
        """), {
            "class_code": class_code,
        })


def is_ranking_open(class_code):
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(text("""
        SELECT is_ranking_open
        FROM classes
        WHERE class_code=:class_code
        """), {
            "class_code": class_code,
        }).fetchone()

    return bool(row and row[0] == 1)


def join_class(class_code, student_key, student_name, team_name):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO participants (
            class_code, student_key, student_name, team_name, joined_at
        )
        VALUES (
            :class_code, :student_key, :student_name, :team_name, :joined_at
        )
        ON CONFLICT(class_code, student_key)
        DO UPDATE SET
            student_name=EXCLUDED.student_name
        """), {
            "class_code": class_code,
            "student_key": student_key,
            "student_name": student_name,
            "team_name": team_name,
            "joined_at": datetime.now().isoformat(),
        })


def get_participant(class_code, student_key):
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(text("""
        SELECT *
        FROM participants
        WHERE class_code=:class_code AND student_key=:student_key
        """), {
            "class_code": class_code,
            "student_key": student_key,
        }).mappings().fetchone()

    return row_to_dict(row) if row else None


def get_participants(class_code):
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            text("""
            SELECT *
            FROM participants
            WHERE class_code=:class_code
            ORDER BY joined_at ASC
            """),
            conn,
            params={"class_code": class_code}
        )

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
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO questions (
            class_code, worksheet_id, question_title, question_text,
            question_type, choice_1, choice_2, choice_3, choice_4,
            choice_5, correct_answer, score, image_data, created_at
        )
        VALUES (
            :class_code, :worksheet_id, :question_title, :question_text,
            :question_type, :choice_1, :choice_2, :choice_3, :choice_4,
            :choice_5, :correct_answer, :score, :image_data, :created_at
        )
        """), {
            "class_code": class_code,
            "worksheet_id": int(worksheet_id),
            "question_title": question_title,
            "question_text": question_text,
            "question_type": question_type,
            "choice_1": choices.get("choice_1", ""),
            "choice_2": choices.get("choice_2", ""),
            "choice_3": choices.get("choice_3", ""),
            "choice_4": choices.get("choice_4", ""),
            "choice_5": choices.get("choice_5", ""),
            "correct_answer": correct_answer,
            "score": int(score),
            "image_data": image_data,
            "created_at": datetime.now().isoformat(),
        })


def get_questions(class_code, worksheet_id):
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(text("""
        SELECT *
        FROM questions
        WHERE class_code=:class_code AND worksheet_id=:worksheet_id
        ORDER BY id ASC
        """), {
            "class_code": class_code,
            "worksheet_id": int(worksheet_id),
        }).mappings().all()

    return [row_to_dict(row) for row in rows]


def delete_question(question_id):
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        DELETE FROM questions
        WHERE id=:question_id
        """), {
            "question_id": int(question_id),
        })


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
    engine = get_engine()

    with engine.connect() as conn:
        count = conn.execute(text("""
        SELECT COUNT(*)
        FROM submissions
        WHERE class_code=:class_code
          AND worksheet_id=:worksheet_id
          AND student_key=:student_key
        """), {
            "class_code": class_code,
            "worksheet_id": int(worksheet_id),
            "student_key": student_key,
        }).scalar()

    return count > 0


def submit_answers(class_code, worksheet_id, student_key, student_name, team_name, student_answers):
    questions = get_questions(class_code, worksheet_id)

    if len(questions) == 0:
        return False, "아직 문제가 생성되지 않았습니다."

    if already_submitted(class_code, worksheet_id, student_key):
        return False, "이미 제출했습니다."

    accuracy_score, answers_text = grade_answers(class_code, worksheet_id, student_answers)
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO submissions (
            class_code, worksheet_id, student_key, student_name, team_name,
            answers_text, submitted_at, accuracy_score
        )
        VALUES (
            :class_code, :worksheet_id, :student_key, :student_name, :team_name,
            :answers_text, :submitted_at, :accuracy_score
        )
        ON CONFLICT(class_code, worksheet_id, student_key)
        DO NOTHING
        """), {
            "class_code": class_code,
            "worksheet_id": int(worksheet_id),
            "student_key": student_key,
            "student_name": student_name,
            "team_name": team_name,
            "answers_text": answers_text,
            "submitted_at": datetime.now().isoformat(),
            "accuracy_score": int(accuracy_score),
        })

    return True, "제출 완료!"


def get_submission(class_code, worksheet_id, student_key):
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(text("""
        SELECT *
        FROM submissions
        WHERE class_code=:class_code
          AND worksheet_id=:worksheet_id
          AND student_key=:student_key
        """), {
            "class_code": class_code,
            "worksheet_id": int(worksheet_id),
            "student_key": student_key,
        }).mappings().fetchone()

    return row_to_dict(row) if row else None


def get_submissions(class_code, worksheet_id):
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            text("""
            SELECT *
            FROM submissions
            WHERE class_code=:class_code AND worksheet_id=:worksheet_id
            ORDER BY submitted_at ASC
            """),
            conn,
            params={
                "class_code": class_code,
                "worksheet_id": int(worksheet_id),
            }
        )

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

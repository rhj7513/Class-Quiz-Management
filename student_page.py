import html
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from server.database import (
    get_questions,
    submit_answers,
    get_team_ranking,
    join_class,
    get_participant,
    is_class_started,
    is_ranking_open,
    get_teams,
    already_submitted,
    get_active_worksheet,
    get_submission,
)


def render_podium(team_rank):
    if len(team_rank) == 0:
        st.info("아직 팀 순위가 없습니다.")
        return

    top_rows = team_rank.head(3).to_dict("records")

    rank_map = {}
    for row in top_rows:
        rank_map[int(row["순위"])] = row

    def make_circle(rank, row):
        if not row:
            return ""

        team_name = html.escape(str(row["team_name"]))
        total_score = round(float(row["총점"]), 1)
        accuracy_score = round(float(row["정확도점수"]), 1)
        speed_score = round(float(row["속도점수"]), 1)

        medal = {
            1: "🥇",
            2: "🥈",
            3: "🥉",
        }.get(rank, "")

        return f"""
        <div class="podium-item rank-{rank}">
            <div class="podium-circle">
                <div class="podium-medal">{medal}</div>
                <div class="podium-rank">{rank}등</div>
                <div class="podium-team">{team_name}</div>
                <div class="podium-score">{total_score}점</div>
            </div>
            <div class="podium-detail">
                정확도 {accuracy_score} · 속도 {speed_score}
            </div>
        </div>
        """

    second = make_circle(2, rank_map.get(2))
    first = make_circle(1, rank_map.get(1))
    third = make_circle(3, rank_map.get(3))

    st.markdown(
        f"""
        <style>
        .podium-wrap {{
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            gap: 28px;
            padding: 28px 8px 24px;
            margin: 10px 0 26px;
        }}

        .podium-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            min-width: 180px;
        }}

        .podium-circle {{
            border-radius: 999px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #1f2937;
            box-shadow:
                0 18px 45px rgba(15, 23, 42, 0.22),
                inset 0 2px 8px rgba(255, 255, 255, 0.7);
            border: 5px solid rgba(255, 255, 255, 0.95);
        }}

        .rank-1 .podium-circle {{
            width: 230px;
            height: 230px;
            background: radial-gradient(circle at 35% 25%, #fff7b8 0%, #facc15 38%, #f59e0b 100%);
        }}

        .rank-2 .podium-circle {{
            width: 185px;
            height: 185px;
            background: radial-gradient(circle at 35% 25%, #ffffff 0%, #d1d5db 42%, #94a3b8 100%);
            margin-top: 42px;
        }}

        .rank-3 .podium-circle {{
            width: 165px;
            height: 165px;
            background: radial-gradient(circle at 35% 25%, #fed7aa 0%, #fb923c 43%, #c2410c 100%);
            margin-top: 74px;
        }}

        .podium-medal {{
            font-size: 36px;
            line-height: 1;
            margin-bottom: 5px;
        }}

        .rank-1 .podium-medal {{
            font-size: 48px;
        }}

        .podium-rank {{
            font-size: 26px;
            font-weight: 900;
            line-height: 1.1;
        }}

        .rank-1 .podium-rank {{
            font-size: 34px;
        }}

        .podium-team {{
            max-width: 78%;
            margin-top: 6px;
            font-size: 20px;
            font-weight: 800;
            line-height: 1.2;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }}

        .rank-1 .podium-team {{
            font-size: 25px;
        }}

        .podium-score {{
            margin-top: 7px;
            font-size: 18px;
            font-weight: 800;
        }}

        .rank-1 .podium-score {{
            font-size: 22px;
        }}

        .podium-detail {{
            margin-top: 12px;
            padding: 7px 12px;
            border-radius: 999px;
            background: #f8fafc;
            color: #475569;
            font-size: 14px;
            font-weight: 700;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
        }}

        @media (max-width: 760px) {{
            .podium-wrap {{
                gap: 10px;
                padding-left: 0;
                padding-right: 0;
            }}

            .podium-item {{
                min-width: 104px;
            }}

            .rank-1 .podium-circle {{
                width: 132px;
                height: 132px;
            }}

            .rank-2 .podium-circle {{
                width: 112px;
                height: 112px;
                margin-top: 24px;
            }}

            .rank-3 .podium-circle {{
                width: 104px;
                height: 104px;
                margin-top: 42px;
            }}

            .podium-medal,
            .rank-1 .podium-medal {{
                font-size: 26px;
            }}

            .podium-rank,
            .rank-1 .podium-rank {{
                font-size: 18px;
            }}

            .podium-team,
            .rank-1 .podium-team {{
                font-size: 14px;
            }}

            .podium-score,
            .rank-1 .podium-score {{
                font-size: 13px;
            }}

            .podium-detail {{
                display: none;
            }}
        }}
        </style>

        <div class="podium-wrap">
            {second}
            {first}
            {third}
        </div>
        """,
        unsafe_allow_html=True
    )

    if len(team_rank) > 3:
        st.subheader("전체 순위")
    else:
        st.subheader("순위표")

    st.dataframe(
        team_rank[[
            "순위",
            "team_name",
            "제출인원",
            "정확도점수",
            "속도점수",
            "총점"
        ]].rename(columns={
            "team_name": "팀"
        }),
        use_container_width=True
    )


def parse_submission_answers(submission):
    if not submission:
        return {}

    answers_text = submission["answers_text"] or ""
    lines = answers_text.splitlines()

    parsed = {}

    for idx, line in enumerate(lines, start=1):
        parts = [part.strip() for part in line.split("|")]

        student_answer = ""
        correct_answer = ""
        result = ""

        for part in parts:
            if part.startswith("학생 답:"):
                student_answer = part.replace("학생 답:", "").strip()
            elif part.startswith("정답:"):
                correct_answer = part.replace("정답:", "").strip()
            elif part in ["정답", "오답"]:
                result = part

        parsed[idx] = {
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "result": result,
        }

    return parsed


def render_answer_result(student_answer, correct_answer, result):
    if result == "정답":
        st.success(f"내 답: {student_answer}  |  정답: {correct_answer}  |  결과: 정답")
    else:
        st.error(f"내 답: {student_answer}  |  정답: {correct_answer}  |  결과: 오답")


def render_worksheet_review(questions, submission):
    answer_map = parse_submission_answers(submission)

    st.divider()
    st.header("📘 활동지 전체 보기")

    for idx, q in enumerate(questions, start=1):
        answer_info = answer_map.get(idx, {})

        student_answer = str(answer_info.get("student_answer", ""))
        correct_answer = str(answer_info.get("correct_answer", q["correct_answer"]))
        result = answer_info.get("result", "")

        st.divider()

        st.subheader(f"{idx}. {q['question_title']} ({q['score']}점)")
        st.write(q["question_text"])

        if q["image_data"]:
            st.image(q["image_data"], width=450)

        st.caption(f"문제 유형: {q['question_type']}")

        if q["question_type"] == "OX":
            col1, col2 = st.columns(2)

            with col1:
                if student_answer == "O":
                    st.info("내 선택: O")
                elif correct_answer == "O":
                    st.success("정답: O")
                else:
                    st.write("O")

            with col2:
                if student_answer == "X":
                    st.info("내 선택: X")
                elif correct_answer == "X":
                    st.success("정답: X")
                else:
                    st.write("X")

            render_answer_result(student_answer, correct_answer, result)

        elif q["question_type"] == "5지선다":
            choices = {
                "1": q["choice_1"],
                "2": q["choice_2"],
                "3": q["choice_3"],
                "4": q["choice_4"],
                "5": q["choice_5"],
            }

            st.write("선택지")

            for number, text in choices.items():
                labels = []

                if number == student_answer:
                    labels.append("내 선택")

                if number == correct_answer:
                    labels.append("정답")

                label_text = f" ({', '.join(labels)})" if labels else ""

                if number == correct_answer:
                    st.success(f"{number}. {text}{label_text}")
                elif number == student_answer:
                    st.error(f"{number}. {text}{label_text}")
                else:
                    st.write(f"{number}. {text}")

            render_answer_result(student_answer, correct_answer, result)

        else:
            st.write(f"내 답: {student_answer}")
            st.success(f"예시 정답: {correct_answer}")

            if result == "정답":
                st.success("결과: 정답")
            else:
                st.error("결과: 오답")


def render_student_page(class_code):
    st_autorefresh(interval=2000, key="student_auto_refresh")

    st.title("👩‍🎓 학생 화면")

    if "student_ready" not in st.session_state:
        st.session_state.student_ready = False

    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    if not st.session_state.student_ready:
        st.header("입장하기")

        student_number = st.text_input("학급반 번호", placeholder="예: 1101")
        student_name = st.text_input("이름")

        teams = get_teams(class_code)

        if len(teams) == 0:
            st.warning("아직 생성된 팀이 없습니다. 선생님이 팀을 만든 뒤 다시 접속해주세요.")
            return

        team_name = st.selectbox(
            "팀 선택",
            teams["team_name"].tolist()
        )

        if st.button("입장하기"):
            if not student_number:
                st.error("학급반 번호를 입력해주세요.")
            elif not student_name:
                st.error("이름을 입력해주세요.")
            else:
                student_key = student_number.strip()

                join_class(
                    class_code,
                    student_key,
                    student_name,
                    team_name
                )

                participant = get_participant(class_code, student_key)

                st.session_state.student_key = student_key
                st.session_state.student_number = student_number
                st.session_state.student_name = participant["student_name"]
                st.session_state.team_name = participant["team_name"]
                st.session_state.student_ready = True
                st.session_state.submitted = False
                st.session_state.current_worksheet_id = None

                st.rerun()

        return

    started = is_class_started(class_code)

    if not started:
        st.success(f"{st.session_state.team_name}팀 입장 완료!")

        st.header("⏳ 대기 화면")
        st.info("아직 선생님이 문제 풀이를 시작하지 않았습니다.")

        st.write(f"학급반 번호: {st.session_state.student_number}")
        st.write(f"이름: {st.session_state.student_name}")
        st.write(f"팀: {st.session_state.team_name}")

        st.caption("선생님이 시작 버튼을 누르면 자동으로 문제 화면으로 이동합니다.")
        return

    active_worksheet = get_active_worksheet(class_code)

    if not active_worksheet:
        st.warning("아직 선생님이 학습지를 선택하지 않았습니다.")
        return

    worksheet_id = active_worksheet["id"]

    if st.session_state.get("current_worksheet_id") != worksheet_id:
        st.session_state.current_worksheet_id = worksheet_id
        st.session_state.submitted = False

    st.info(f"현재 학습지: {active_worksheet['worksheet_title']}")

    questions = get_questions(class_code, worksheet_id)

    if len(questions) == 0:
        st.warning("아직 생성된 문제가 없습니다.")
        return

    if already_submitted(class_code, worksheet_id, st.session_state.student_key):
        st.session_state.submitted = True

    if st.session_state.submitted:
        st.success("답안 제출 완료!")

        ranking_open = is_ranking_open(class_code)

        if not ranking_open:
            st.header("🏅 팀 순위")
            st.info("아직 선생님이 순위와 활동지 풀이를 공개하지 않았습니다.")
            return

        st.header("🏆 팀 순위 발표")
        st.success("팀 순위 공개!")

        team_rank = get_team_ranking(class_code, worksheet_id)
        render_podium(team_rank)

        submission = get_submission(
            class_code,
            worksheet_id,
            st.session_state.student_key
        )

        render_worksheet_review(questions, submission)
        return

    st.success("문제 풀이 시작!")

    student_answers = {}

    for idx, q in enumerate(questions, start=1):
        st.divider()

        st.subheader(f"{idx}. {q['question_title']} ({q['score']}점)")
        st.write(q["question_text"])

        if q["image_data"]:
            st.image(q["image_data"], width=450)

        qid = str(q["id"])

        if q["question_type"] == "OX":
            student_answers[qid] = st.radio(
                "답 선택",
                ["O", "X"],
                index=None,
                horizontal=True,
                key=f"answer_{worksheet_id}_{qid}"
            )

        elif q["question_type"] == "5지선다":
            options = {
                "1": f"① {q['choice_1']}",
                "2": f"② {q['choice_2']}",
                "3": f"③ {q['choice_3']}",
                "4": f"④ {q['choice_4']}",
                "5": f"⑤ {q['choice_5']}",
            }

            selected = st.radio(
                "답 선택",
                list(options.keys()),
                index=None,
                format_func=lambda x: options[x],
                key=f"answer_{worksheet_id}_{qid}"
            )

            student_answers[qid] = selected

        else:
            student_answers[qid] = st.text_area(
                "답 입력",
                key=f"answer_{worksheet_id}_{qid}"
            )

    st.divider()

    if st.button("전체 답안 제출하기"):
        unanswered = []

        for idx, q in enumerate(questions, start=1):
            qid = str(q["id"])
            answer = student_answers.get(qid)

            if answer is None or str(answer).strip() == "":
                unanswered.append(idx)

        if unanswered:
            st.error(f"답하지 않은 문제가 있습니다: {unanswered}")
            st.stop()

        success, message = submit_answers(
            class_code,
            worksheet_id,
            st.session_state.student_key,
            st.session_state.student_name,
            st.session_state.team_name,
            student_answers
        )

        if success:
            st.session_state.submitted = True
            st.success(message)
            st.rerun()
        else:
            st.error(message)
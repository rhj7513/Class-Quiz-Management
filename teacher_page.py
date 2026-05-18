import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from server.database import (
    create_class,
    get_classes,
    add_team,
    get_teams,
    create_worksheet,
    get_worksheets,
    set_active_worksheet,
    get_active_worksheet,
    save_question,
    get_questions,
    delete_question,
    get_submissions,
    get_participants,
    start_class,
    reset_class_start,
    is_class_started,
    get_team_ranking,
    open_ranking,
    close_ranking,
    is_ranking_open,
)

from server.qr_utils import make_qr


def render_teacher_page():
    st.title("👩‍🏫 교사 화면")

    menu = st.sidebar.radio(
        "교사 메뉴",
        [
            "클래스 생성",
            "팀 설정",
            "활동지 만들기",
            "QR 코드 생성",
            "대기실 관리",
            "제출 현황 / 순위표",
        ],
    )

    if menu == "클래스 생성":
        st.header("1️⃣ 클래스 생성")

        class_name = st.text_input("클래스 이름", placeholder="예: 1학년 1반")

        if st.button("클래스 만들기"):
            if not class_name:
                st.error("클래스 이름을 입력해주세요.")
            else:
                class_code = create_class(class_name)
                st.success(f"클래스 생성 완료! 클래스 코드: {class_code}")

        st.subheader("생성된 클래스")
        st.dataframe(get_classes(), use_container_width=True)

    elif menu == "팀 설정":
        st.header("2️⃣ 팀 설정")

        classes = get_classes()

        if len(classes) == 0:
            st.warning("먼저 클래스를 생성해주세요.")
            return

        selected_class = st.selectbox(
            "클래스 선택",
            classes["class_code"].tolist(),
            format_func=lambda x: f"{x} - {classes[classes['class_code'] == x]['class_name'].values[0]}"
        )

        st.divider()

        team_name = st.text_input("팀 이름", placeholder="예: 1조")

        if st.button("팀 추가"):
            if not team_name:
                st.error("팀 이름을 입력해주세요.")
            else:
                add_team(selected_class, team_name)
                st.success("팀 추가 완료!")
                st.rerun()

        teams = get_teams(selected_class)

        st.subheader("현재 팀 목록")

        if len(teams) == 0:
            st.info("아직 생성된 팀이 없습니다.")
        else:
            st.dataframe(
                teams[["team_name"]].rename(columns={"team_name": "팀 이름"}),
                use_container_width=True
            )

    elif menu == "활동지 만들기":
        st.header("3️⃣ 활동지 만들기")

        classes = get_classes()

        if len(classes) == 0:
            st.warning("먼저 클래스를 생성해주세요.")
            return

        selected_class = st.selectbox(
            "클래스 선택",
            classes["class_code"].tolist(),
            format_func=lambda x: f"{x} - {classes[classes['class_code'] == x]['class_name'].values[0]}"
        )

        st.divider()
        st.subheader("학습지 선택 / 생성")

        worksheet_title = st.text_input("새 학습지 이름", placeholder="예: 1번 학습지")

        if st.button("학습지 만들기"):
            if not worksheet_title:
                st.error("학습지 이름을 입력해주세요.")
            else:
                create_worksheet(selected_class, worksheet_title)
                st.success("학습지 생성 완료!")
                st.rerun()

        worksheets = get_worksheets(selected_class)

        if len(worksheets) == 0:
            st.info("먼저 학습지를 만들어주세요.")
            return

        selected_worksheet = st.selectbox(
            "문제를 넣을 학습지 선택",
            worksheets["id"].tolist(),
            format_func=lambda x: worksheets[worksheets["id"] == x]["worksheet_title"].values[0]
        )

        st.divider()

        question_title = st.text_input("문제 제목")
        question_text = st.text_area("문제 지문", height=180)

        image_file = st.file_uploader(
            "문제 이미지",
            type=["png", "jpg", "jpeg"]
        )

        question_type = st.selectbox(
            "문제 유형",
            ["OX", "5지선다", "서술형"]
        )

        choices = {
            "choice_1": "",
            "choice_2": "",
            "choice_3": "",
            "choice_4": "",
            "choice_5": "",
        }

        if question_type == "OX":
            correct_answer = st.radio("정답", ["O", "X"], horizontal=True)

        elif question_type == "5지선다":
            choices["choice_1"] = st.text_input("①")
            choices["choice_2"] = st.text_input("②")
            choices["choice_3"] = st.text_input("③")
            choices["choice_4"] = st.text_input("④")
            choices["choice_5"] = st.text_input("⑤")

            correct_answer = st.selectbox(
                "정답 번호",
                ["1", "2", "3", "4", "5"]
            )

        else:
            correct_answer = st.text_input("정답")

        score = st.number_input(
            "문항 배점",
            min_value=0,
            max_value=100,
            value=10
        )

        if st.button("문제 저장하기"):
            if not question_title or not question_text:
                st.error("문제 제목과 지문을 입력해주세요.")
            else:
                image_data = image_file.getvalue() if image_file else None

                save_question(
                    selected_class,
                    selected_worksheet,
                    question_title,
                    question_text,
                    question_type,
                    choices,
                    correct_answer,
                    score,
                    image_data
                )

                st.success("문제 저장 완료!")
                st.rerun()

        st.divider()

        questions = get_questions(selected_class, selected_worksheet)

        st.subheader("저장된 문제")

        if len(questions) == 0:
            st.info("저장된 문제가 없습니다.")
        else:
            for idx, q in enumerate(questions, start=1):
                with st.expander(f"{idx}. {q['question_title']} ({q['score']}점)"):
                    st.write(q["question_text"])

                    if q["image_data"]:
                        st.image(q["image_data"], width=350)

                    st.write(f"문제 유형: {q['question_type']}")
                    st.write(f"정답: {q['correct_answer']}")

                    if st.button("삭제", key=f"delete_{q['id']}"):
                        delete_question(q["id"])
                        st.success("문제 삭제 완료!")
                        st.rerun()

    elif menu == "QR 코드 생성":
        st.header("4️⃣ QR 코드 생성")

        classes = get_classes()

        if len(classes) == 0:
            st.warning("먼저 클래스를 생성해주세요.")
            return

        selected_class = st.selectbox(
            "클래스 선택",
            classes["class_code"].tolist(),
            format_func=lambda x: f"{x} - {classes[classes['class_code'] == x]['class_name'].values[0]}"
        )

        st.divider()

        current_url = streamlit_js_eval(
            js_expressions="window.location.origin",
            key="get_current_url"
        )

        base_url = st.text_input(
            "배포 주소 또는 현재 주소",
            value=current_url or "",
            placeholder="예: https://example.streamlit.app"
        )

        if base_url:
            base_url = base_url.rstrip("/")
            student_url = f"{base_url}?class_code={selected_class}"

            st.subheader("학생 입장 주소")
            st.code(student_url)

            st.markdown(
                f"""
                <input type="text" value="{student_url}" id="copyTarget" style="width:100%;padding:8px;">
                <button onclick="
                    navigator.clipboard.writeText(document.getElementById('copyTarget').value);
                    alert('주소가 복사되었습니다!');
                ">
                주소 복사하기
                </button>
                """,
                unsafe_allow_html=True
            )

            st.subheader("학생 입장 QR 코드")
            qr_image = make_qr(student_url)
            st.image(qr_image, width=280)

    elif menu == "대기실 관리":
        st.header("5️⃣ 대기실 관리")

        classes = get_classes()

        if len(classes) == 0:
            return

        selected_class = st.selectbox("클래스 선택", classes["class_code"].tolist())

        worksheets = get_worksheets(selected_class)

        if len(worksheets) == 0:
            st.warning("먼저 학습지를 만들어주세요.")
            return

        selected_worksheet = st.selectbox(
            "이번에 풀 학습지 선택",
            worksheets["id"].tolist(),
            format_func=lambda x: worksheets[worksheets["id"] == x]["worksheet_title"].values[0]
        )

        active_worksheet = get_active_worksheet(selected_class)

        if active_worksheet:
            st.info(f"현재 선택된 학습지: {active_worksheet['worksheet_title']}")

        started = is_class_started(selected_class)

        if started:
            st.success("현재 문제 풀이 진행 중")
        else:
            st.info("현재 학생 대기 중")

        participants = get_participants(selected_class)

        st.metric("입장 학생 수", len(participants))

        if len(participants) > 0:
            st.dataframe(
                participants[[
                    "team_name",
                    "student_name",
                    "joined_at"
                ]].rename(columns={
                    "team_name": "팀",
                    "student_name": "학생",
                    "joined_at": "입장 시간"
                }),
                use_container_width=True
            )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("문제 풀이 시작하기"):
                set_active_worksheet(selected_class, selected_worksheet)
                close_ranking(selected_class)
                start_class(selected_class)
                st.success("문제 풀이 시작!")
                st.rerun()

        with col2:
            if st.button("다시 대기 상태로"):
                reset_class_start(selected_class)
                close_ranking(selected_class)
                st.warning("대기 상태 변경 완료")
                st.rerun()

    elif menu == "제출 현황 / 순위표":
        st.header("6️⃣ 제출 현황 / 순위표")

        classes = get_classes()

        if len(classes) == 0:
            return

        selected_class = st.selectbox("클래스 선택", classes["class_code"].tolist())

        worksheets = get_worksheets(selected_class)

        if len(worksheets) == 0:
            st.warning("먼저 학습지를 만들어주세요.")
            return

        selected_worksheet = st.selectbox(
            "확인할 학습지 선택",
            worksheets["id"].tolist(),
            format_func=lambda x: worksheets[worksheets["id"] == x]["worksheet_title"].values[0]
        )

        ranking_open = is_ranking_open(selected_class)

        if ranking_open:
            st.success("현재 상태: 팀 순위 공개 중")
        else:
            st.info("현재 상태: 팀 순위 비공개")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🏆 팀 순위 공개하기"):
                open_ranking(selected_class)
                st.success("학생들에게 팀 순위가 공개되었습니다.")
                st.rerun()

        with col2:
            if st.button("🙈 팀 순위 숨기기"):
                close_ranking(selected_class)
                st.warning("학생 화면에서 순위가 숨겨졌습니다.")
                st.rerun()

        st.divider()

        df = get_submissions(selected_class, selected_worksheet)

        if len(df) == 0:
            st.info("아직 제출된 답안이 없습니다.")
        else:
            st.subheader("개인 제출 현황")

            st.dataframe(
                df[[
                    "team_name",
                    "student_name",
                    "submitted_at",
                    "accuracy_score"
                ]].rename(columns={
                    "team_name": "팀",
                    "student_name": "학생",
                    "submitted_at": "제출 시간",
                    "accuracy_score": "점수"
                }),
                use_container_width=True
            )

            st.subheader("팀 순위")

            team_rank = get_team_ranking(selected_class, selected_worksheet)

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
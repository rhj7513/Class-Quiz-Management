import streamlit as st
from server.database import init_db
from teacher.teacher_page import render_teacher_page
from student.student_page import render_student_page

st.set_page_config(
    page_title="팀전 활동지 제출 사이트",
    page_icon="🏆",
    layout="wide"
)

init_db()

class_code = st.query_params.get("class_code")

if class_code:
    render_student_page(class_code)
else:
    render_teacher_page()
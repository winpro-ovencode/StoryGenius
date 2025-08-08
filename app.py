import streamlit as st
import json
import os
from pdf_processor import PDFProcessor
from character_extractor import CharacterExtractor
from chatbot import Chatbot
from data_manager import DataManager

# 페이지 설정
st.set_page_config(
    page_title="소설 캐릭터 챗봇",
    page_icon="📚",
    layout="wide"
)

# 세션 상태 초기화
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()

if 'pdf_processor' not in st.session_state:
    st.session_state.pdf_processor = PDFProcessor()

if 'character_extractor' not in st.session_state:
    st.session_state.character_extractor = CharacterExtractor()

if 'chatbot' not in st.session_state:
    st.session_state.chatbot = Chatbot()

if 'current_novel' not in st.session_state:
    st.session_state.current_novel = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}

if 'story_mode_history' not in st.session_state:
    st.session_state.story_mode_history = []

def main():
    st.title("📚 소설 캐릭터 AI 챗봇 시스템")
    
    # 사이드바 메뉴
    with st.sidebar:
        st.header("메뉴")
        menu = st.selectbox(
            "기능 선택",
            ["소설 업로드", "챕터 분석", "캐릭터 관리", "캐릭터 대화", "스토리 모드"]
        )
        
        # 현재 소설 정보 표시
        if st.session_state.current_novel:
            st.info(f"현재 소설: {st.session_state.current_novel['title']}")
            st.write(f"챕터 수: {len(st.session_state.current_novel.get('chapters', []))}")
            st.write(f"캐릭터 수: {len(st.session_state.current_novel.get('characters', []))}")

    if menu == "소설 업로드":
        show_upload_page()
    elif menu == "챕터 분석":
        show_chapter_analysis_page()
    elif menu == "캐릭터 관리":
        show_character_management_page()
    elif menu == "캐릭터 대화":
        show_character_chat_page()
    elif menu == "스토리 모드":
        show_story_mode_page()

def show_upload_page():
    st.header("📁 소설 PDF 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 업로드하세요",
        type=['pdf'],
        help="소설이 포함된 PDF 파일을 업로드하면 자동으로 분석됩니다."
    )
    
    if uploaded_file is not None:
        # 파일 정보 표시
        st.info(f"파일명: {uploaded_file.name}")
        st.info(f"파일 크기: {uploaded_file.size:,} bytes")
        
        if st.button("PDF 분석 시작", type="primary"):
            with st.spinner("PDF를 분석하고 있습니다..."):
                try:
                    # PDF 텍스트 추출
                    text_content = st.session_state.pdf_processor.extract_text(uploaded_file)
                    
                    if text_content:
                        # 소설 정보 생성
                        novel_info = {
                            'title': uploaded_file.name.replace('.pdf', ''),
                            'content': text_content,
                            'chapters': [],
                            'characters': []
                        }
                        
                        # 데이터 매니저에 저장
                        st.session_state.data_manager.save_novel(novel_info)
                        st.session_state.current_novel = novel_info
                        
                        st.success("PDF 업로드 및 텍스트 추출이 완료되었습니다!")
                        st.write(f"추출된 텍스트 길이: {len(text_content):,} 문자")
                        
                        # 텍스트 미리보기
                        with st.expander("텍스트 미리보기"):
                            st.text_area("", text_content[:1000] + "...", height=200, disabled=True)
                    else:
                        st.error("PDF에서 텍스트를 추출할 수 없습니다.")
                        
                except Exception as e:
                    st.error(f"PDF 처리 중 오류가 발생했습니다: {str(e)}")

def show_chapter_analysis_page():
    st.header("📖 챕터 분석")
    
    if not st.session_state.current_novel:
        st.warning("먼저 소설 PDF를 업로드해주세요.")
        return
    
    novel = st.session_state.current_novel
    
    if not novel.get('chapters'):
        if st.button("챕터 분석 시작", type="primary"):
            with st.spinner("챕터를 분석하고 있습니다..."):
                try:
                    chapters = st.session_state.character_extractor.extract_chapters(novel['content'])
                    novel['chapters'] = chapters
                    st.session_state.data_manager.save_novel(novel)
                    st.success(f"{len(chapters)}개의 챕터가 분석되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"챕터 분석 중 오류가 발생했습니다: {str(e)}")
    else:
        st.success(f"총 {len(novel['chapters'])}개의 챕터가 분석되었습니다.")
        
        # 챕터 목록 표시
        for i, chapter in enumerate(novel['chapters'], 1):
            with st.expander(f"챕터 {i}: {chapter['title']}"):
                st.write(f"**요약:** {chapter['summary']}")
                st.write(f"**내용 길이:** {len(chapter['content']):,} 문자")

def show_character_management_page():
    st.header("👥 캐릭터 관리")
    
    if not st.session_state.current_novel:
        st.warning("먼저 소설 PDF를 업로드해주세요.")
        return
    
    novel = st.session_state.current_novel
    
    if not novel.get('chapters'):
        st.warning("먼저 챕터 분석을 완료해주세요.")
        return
    
    if not novel.get('characters'):
        if st.button("캐릭터 추출 시작", type="primary"):
            with st.spinner("캐릭터 정보를 추출하고 있습니다..."):
                try:
                    characters = st.session_state.character_extractor.extract_characters(
                        novel['content'], novel['chapters']
                    )
                    novel['characters'] = characters
                    st.session_state.data_manager.save_novel(novel)
                    st.success(f"{len(characters)}명의 캐릭터가 추출되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"캐릭터 추출 중 오류가 발생했습니다: {str(e)}")
    else:
        st.success(f"총 {len(novel['characters'])}명의 캐릭터가 추출되었습니다.")
        
        # 캐릭터 목록 표시
        for character in novel['characters']:
            with st.expander(f"🎭 {character['name']}"):
                st.write(f"**성격:** {character['personality']}")
                st.write(f"**배경:** {character['background']}")
                st.write(f"**역할:** {character['role']}")
                if character.get('relationships'):
                    st.write(f"**관계:** {character['relationships']}")

def show_character_chat_page():
    st.header("💬 캐릭터 대화")
    
    if not st.session_state.current_novel or not st.session_state.current_novel.get('characters'):
        st.warning("먼저 캐릭터 추출을 완료해주세요.")
        return
    
    characters = st.session_state.current_novel['characters']
    
    # 캐릭터 선택
    selected_character = st.selectbox(
        "대화할 캐릭터를 선택하세요",
        options=[char['name'] for char in characters],
        key="chat_character_select"
    )
    
    if selected_character:
        character_info = next(char for char in characters if char['name'] == selected_character)
        
        # 캐릭터 정보 표시
        with st.expander(f"{selected_character} 정보"):
            st.write(f"**성격:** {character_info['personality']}")
            st.write(f"**배경:** {character_info['background']}")
        
        # 대화 히스토리 초기화
        if selected_character not in st.session_state.chat_history:
            st.session_state.chat_history[selected_character] = []
        
        # 대화 히스토리 표시
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_history[selected_character]:
                if message['role'] == 'user':
                    st.write(f"**나:** {message['content']}")
                else:
                    st.write(f"**{selected_character}:** {message['content']}")
        
        # 메시지 입력
        user_message = st.text_input("메시지를 입력하세요:", key=f"chat_input_{selected_character}")
        
        if st.button("전송") and user_message:
            # 사용자 메시지 추가
            st.session_state.chat_history[selected_character].append({
                'role': 'user',
                'content': user_message
            })
            
            with st.spinner(f"{selected_character}이(가) 응답하고 있습니다..."):
                try:
                    response = st.session_state.chatbot.chat_with_character(
                        character_info,
                        user_message,
                        st.session_state.chat_history[selected_character]
                    )
                    
                    # 캐릭터 응답 추가
                    st.session_state.chat_history[selected_character].append({
                        'role': 'assistant',
                        'content': response
                    })
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"응답 생성 중 오류가 발생했습니다: {str(e)}")

def show_story_mode_page():
    st.header("🎮 스토리 모드")
    
    if not st.session_state.current_novel or not st.session_state.current_novel.get('characters'):
        st.warning("먼저 캐릭터 추출을 완료해주세요.")
        return
    
    novel = st.session_state.current_novel
    
    st.write("소설의 세계관에서 3자 시점으로 플레이할 수 있습니다.")
    
    # 스토리 모드 히스토리 표시
    story_container = st.container()
    with story_container:
        for message in st.session_state.story_mode_history:
            if message['role'] == 'user':
                st.write(f"**행동:** {message['content']}")
            else:
                st.write(f"**내레이션:** {message['content']}")
    
    # 행동 입력
    user_action = st.text_input("어떤 행동을 취하시겠습니까?", key="story_mode_input")
    
    if st.button("행동 실행") and user_action:
        # 사용자 행동 추가
        st.session_state.story_mode_history.append({
            'role': 'user',
            'content': user_action
        })
        
        with st.spinner("세계가 반응하고 있습니다..."):
            try:
                response = st.session_state.chatbot.story_mode_response(
                    novel,
                    user_action,
                    st.session_state.story_mode_history
                )
                
                # 내레이션 응답 추가
                st.session_state.story_mode_history.append({
                    'role': 'assistant',
                    'content': response
                })
                
                st.rerun()
                
            except Exception as e:
                st.error(f"스토리 진행 중 오류가 발생했습니다: {str(e)}")
    
    # 초기화 버튼
    if st.button("스토리 초기화"):
        st.session_state.story_mode_history = []
        st.rerun()

if __name__ == "__main__":
    main()

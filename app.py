import streamlit as st
import json
import os
from dotenv import load_dotenv
from file_processor import FileProcessor
from enhanced_character_extractor import EnhancedCharacterExtractor
from vector_db_manager import VectorDBManager
from chatbot import Chatbot
from data_manager import DataManager
from character_extractor import CharacterExtractor


load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="소설 캐릭터 챗봇",
    page_icon="📚",
    layout="wide"
)

# 세션 상태 초기화
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()

if 'file_processor' not in st.session_state:
    st.session_state.file_processor = FileProcessor()

if 'character_extractor' not in st.session_state:
    st.session_state.character_extractor = EnhancedCharacterExtractor()

if 'vector_db' not in st.session_state:
    st.session_state.vector_db = VectorDBManager()

if 'chatbot' not in st.session_state:
    st.session_state.chatbot = Chatbot()

if 'current_novel' not in st.session_state:
    st.session_state.current_novel = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}

if 'story_mode_history' not in st.session_state:
    st.session_state.story_mode_history = []

if "run_count" not in st.session_state:
    st.session_state.run_count = 0
st.session_state.run_count += 1

def main():
    st.title("📚 소설 캐릭터 AI 챗봇 시스템")
    
    # 사이드바 메뉴
    with st.sidebar:
        st.header("메뉴")
        # 프로젝트 관리 영역
        with st.expander("📁 프로젝트 관리", expanded=False):
            colp1, colp2 = st.columns(2)
            with colp1:
                if st.button("새 프로젝트 만들기"):
                    st.session_state.current_novel = None
                    st.session_state.chat_history = {}
                    st.session_state.story_mode_history = []
                    st.success("새 프로젝트가 초기화되었습니다.")
                if st.button("현재 프로젝트 저장"):
                    if st.session_state.current_novel:
                        saved_path = st.session_state.data_manager.export_novel_to_file(st.session_state.current_novel)
                        # 현재 프로젝트 저장-> 세션에 있는 소설을 파일로 저장
                        if saved_path:
                            st.success(f"프로젝트 저장됨: {saved_path}")
                            try:
                                # 벡터 DB도 함께 저장됨(이미 save_to_disk 호출된 상태가 이상적)
                                st.session_state.vector_db.save_to_disk(st.session_state.current_novel.get('title','Untitled'))
                                # 컴퓨터가 읽는 형태로 저장
                            except Exception:
                                pass
                        else:
                            st.error("프로젝트 저장에 실패했습니다.")
                    else:
                        st.warning("저장할 현재 프로젝트가 없습니다.")
            with colp2:
                projects = st.session_state.data_manager.list_project_files()
                # brings all projects from data manager
                if not projects:
                    st.info("저장된 프로젝트가 없습니다.")
                else:
                    options = [p["filename"] for p in projects]
                    labels = [f"{p['title']} ({p['filename']})" for p in projects]
                    selected_idx = st.selectbox(
                        "저장된 프로젝트 불러오기",
                        options=range(len(options)),
                        format_func=(lambda i: labels[i] if 0 <= i < len(labels) else ""),
                        key="project_select_box"
                    )
                    if st.button("불러오기", key="load_project_btn"):
                        selected_file = options[selected_idx]
                        data = st.session_state.data_manager.load_project_file(selected_file)
                        if data:
                            st.session_state.current_novel = data
                            #  불러온걸로 세션에 저장
                            try:
                                st.session_state.vector_db.load_from_disk(data.get('title','Untitled'))
                                # 컴퓨터 형식으로 된거 사용하게 불러오기

                            except Exception:
                                pass
                            st.success(f"프로젝트 '{data.get('title','Untitled')}'를 불러왔습니다.")
                        else:
                            st.error("프로젝트 로드에 실패했습니다.")

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
    st.header("📁 소설 파일 업로드")
    
    uploaded_file = st.file_uploader(
        "소설 파일을 업로드하세요",
        type=['pdf', 'txt'],
        help="소설이 포함된 PDF 또는 TXT 파일을 업로드하면 자동으로 분석됩니다."
    )
    
    if uploaded_file is not None:
        # 선택 후 파일 정보 표시
        st.info(f"파일명: {uploaded_file.name}")
        st.info(f"파일 크기: {uploaded_file.size:,} bytes")
        
        if st.button("파일 분석 시작", type="primary"):
            with st.spinner("파일을 분석하고 있습니다..."):
                try:
                    # 파일 텍스트 추출
                    text_content = st.session_state.file_processor.extract_text(uploaded_file)
                    # 디버깅용: 텍스트를 10만자로 제한
                    text_content = text_content[:100000]
                    
                    if text_content:
                        # 소설 정보 생성
                        file_name = uploaded_file.name
                        title = file_name.replace('.pdf', '').replace('.txt', '')
                        novel_info = {
                            'title': title,
                            'content': text_content,
                            'chapters': [],
                            'characters': []
                        }
                        
                        st.success("파일 텍스트 추출이 완료되었습니다!")
                        st.write(f"추출된 텍스트 길이: {len(text_content):,} 문자")
                        
                        # RAG 시스템 기반 향상된 분석 시작
                        progress_placeholder = st.empty()
                        
                        # 벡터 DB 초기화
                        if not st.session_state.vector_db.create_novel_collections(title):
                            st.error("벡터 데이터베이스 초기화에 실패했습니다.")
                            return
                        
                        # 챕터별 상세 분석
                        with st.spinner("챕터를 상세 분석하고 있습니다..."):
                            # 진행 표시와 함께, 각 챕터 완료 시 제목/길이도 출력
                            chapter_log = st.container()
                            def chapter_progress(current, total, message):
                                progress_placeholder.text(f"{message} ({current}/{total})")
                                # 완료 메시지 형식일 때 아래에 누적 출력
                                if message.startswith("완료:"):
                                    with chapter_log:
                                        st.write(message)
                            
                            try:
                                chapters = st.session_state.character_extractor.extract_chapters_enhanced(
                                    text_content, progress_callback=chapter_progress
                                )
                                novel_info['chapters'] = chapters
                                progress_placeholder.empty()
                                st.success(f"{len(chapters)}개의 챕터가 상세 분석되었습니다!")
                                
                                # 챕터를 벡터 DB에 저장
                                with st.spinner("챕터 정보를 벡터 데이터베이스에 저장하고 있습니다..."):
                                    for chapter in chapters:
                                        st.session_state.vector_db.add_chapter_to_db(chapter)
                                
                                # 캐릭터 추출 및 분석
                                with st.spinner("캐릭터 정보를 추출하고 있습니다..."):
                                    def character_progress(current, total, message):
                                        progress_placeholder.text(f"{message} ({current}/{total})")
                                    
                                    try:
                                        characters = st.session_state.character_extractor.extract_characters_from_chapters(
                                            chapters, progress_callback=character_progress
                                        )
                                        novel_info['characters'] = characters
                                        progress_placeholder.empty()
                                        
                                        # 캐릭터를 벡터 DB에 저장
                                        with st.spinner("캐릭터 정보를 벡터 데이터베이스에 저장하고 있습니다..."):
                                            for character in characters:
                                                st.session_state.vector_db.add_character_to_db(character)
                                        
                                        # 벡터 DB를 디스크에 저장
                                        st.session_state.vector_db.save_to_disk(title)
                                        
                                        # 데이터 매니저에 저장
                                        st.session_state.data_manager.save_novel(novel_info)
                                        st.session_state.current_novel = novel_info

                                        # 분석 완료 즉시 프로젝트 파일로 별도 저장
                                        saved_path = st.session_state.data_manager.export_novel_to_file(novel_info)
                                        if saved_path:
                                            st.caption(f"프로젝트 파일로 저장됨: {saved_path}")
                                        
                                        st.success(f"분석 완료! {len(characters)}명의 캐릭터가 추출되었습니다!")
                                        
                                        # 결과 요약
                                        st.info("✅ 파일 업로드 및 RAG 기반 전체 분석이 완료되었습니다. 이제 '캐릭터 대화' 메뉴에서 캐릭터들과 대화할 수 있습니다.")
                                        
                                        # 텍스트 미리보기
                                        with st.expander("텍스트 미리보기"):
                                            st.text_area("텍스트 내용", text_content[:1000] + "...", height=200, disabled=True)
                                        
                                        # 향상된 분석 결과 미리보기
                                        with st.expander("상세 분석 결과"):
                                            st.write(f"**챕터 수:** {len(chapters)}")
                                            st.write(f"**캐릭터 수:** {len(characters)}")
                                            
                                            # 챕터 요약
                                            st.subheader("챕터 요약")
                                            for chapter in chapters[:3]:  # 처음 3개만 표시
                                                st.write(f"**{chapter['title']}**")
                                                st.write(f"- 요약: {chapter['summary']}")
                                                st.write(f"- 키워드: {', '.join(chapter.get('keywords', []))}")
                                                st.write(f"- 등장인물: {', '.join(chapter.get('characters_mentioned', []))}")
                                                st.write("---")
                                            
                                            # 캐릭터 요약
                                            st.subheader("주요 캐릭터")
                                            for char in characters:
                                                st.write(f"**{char['name']}** ({char['role']})")
                                                st.write(f"- 성격: {char['personality'][:100]}...")
                                                st.write(f"- 등장 챕터: {len(char.get('chapters_appeared', []))}개")
                                                st.write("---")
                                                
                                    except Exception as e:
                                        st.error(f"캐릭터 추출 중 오류: {str(e)}")
                                        # 챕터 분석까지는 완료된 상태로 저장
                                        st.session_state.data_manager.save_novel(novel_info)
                                        st.session_state.current_novel = novel_info
                                        progress_placeholder.empty()
                                        
                            except Exception as e:
                                st.error(f"챕터 분석 중 오류: {str(e)}")
                                # 기본 정보만 저장
                                st.session_state.data_manager.save_novel(novel_info)
                                st.session_state.current_novel = novel_info
                                # 실패해도 현 상태를 프로젝트 파일로 백업 저장
                                try:
                                    st.session_state.data_manager.export_novel_to_file(novel_info)
                                except Exception:
                                    pass
                                progress_placeholder.empty()
                    else:
                        st.error("파일에서 텍스트를 추출할 수 없습니다.")
                        
                except Exception as e:
                    st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")

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
                    character_extractor = CharacterExtractor()  # make an instance

                    chapters = character_extractor.extract_chapters(novel['content'])

                    # chapters = st.session_state.character_extractor.extract_chapters(novel['content'])
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
                if character.get('speech_style'):
                    st.write(f"**말투 특징:** {character['speech_style']}")
                if character.get('quotes'):
                    st.write("**대표 어록:**")
                    for q in character.get('quotes', [])[:5]:
                        st.write(f"- {q}")
                if character.get('relationships'):
                    st.write(f"**관계:** {character['relationships']}")

def show_character_chat_page():
    st.header("💬 캐릭터 대화")
    
    if not st.session_state.current_novel or not st.session_state.current_novel.get('characters'):
        st.warning("먼저 캐릭터 추출을 완료해주세요.")
        return
    
    novel = st.session_state.current_novel
    chapters = novel.get('chapters', [])
    characters = novel.get('characters', [])
    
    # 대화 모드 선택
    chat_mode = st.radio(
        "대화 모드를 선택하세요:",
        ["전체 캐릭터 대화", "챕터별 캐릭터 대화", "RAG 검색 기반 대화"],
        key="chat_mode_select"
    )
    
    if chat_mode == "전체 캐릭터 대화":
        show_all_character_chat(characters)
    elif chat_mode == "챕터별 캐릭터 대화":
        show_chapter_character_chat(chapters, characters)
    else:
        show_rag_character_chat(characters)

def show_all_character_chat(characters):
    """전체 캐릭터와 대화하는 기능"""
    st.subheader("📝 전체 캐릭터 대화")
    
    # 캐릭터 선택
    selected_character = st.selectbox(
        "대화할 캐릭터를 선택하세요",
        options=[char['name'] for char in characters],
        key="all_chat_character_select"
    )
    
    if selected_character:
        character_info = next(char for char in characters if char['name'] == selected_character)
        show_character_conversation(selected_character, character_info, "all")

def show_chapter_character_chat(chapters, characters):
    """챕터별 캐릭터와 대화하는 기능"""
    st.subheader("📖 챕터별 캐릭터 대화")
    
    if not chapters:
        st.warning("챕터 정보가 없습니다. 먼저 챕터 분석을 완료해주세요.")
        return
    
    # 챕터 선택
    chapter_titles = [f"챕터 {ch['number']}: {ch['title']}" for ch in chapters]
    selected_chapter_idx = st.selectbox(
        "챕터를 선택하세요",
        options=range(len(chapters)),
        format_func=lambda x: chapter_titles[x],
        key="chapter_select"
    )
    
    selected_chapter = chapters[selected_chapter_idx]
    chapter_characters = selected_chapter.get('characters_mentioned', [])
    
    # 선택한 챕터 정보 표시
    with st.expander(f"📖 {selected_chapter['title']} 정보"):
        st.write(f"**요약:** {selected_chapter['summary']}")
        if chapter_characters:
            st.write(f"**등장 캐릭터:** {', '.join(chapter_characters)}")
        else:
            st.write("**등장 캐릭터:** 분석된 캐릭터가 없습니다.")
    
    if not chapter_characters:
        st.warning("이 챕터에는 분석된 캐릭터가 없습니다.")
        return
    
    # 챕터의 캐릭터 중에서 대화할 캐릭터 선택
    # 전체 캐릭터 리스트에서 챕터에 등장하는 캐릭터만 필터링
    available_characters = []
    for char in characters:
        if char['name'] in chapter_characters:
            available_characters.append(char)
    
    if not available_characters:
        st.warning("이 챕터에 등장하는 캐릭터의 상세 정보가 없습니다.")
        return
    
    selected_character_name = st.selectbox(
        "대화할 캐릭터를 선택하세요",
        options=[char['name'] for char in available_characters],
        key="chapter_chat_character_select"
    )
    
    if selected_character_name:
        character_info = next(char for char in available_characters if char['name'] == selected_character_name)
        
        # 챕터 맥락 정보 추가
        character_info_with_context = character_info.copy()
        character_info_with_context['current_chapter'] = selected_chapter
        
        show_character_conversation(
            selected_character_name, 
            character_info_with_context, 
            f"chapter_{selected_chapter['number']}"
        )

def show_character_conversation(character_name, character_info, context_key):
    """캐릭터와의 대화를 표시하고 관리하는 함수"""
    
    # 캐릭터 정보 표시
    with st.expander(f"🎭 {character_name} 정보"):
        st.write(f"**성격:** {character_info['personality']}")
        st.write(f"**배경:** {character_info['background']}")
        st.write(f"**역할:** {character_info['role']}")
        if character_info.get('relationships'):
            st.write(f"**관계:** {character_info['relationships']}")
        
        # 챕터 맥락 정보가 있는 경우
        if 'current_chapter' in character_info:
            chapter = character_info['current_chapter']
            st.write(f"**현재 챕터:** {chapter['title']}")
            st.write(f"**챕터 요약:** {chapter['summary']}")
    
    # 대화 키 생성 (전체 대화와 챕터별 대화를 구분)
    chat_key = f"{character_name}_{context_key}"
    
    # 대화 히스토리 초기화
    if chat_key not in st.session_state.chat_history:
        st.session_state.chat_history[chat_key] = []
    
    # 대화 히스토리 표시
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history[chat_key]:
            if message['role'] == 'user':
                st.write(f"**나:** {message['content']}")
            else:
                st.write(f"**{character_name}:** {message['content']}")
    
    # 메시지 입력
    user_message = st.text_input(
        "메시지를 입력하세요:", 
        key=f"chat_input_{chat_key}"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        send_button = st.button("전송", key=f"send_{chat_key}")
    with col2:
        if st.button("대화 초기화", key=f"clear_{chat_key}"):
            st.session_state.chat_history[chat_key] = []
            st.rerun()
    
    if send_button and user_message:
        # 사용자 메시지 추가
        st.session_state.chat_history[chat_key].append({
            'role': 'user',
            'content': user_message
        })
        
        with st.spinner(f"{character_name}이(가) 응답하고 있습니다..."):
            try:
                response = st.session_state.chatbot.chat_with_character(
                    character_info,
                    user_message,
                    st.session_state.chat_history[chat_key]
                )
                
                # 캐릭터 응답 추가
                st.session_state.chat_history[chat_key].append({
                    'role': 'assistant',
                    'content': response
                })
                
                st.rerun()
                
            except Exception as e:
                st.error(f"응답 생성 중 오류가 발생했습니다: {str(e)}")

def show_rag_character_chat(characters):
    """RAG 검색 기반 캐릭터 대화"""
    st.subheader("🔍 RAG 검색 기반 캐릭터 대화")
    st.info("소설 내용을 검색하여 더 정확한 대화를 할 수 있습니다.")
    
    # 캐릭터 선택
    selected_character = st.selectbox(
        "대화할 캐릭터를 선택하세요",
        options=[char['name'] for char in characters],
        key="rag_chat_character_select"
    )
    
    if selected_character:
        character_info = next(char for char in characters if char['name'] == selected_character)
        
        # 검색 기능
        st.subheader("📚 관련 내용 검색")
        search_query = st.text_input(
            "관련 내용을 검색하세요 (선택사항):",
            placeholder="예: 로맨스, 갈등, 친구 관계 등",
            key="rag_search_input"
        )
        
        search_results = []
        if search_query:
            with st.spinner("관련 내용을 검색하고 있습니다..."):
                # 챕터 검색
                chapter_results = st.session_state.vector_db.search_chapters(search_query, n_results=3)
                if chapter_results:
                    st.write("**관련 챕터:**")
                    for chapter in chapter_results:
                        st.write(f"- {chapter['title']}: {chapter['summary']}")
                        search_results.append(f"챕터 '{chapter['title']}': {chapter['summary']}")
        
        # 캐릭터 정보에 검색 결과 추가
        enhanced_character_info = character_info.copy()
        if search_results:
            enhanced_character_info['search_context'] = search_results
        
        show_character_conversation(
            selected_character, 
            enhanced_character_info, 
            "rag_enhanced"
        )

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
        
        placeholder = st.empty()
        try:
            # 스트리밍 출력
            chunks = st.session_state.chatbot.story_mode_response_stream(
                novel,
                user_action,
                st.session_state.story_mode_history
            )
            accumulated = ""
            for piece in chunks:
                accumulated += piece
                # 스트리밍 중 사용자가 다른 입력을 하거나 세션이 변경되면 종료될 수 있으므로 안전 가드
                try:
                    placeholder.markdown(accumulated)
                except Exception:
                    break
            # 스트리밍 완료 후 대화 기록에 저장
            st.session_state.story_mode_history.append({
                'role': 'assistant',
                'content': accumulated
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

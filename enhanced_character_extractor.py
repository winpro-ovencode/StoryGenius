import json
import os
import re
from openai import OpenAI
from typing import List, Dict, Any
import streamlit as st

class EnhancedCharacterExtractor:
    """향상된 캐릭터 및 챕터 분석 클래스 (RAG 기반)"""

    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o"

    def extract_chapters_enhanced(self, text_content: str, progress_callback=None) -> List[Dict[str, Any]]:
        """
        소설 텍스트를 챕터별로 분석하여 상세 정보를 추출합니다.
        
        Args:
            text_content (str): 소설 전체 텍스트
            progress_callback: 진행률 콜백 함수
            
        Returns:
            list: 향상된 챕터 정보 리스트
        """
        try:
            # 먼저 챕터 구분
            chapters = self._auto_detect_chapters(text_content)
            
            if not chapters:
                # 자동 구분이 실패하면 텍스트 길이로 임의 분할
                chapters = self._split_by_length(text_content)
            
            # 각 챕터를 상세 분석
            analyzed_chapters = []
            total_chapters = len(chapters)
            
            for i, chapter_content in enumerate(chapters, 1):
                if progress_callback:
                    progress_callback(i, total_chapters, f"챕터 {i} 분석 중...")
                
                chapter_info = self._analyze_chapter_enhanced(chapter_content, i)
                analyzed_chapters.append(chapter_info)
                
                # 너무 많은 API 호출 방지를 위한 잠시 대기
                if i % 3 == 0:  # 3개마다 잠시 대기
                    import time
                    time.sleep(1)
            
            return analyzed_chapters

        except Exception as e:
            raise Exception(f"향상된 챕터 추출 실패: {str(e)}")

    def _auto_detect_chapters(self, text: str) -> List[str]:
        """텍스트에서 자동으로 챕터를 감지합니다."""
        # 챕터 구분 패턴들
        chapter_patterns = [
            r'제\s*\d+\s*장',  # 제1장, 제 1 장
            r'Chapter\s*\d+',  # Chapter 1
            r'챕터\s*\d+',  # 챕터1, 챕터 1
            r'\d+\s*장',  # 1장
            r'\d+\.',  # 1.
            r'CHAPTER\s*\d+',  # CHAPTER 1
        ]

        chapters = []
        chapter_splits = []

        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if len(matches) > 1:  # 2개 이상의 챕터가 있을 때만
                chapter_splits = [(m.start(), m.end()) for m in matches]
                break

        if chapter_splits:
            for i, (start, end) in enumerate(chapter_splits):
                if i == len(chapter_splits) - 1:
                    # 마지막 챕터
                    chapter_text = text[start:]
                else:
                    # 다음 챕터 시작점까지
                    next_start = chapter_splits[i + 1][0]
                    chapter_text = text[start:next_start]

                chapters.append(chapter_text.strip())

        return chapters

    def _split_by_length(self, text: str, max_length: int = 8000) -> List[str]:
        """텍스트를 길이로 분할합니다."""
        chapters = []
        current_pos = 0

        while current_pos < len(text):
            end_pos = min(current_pos + max_length, len(text))

            # 문장 끝에서 자르기 시도
            if end_pos < len(text):
                # 마지막 문장 끝 찾기
                sentence_endings = ['.', '!', '?', '。', '！', '？']
                best_end = current_pos
                
                for ending in sentence_endings:
                    last_pos = text.rfind(ending, current_pos, end_pos)
                    if last_pos > best_end:
                        best_end = last_pos + 1
                
                if best_end > current_pos:
                    end_pos = best_end

            chapter_text = text[current_pos:end_pos].strip()
            if chapter_text:
                chapters.append(chapter_text)

            current_pos = end_pos

        return chapters

    def _analyze_chapter_enhanced(self, chapter_content: str, chapter_number: int) -> Dict[str, Any]:
        """
        개별 챕터를 상세 분석합니다.
        """
        try:
            # 챕터 내용을 적절한 길이로 제한
            content_sample = chapter_content[:3000]
            
            prompt = f"""
            다음은 소설의 챕터 {chapter_number} 내용입니다. 이 챕터를 자세히 분석해서 다음 정보를 JSON 형태로 제공해주세요:

            1. title: 챕터 제목 (적절한 제목이 없으면 내용을 바탕으로 생성)
            2. summary: 챕터 요약 (3-4문장으로 상세하게)
            3. keywords: 주요 키워드들 (배열 형태, 5-8개)
            4. characters_mentioned: 언급된 캐릭터들 (배열 형태)
            5. plot_progression: 스토리 전개 과정 (2-3문장)
            6. key_events: 주요 사건들 (배열 형태, 3-5개)
            7. emotional_tone: 감정적 톤 (예: "긴장감", "로맨틱", "슬픔" 등)
            8. setting: 배경 설정 (장소, 시간 등)

            챕터 내용:
            {content_sample}

            JSON 형태로 응답해주세요.
            """

            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "system",
                    "content": "당신은 소설 분석 전문가입니다. 한국어 소설을 정확히 분석하고 구조화된 JSON 형태로 응답합니다."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                response_format={"type": "json_object"},
                max_tokens=1500,
                temperature=0.3
            )

            content = response.choices[0].message.content
            if content:
                analysis = json.loads(content)
            else:
                analysis = {}

            return {
                'number': chapter_number,
                'title': analysis.get('title', f'챕터 {chapter_number}'),
                'summary': analysis.get('summary', ''),
                'keywords': analysis.get('keywords', []),
                'characters_mentioned': analysis.get('characters_mentioned', []),
                'plot_progression': analysis.get('plot_progression', ''),
                'key_events': analysis.get('key_events', []),
                'emotional_tone': analysis.get('emotional_tone', ''),
                'setting': analysis.get('setting', ''),
                'content': chapter_content  # 전체 내용 저장
            }

        except Exception as e:
            # 분석 실패시 기본 정보 반환
            return {
                'number': chapter_number,
                'title': f'챕터 {chapter_number}',
                'summary': '챕터 분석을 완료하지 못했습니다.',
                'keywords': [],
                'characters_mentioned': [],
                'plot_progression': '',
                'key_events': [],
                'emotional_tone': '',
                'setting': '',
                'content': chapter_content
            }

    def extract_characters_from_chapters(self, chapters: List[Dict], progress_callback=None) -> List[Dict[str, Any]]:
        """
        챕터 정보를 바탕으로 캐릭터를 추출합니다.
        """
        try:
            # 모든 챕터에서 언급된 캐릭터 수집
            all_characters = set()
            character_appearances = {}
            
            for chapter in chapters:
                mentioned = chapter.get('characters_mentioned', [])
                for char in mentioned:
                    all_characters.add(char)
                    if char not in character_appearances:
                        character_appearances[char] = []
                    character_appearances[char].append(chapter['number'])
            
            # 주요 캐릭터만 필터링 (2회 이상 등장)
            main_characters = [char for char in all_characters 
                             if len(character_appearances.get(char, [])) >= 2]
            
            # 너무 많으면 상위 10명으로 제한
            if len(main_characters) > 10:
                # 등장 빈도순으로 정렬
                main_characters = sorted(main_characters, 
                                       key=lambda x: len(character_appearances.get(x, [])), 
                                       reverse=True)[:10]
            
            # 각 캐릭터 상세 분석
            detailed_characters = []
            total_chars = len(main_characters)
            
            for i, character_name in enumerate(main_characters, 1):
                if progress_callback:
                    progress_callback(i, total_chars, f"캐릭터 '{character_name}' 분석 중...")
                
                character_info = self._analyze_character_enhanced(
                    character_name, chapters, character_appearances[character_name]
                )
                detailed_characters.append(character_info)
                
                # API 호출 제한을 위한 대기
                if i % 2 == 0:
                    import time
                    time.sleep(1)
            
            return detailed_characters

        except Exception as e:
            raise Exception(f"캐릭터 추출 실패: {str(e)}")

    def _analyze_character_enhanced(self, character_name: str, chapters: List[Dict], appeared_chapters: List[int]) -> Dict[str, Any]:
        """
        개별 캐릭터를 상세 분석합니다.
        """
        try:
            # 캐릭터가 등장하는 챕터들의 정보 수집
            relevant_info = []
            for chapter_num in appeared_chapters:
                chapter = next((ch for ch in chapters if ch['number'] == chapter_num), None)
                if chapter:
                    relevant_info.append({
                        'chapter': chapter_num,
                        'title': chapter['title'],
                        'summary': chapter['summary'],
                        'events': chapter.get('key_events', [])
                    })
            
            # 분석용 컨텍스트 구성
            context_text = f"캐릭터 '{character_name}'가 등장하는 챕터들:\n"
            for info in relevant_info[:5]:  # 최대 5개 챕터만
                context_text += f"- 챕터 {info['chapter']}: {info['title']}\n"
                context_text += f"  요약: {info['summary']}\n"
                context_text += f"  주요 사건: {', '.join(info['events'])}\n\n"

            prompt = f"""
            다음은 소설에서 '{character_name}' 캐릭터가 등장하는 챕터들의 정보입니다.
            이 정보를 바탕으로 캐릭터에 대한 상세 정보를 JSON 형태로 제공해주세요:

            1. name: 캐릭터 이름
            2. personality: 성격 특성 (구체적이고 상세하게)
            3. background: 배경 설정 (직업, 출신, 과거사 등)
            4. role: 소설에서의 역할 (주인공, 조연, 악역, 조력자 등)
            5. relationships: 다른 캐릭터와의 관계
            6. key_traits: 주요 특징들 (배열 형태, 5-7개)
            7. description: 외모나 특징 묘사
            8. character_arc: 캐릭터의 성장이나 변화 과정
            9. motivations: 동기와 목표
            10. chapters_appeared: 등장 챕터 번호들 (배열 형태)

            컨텍스트:
            {context_text}

            JSON 형태로 응답해주세요.
            """

            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "system",
                    "content": "당신은 소설 캐릭터 분석 전문가입니다. 주어진 정보에서 캐릭터의 특성을 정확히 파악하고 구조화합니다."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                response_format={"type": "json_object"},
                max_tokens=1500,
                temperature=0.3
            )

            content = response.choices[0].message.content
            if content:
                character_info = json.loads(content)
            else:
                character_info = {}

            return {
                'name': character_name,
                'personality': character_info.get('personality', '분석 정보 없음'),
                'background': character_info.get('background', '분석 정보 없음'),
                'role': character_info.get('role', '등장인물'),
                'relationships': character_info.get('relationships', ''),
                'key_traits': character_info.get('key_traits', []),
                'description': character_info.get('description', ''),
                'character_arc': character_info.get('character_arc', ''),
                'motivations': character_info.get('motivations', ''),
                'chapters_appeared': appeared_chapters
            }

        except Exception as e:
            # 분석 실패시 기본 정보 반환
            return {
                'name': character_name,
                'personality': '성격 분석을 완료하지 못했습니다.',
                'background': '배경 정보가 없습니다.',
                'role': '등장인물',
                'relationships': '',
                'key_traits': [],
                'description': '',
                'character_arc': '',
                'motivations': '',
                'chapters_appeared': appeared_chapters
            }
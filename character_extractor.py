import json
import os
import re
from openai import OpenAI

class CharacterExtractor:
    """소설에서 챕터와 캐릭터 정보를 추출하는 클래스"""
    
    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o"
    
    def extract_chapters(self, text_content):
        """
        소설 텍스트에서 챕터를 추출하고 분석합니다.
        
        Args:
            text_content (str): 소설 전체 텍스트
            
        Returns:
            list: 챕터 정보 리스트
        """
        try:
            # 먼저 자동으로 챕터 구분 시도
            chapters = self._auto_detect_chapters(text_content)
            
            if not chapters:
                # 자동 구분이 실패하면 텍스트 길이로 임의 분할
                chapters = self._split_by_length(text_content)
            
            # 각 챕터 분석
            analyzed_chapters = []
            for i, chapter_content in enumerate(chapters, 1):
                chapter_info = self._analyze_chapter(chapter_content, i)
                analyzed_chapters.append(chapter_info)
            
            return analyzed_chapters
            
        except Exception as e:
            raise Exception(f"챕터 추출 실패: {str(e)}")
    
    def _auto_detect_chapters(self, text):
        """
        텍스트에서 자동으로 챕터를 감지합니다.
        
        Args:
            text (str): 소설 텍스트
            
        Returns:
            list: 챕터 텍스트 리스트
        """
        # 챕터 구분 패턴들
        chapter_patterns = [
            r'제\s*\d+\s*장',  # 제1장, 제 1 장
            r'Chapter\s*\d+',  # Chapter 1
            r'챕터\s*\d+',     # 챕터1, 챕터 1
            r'\d+\s*장',       # 1장
            r'\d+\.',          # 1.
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
    
    def _split_by_length(self, text, max_length=5000):
        """
        텍스트를 길이로 분할합니다.
        
        Args:
            text (str): 분할할 텍스트
            max_length (int): 최대 길이
            
        Returns:
            list: 분할된 텍스트 리스트
        """
        chapters = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + max_length, len(text))
            
            # 문장 끝에서 자르기 시도
            if end_pos < len(text):
                # 마지막 문장 끝 찾기
                last_period = text.rfind('.', current_pos, end_pos)
                last_exclamation = text.rfind('!', current_pos, end_pos)
                last_question = text.rfind('?', current_pos, end_pos)
                
                sentence_end = max(last_period, last_exclamation, last_question)
                if sentence_end > current_pos:
                    end_pos = sentence_end + 1
            
            chapter_text = text[current_pos:end_pos].strip()
            if chapter_text:
                chapters.append(chapter_text)
            
            current_pos = end_pos
        
        return chapters
    
    def _analyze_chapter(self, chapter_content, chapter_number):
        """
        개별 챕터를 분석합니다.
        
        Args:
            chapter_content (str): 챕터 내용
            chapter_number (int): 챕터 번호
            
        Returns:
            dict: 챕터 분석 결과
        """
        try:
            prompt = f"""
            다음은 소설의 챕터 {chapter_number} 내용입니다. 이 챕터를 분석해서 다음 정보를 JSON 형태로 제공해주세요:

            1. title: 챕터 제목 (적절한 제목이 없으면 내용을 바탕으로 생성)
            2. summary: 챕터 요약 (2-3문장)
            3. key_events: 주요 사건들 (배열 형태)
            4. characters_mentioned: 언급된 캐릭터들 (배열 형태)

            챕터 내용:
            {chapter_content[:2000]}...

            JSON 형태로 응답해주세요.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 소설 분석 전문가입니다. 한국어 소설을 정확히 분석하고 JSON 형태로 응답합니다."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
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
                'key_events': analysis.get('key_events', []),
                'characters_mentioned': analysis.get('characters_mentioned', []),
                'content': chapter_content
            }
            
        except Exception as e:
            # 분석 실패시 기본 정보 반환
            return {
                'number': chapter_number,
                'title': f'챕터 {chapter_number}',
                'summary': '챕터 분석을 완료하지 못했습니다.',
                'key_events': [],
                'characters_mentioned': [],
                'content': chapter_content
            }
    
    def extract_characters(self, text_content, chapters):
        """
        소설에서 주요 캐릭터들을 추출합니다.
        
        Args:
            text_content (str): 소설 전체 텍스트
            chapters (list): 챕터 정보 리스트
            
        Returns:
            list: 캐릭터 정보 리스트
        """
        try:
            # 전체 텍스트에서 캐릭터 추출
            characters = self._extract_main_characters(text_content, chapters)
            
            # 각 캐릭터에 대한 상세 정보 추출
            detailed_characters = []
            for character_name in characters:
                character_info = self._analyze_character(character_name, text_content, chapters)
                detailed_characters.append(character_info)
            
            return detailed_characters
            
        except Exception as e:
            raise Exception(f"캐릭터 추출 실패: {str(e)}")
    
    def _extract_main_characters(self, text_content, chapters):
        """
        주요 캐릭터 이름을 추출합니다.
        
        Args:
            text_content (str): 소설 전체 텍스트
            chapters (list): 챕터 정보
            
        Returns:
            list: 주요 캐릭터 이름 리스트
        """
        try:
            # 챕터들에서 언급된 모든 캐릭터 수집
            all_mentioned = []
            for chapter in chapters:
                all_mentioned.extend(chapter.get('characters_mentioned', []))
            
            # 텍스트 샘플 (처음 3000자)
            text_sample = text_content[:3000]
            
            prompt = f"""
            다음은 소설의 텍스트와 각 챕터에서 언급된 캐릭터들입니다. 
            이 소설의 주요 캐릭터 5-10명의 이름을 추출해주세요.

            텍스트 샘플:
            {text_sample}

            챕터별 언급 캐릭터:
            {', '.join(set(all_mentioned))}

            주요 캐릭터들의 이름만을 JSON 배열 형태로 반환해주세요.
            예: {{"characters": ["홍길동", "김철수", "이영희"]}}
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 소설 분석 전문가입니다. 텍스트에서 주요 캐릭터를 정확히 식별합니다."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
            else:
                result = {}
            return result.get('characters', [])
            
        except Exception as e:
            # 실패시 챕터에서 언급된 캐릭터들 중 상위 5개 반환
            character_count = {}
            for chapter in chapters:
                for char in chapter.get('characters_mentioned', []):
                    character_count[char] = character_count.get(char, 0) + 1
            
            # 빈도순으로 정렬해서 상위 5개 반환
            sorted_chars = sorted(character_count.items(), key=lambda x: x[1], reverse=True)
            return [char[0] for char in sorted_chars[:5]]
    
    def _analyze_character(self, character_name, text_content, chapters):
        """
        개별 캐릭터를 상세 분석합니다.
        
        Args:
            character_name (str): 캐릭터 이름
            text_content (str): 소설 전체 텍스트
            chapters (list): 챕터 정보
            
        Returns:
            dict: 캐릭터 상세 정보
        """
        try:
            # 해당 캐릭터가 언급된 부분들 찾기
            character_contexts = self._find_character_contexts(character_name, text_content)
            context_sample = '\n'.join(character_contexts[:5])  # 상위 5개 컨텍스트
            
            prompt = f"""
            다음은 소설에서 '{character_name}' 캐릭터가 언급된 부분들입니다.
            이 정보를 바탕으로 캐릭터에 대한 상세 정보를 JSON 형태로 제공해주세요:

            1. name: 캐릭터 이름
            2. personality: 성격 특성 (구체적으로)
            3. background: 배경 설정 (직업, 출신 등)
            4. role: 소설에서의 역할 (주인공, 조연, 악역 등)
            5. relationships: 다른 캐릭터와의 관계
            6. key_traits: 주요 특징들 (배열 형태)
            7. description: 외모나 특징 묘사

            컨텍스트:
            {context_sample}

            JSON 형태로 응답해주세요.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 소설 캐릭터 분석 전문가입니다. 주어진 텍스트에서 캐릭터의 특성을 정확히 파악합니다."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
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
                'contexts': character_contexts[:10]  # 컨텍스트 상위 10개 저장
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
                'contexts': []
            }
    
    def _find_character_contexts(self, character_name, text, context_length=200):
        """
        텍스트에서 특정 캐릭터가 언급된 문맥들을 찾습니다.
        
        Args:
            character_name (str): 찾을 캐릭터 이름
            text (str): 검색할 텍스트
            context_length (int): 문맥 길이
            
        Returns:
            list: 캐릭터가 언급된 문맥들
        """
        contexts = []
        start = 0
        
        while True:
            # 캐릭터 이름 찾기
            pos = text.find(character_name, start)
            if pos == -1:
                break
            
            # 문맥 추출 (앞뒤로 context_length만큼)
            context_start = max(0, pos - context_length // 2)
            context_end = min(len(text), pos + len(character_name) + context_length // 2)
            
            context = text[context_start:context_end].strip()
            if context and context not in contexts:
                contexts.append(context)
            
            start = pos + len(character_name)
            
            # 너무 많은 컨텍스트 수집 방지
            if len(contexts) >= 20:
                break
        
        return contexts

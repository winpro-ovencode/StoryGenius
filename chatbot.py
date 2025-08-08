import json
import os
from openai import OpenAI

class Chatbot:
    """캐릭터와의 대화 및 스토리 모드를 처리하는 클래스"""
    
    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o"
    
    def chat_with_character(self, character_info, user_message, chat_history):
        """
        특정 캐릭터와 대화합니다.
        
        Args:
            character_info (dict): 캐릭터 정보
            user_message (str): 사용자 메시지
            chat_history (list): 대화 히스토리
            
        Returns:
            str: 캐릭터의 응답
        """
        try:
            # 캐릭터 정보를 바탕으로 시스템 프롬프트 생성
            system_prompt = self._create_character_system_prompt(character_info)
            
            # 대화 히스토리를 OpenAI 형식으로 변환
            messages = [{"role": "system", "content": system_prompt}]
            
            # 최근 10개의 대화만 포함 (토큰 제한)
            recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
            
            for msg in recent_history[:-1]:  # 마지막 메시지 제외 (이미 user_message로 처리됨)
                if msg['role'] in ['user', 'assistant']:
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
            
            # 현재 사용자 메시지 추가
            messages.append({
                "role": "user", 
                "content": user_message
            })
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=500,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"죄송합니다. 응답을 생성하는 중에 오류가 발생했습니다: {str(e)}"
    
    def _create_character_system_prompt(self, character_info):
        """
        캐릭터 정보를 바탕으로 시스템 프롬프트를 생성합니다.
        
        Args:
            character_info (dict): 캐릭터 정보
            
        Returns:
            str: 시스템 프롬프트
        """
        prompt = f"""당신은 소설 속 캐릭터 '{character_info['name']}'입니다. 다음 정보를 바탕으로 캐릭터의 성격과 말투를 일관되게 유지하며 대화해주세요:

캐릭터 정보:
- 이름: {character_info['name']}
- 성격: {character_info['personality']}
- 배경: {character_info['background']}
- 역할: {character_info['role']}"""

        if character_info.get('relationships'):
            prompt += f"\n- 인간관계: {character_info['relationships']}"
        
        if character_info.get('key_traits'):
            prompt += f"\n- 주요 특징: {', '.join(character_info['key_traits'])}"
        
        if character_info.get('description'):
            prompt += f"\n- 외모/특징: {character_info['description']}"
        
        prompt += """

대화 규칙:
1. 항상 이 캐릭터의 성격과 배경에 맞게 응답하세요
2. 캐릭터의 말투와 어조를 일관되게 유지하세요
3. 소설의 세계관을 벗어나지 않는 범위에서 대화하세요
4. 자연스럽고 매력적인 대화를 만들어주세요
5. 한국어로 응답하세요"""

        return prompt
    
    def story_mode_response(self, novel_info, user_action, story_history):
        """
        스토리 모드에서 사용자 행동에 대한 세계관 반응을 생성합니다.
        
        Args:
            novel_info (dict): 소설 정보
            user_action (str): 사용자 행동
            story_history (list): 스토리 진행 히스토리
            
        Returns:
            str: 세계관의 반응
        """
        try:
            # 소설 정보를 바탕으로 시스템 프롬프트 생성
            system_prompt = self._create_story_system_prompt(novel_info)
            
            # 스토리 히스토리를 OpenAI 형식으로 변환
            messages = [{"role": "system", "content": system_prompt}]
            
            # 최근 20개의 상호작용만 포함
            recent_history = story_history[-20:] if len(story_history) > 20 else story_history
            
            for msg in recent_history[:-1]:  # 마지막 메시지 제외
                if msg['role'] == 'user':
                    messages.append({
                        "role": "user",
                        "content": f"행동: {msg['content']}"
                    })
                elif msg['role'] == 'assistant':
                    messages.append({
                        "role": "assistant",
                        "content": msg['content']
                    })
            
            # 현재 사용자 행동 추가
            messages.append({
                "role": "user",
                "content": f"행동: {user_action}"
            })
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=600,
                temperature=0.9
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"세계가 응답하지 않습니다... (오류: {str(e)})"
    
    def _create_story_system_prompt(self, novel_info):
        """
        스토리 모드용 시스템 프롬프트를 생성합니다.
        
        Args:
            novel_info (dict): 소설 정보
            
        Returns:
            str: 시스템 프롬프트
        """
        # 캐릭터 정보 요약
        characters_summary = ""
        if novel_info.get('characters'):
            characters_summary = "\n주요 등장인물:\n"
            for char in novel_info['characters'][:5]:  # 상위 5명만
                characters_summary += f"- {char['name']}: {char.get('role', '등장인물')}\n"
        
        # 챕터 정보 요약
        world_summary = ""
        if novel_info.get('chapters'):
            world_summary = "\n세계관 정보:\n"
            for i, chapter in enumerate(novel_info['chapters'][:3], 1):  # 처음 3챕터
                world_summary += f"- 챕터 {i}: {chapter.get('summary', '')}\n"
        
        prompt = f"""당신은 '{novel_info['title']}' 소설의 세계관을 관리하는 내레이터입니다. 
사용자가 이 세계에서 3자 시점의 캐릭터로 행동할 때, 세계가 어떻게 반응하는지 묘사해주세요.

{characters_summary}

{world_summary}

내레이션 규칙:
1. 사용자의 행동에 대해 세계와 등장인물들이 어떻게 반응하는지 묘사하세요
2. 소설의 분위기와 톤을 일관되게 유지하세요
3. 등장인물들의 성격에 맞는 반응을 만들어주세요
4. 흥미롭고 몰입감 있는 스토리를 전개하세요
5. 사용자가 선택할 수 있는 다음 행동을 암시하세요
6. 한국어로 자연스럽게 서술하세요
7. 3자 시점에서 "당신은...", "그대는..." 식으로 서술하세요"""

        return prompt
    
    def generate_character_greeting(self, character_info):
        """
        캐릭터의 첫 인사말을 생성합니다.
        
        Args:
            character_info (dict): 캐릭터 정보
            
        Returns:
            str: 캐릭터의 인사말
        """
        try:
            system_prompt = self._create_character_system_prompt(character_info)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "안녕하세요! 처음 뵙겠습니다. 자기소개를 해주세요."}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=300,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"안녕하세요, 저는 {character_info['name']}입니다. 만나서 반갑습니다!"
    
    def generate_story_opening(self, novel_info):
        """
        스토리 모드의 오프닝을 생성합니다.
        
        Args:
            novel_info (dict): 소설 정보
            
        Returns:
            str: 스토리 오프닝
        """
        try:
            system_prompt = self._create_story_system_prompt(novel_info)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "이 세계에 처음 발을 들여놓았습니다. 주변 상황을 묘사해주세요."}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=400,
                temperature=0.9
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"{novel_info['title']}의 세계에 오신 것을 환영합니다. 모험이 시작됩니다..."

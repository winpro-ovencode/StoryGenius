import json
import os
from datetime import datetime

class DataManager:
    """데이터 저장 및 관리를 담당하는 클래스"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.novels_file = os.path.join(data_dir, "novels.json")
        self.characters_file = os.path.join(data_dir, "characters.json")
        
        # 데이터 디렉토리 생성
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # 데이터 파일 초기화
        self._init_data_files()
    
    def _init_data_files(self):
        """데이터 파일들을 초기화합니다."""
        if not os.path.exists(self.novels_file):
            with open(self.novels_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.characters_file):
            with open(self.characters_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def save_novel(self, novel_info):
        """
        소설 정보를 저장합니다.
        
        Args:
            novel_info (dict): 저장할 소설 정보
        """
        try:
            # 기존 소설 데이터 로드
            novels = self.load_novels()
            
            # 동일한 제목의 소설이 있는지 확인
            existing_index = -1
            for i, novel in enumerate(novels):
                if novel.get('title') == novel_info.get('title'):
                    existing_index = i
                    break
            
            # 타임스탬프 추가
            novel_info['updated_at'] = datetime.now().isoformat()
            if existing_index == -1:
                novel_info['created_at'] = novel_info['updated_at']
            
            # 새 소설이면 추가, 기존 소설이면 업데이트
            if existing_index == -1:
                novels.append(novel_info)
            else:
                novels[existing_index] = novel_info
            
            # 파일에 저장
            with open(self.novels_file, 'w', encoding='utf-8') as f:
                json.dump(novels, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"소설 저장 실패: {str(e)}")
            return False
    
    def load_novels(self):
        """
        저장된 소설 목록을 로드합니다.
        
        Returns:
            list: 소설 정보 리스트
        """
        try:
            with open(self.novels_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"소설 로드 실패: {str(e)}")
            return []
    
    def get_novel_by_title(self, title):
        """
        제목으로 소설을 찾습니다.
        
        Args:
            title (str): 찾을 소설 제목
            
        Returns:
            dict or None: 소설 정보 또는 None
        """
        novels = self.load_novels()
        for novel in novels:
            if novel.get('title') == title:
                return novel
        return None
    
    def delete_novel(self, title):
        """
        소설을 삭제합니다.
        
        Args:
            title (str): 삭제할 소설 제목
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            novels = self.load_novels()
            novels = [novel for novel in novels if novel.get('title') != title]
            
            with open(self.novels_file, 'w', encoding='utf-8') as f:
                json.dump(novels, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"소설 삭제 실패: {str(e)}")
            return False
    
    def save_characters(self, characters, novel_title):
        """
        캐릭터 정보를 저장합니다.
        
        Args:
            characters (list): 캐릭터 정보 리스트
            novel_title (str): 소속 소설 제목
        """
        try:
            # 기존 캐릭터 데이터 로드
            all_characters = self.load_all_characters()
            
            # 해당 소설의 기존 캐릭터 제거
            all_characters = [char for char in all_characters 
                            if char.get('novel_title') != novel_title]
            
            # 새 캐릭터들에 소설 정보 추가
            for character in characters:
                character['novel_title'] = novel_title
                character['updated_at'] = datetime.now().isoformat()
            
            # 새 캐릭터들 추가
            all_characters.extend(characters)
            
            # 파일에 저장
            with open(self.characters_file, 'w', encoding='utf-8') as f:
                json.dump(all_characters, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"캐릭터 저장 실패: {str(e)}")
            return False
    
    def load_all_characters(self):
        """
        모든 캐릭터 정보를 로드합니다.
        
        Returns:
            list: 전체 캐릭터 정보 리스트
        """
        try:
            with open(self.characters_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"캐릭터 로드 실패: {str(e)}")
            return []
    
    def get_characters_by_novel(self, novel_title):
        """
        특정 소설의 캐릭터들을 가져옵니다.
        
        Args:
            novel_title (str): 소설 제목
            
        Returns:
            list: 해당 소설의 캐릭터 리스트
        """
        all_characters = self.load_all_characters()
        return [char for char in all_characters 
                if char.get('novel_title') == novel_title]
    
    def get_character_by_name(self, character_name, novel_title=None):
        """
        이름으로 캐릭터를 찾습니다.
        
        Args:
            character_name (str): 캐릭터 이름
            novel_title (str, optional): 소설 제목 (지정시 해당 소설에서만 검색)
            
        Returns:
            dict or None: 캐릭터 정보 또는 None
        """
        all_characters = self.load_all_characters()
        
        for character in all_characters:
            if character.get('name') == character_name:
                if novel_title is None or character.get('novel_title') == novel_title:
                    return character
        
        return None
    
    def get_storage_info(self):
        """
        저장소 정보를 반환합니다.
        
        Returns:
            dict: 저장소 통계 정보
        """
        novels = self.load_novels()
        characters = self.load_all_characters()
        
        total_novels = len(novels)
        total_characters = len(characters)
        
        # 소설별 캐릭터 수 계산
        novel_character_count = {}
        for character in characters:
            novel_title = character.get('novel_title', 'Unknown')
            novel_character_count[novel_title] = novel_character_count.get(novel_title, 0) + 1
        
        return {
            'total_novels': total_novels,
            'total_characters': total_characters,
            'novels': [
                {
                    'title': novel.get('title', 'Untitled'),
                    'characters_count': novel_character_count.get(novel.get('title'), 0),
                    'chapters_count': len(novel.get('chapters', [])),
                    'created_at': novel.get('created_at'),
                    'updated_at': novel.get('updated_at')
                }
                for novel in novels
            ]
        }
    
    def export_data(self, novel_title=None):
        """
        데이터를 내보냅니다.
        
        Args:
            novel_title (str, optional): 특정 소설만 내보낼 경우 제목 지정
            
        Returns:
            dict: 내보낼 데이터
        """
        if novel_title:
            # 특정 소설만 내보내기
            novel = self.get_novel_by_title(novel_title)
            characters = self.get_characters_by_novel(novel_title)
            
            return {
                'novel': novel,
                'characters': characters,
                'export_date': datetime.now().isoformat()
            }
        else:
            # 전체 데이터 내보내기
            novels = self.load_novels()
            characters = self.load_all_characters()
            
            return {
                'novels': novels,
                'characters': characters,
                'export_date': datetime.now().isoformat()
            }
    
    def import_data(self, data):
        """
        데이터를 가져옵니다.
        
        Args:
            data (dict): 가져올 데이터
            
        Returns:
            bool: 성공 여부
        """
        try:
            if 'novel' in data and 'characters' in data:
                # 단일 소설 데이터 가져오기
                self.save_novel(data['novel'])
                self.save_characters(data['characters'], data['novel']['title'])
            elif 'novels' in data and 'characters' in data:
                # 전체 데이터 가져오기
                with open(self.novels_file, 'w', encoding='utf-8') as f:
                    json.dump(data['novels'], f, ensure_ascii=False, indent=2)
                
                with open(self.characters_file, 'w', encoding='utf-8') as f:
                    json.dump(data['characters'], f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"데이터 가져오기 실패: {str(e)}")
            return False

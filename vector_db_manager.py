import json
import os
import pickle
import numpy as np
from openai import OpenAI
from typing import List, Dict, Any, Optional
import streamlit as st

class VectorDBManager:
    """벡터 데이터베이스를 관리하는 클래스 (OpenAI Embeddings + 간단한 벡터 저장소)"""
    
    def __init__(self):
        # OpenAI 클라이언트 초기화
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # 벡터와 메타데이터 저장소
        self.chapters_vectors = []
        self.characters_vectors = []
        self.chapters_metadata = []
        self.characters_metadata = []
        
        # 데이터 저장 경로
        self.data_dir = "./vector_data"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def create_novel_collections(self, novel_title: str):
        """소설별 벡터 저장소 생성"""
        try:
            # 벡터와 메타데이터 초기화
            self.chapters_vectors = []
            self.characters_vectors = []
            self.chapters_metadata = []
            self.characters_metadata = []
            
            # 소설 제목 저장
            self.current_novel = novel_title.replace(' ', '_')
            
            return True
            
        except Exception as e:
            st.error(f"벡터 저장소 생성 실패: {str(e)}")
            return False
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """텍스트를 임베딩으로 변환"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            # 정규화 (코사인 유사도를 위해)
            embedding = embedding / np.linalg.norm(embedding)
            return embedding
        except Exception as e:
            st.error(f"임베딩 생성 실패: {str(e)}")
            return None

    def add_chapter_to_db(self, chapter_data: Dict[str, Any]):
        """챕터 데이터를 벡터 저장소에 추가"""
        try:
            # 챕터 텍스트로 임베딩 생성
            chapter_text = f"{chapter_data['title']} {chapter_data['summary']} {' '.join(chapter_data.get('keywords', []))}"
            
            embedding = self.get_embedding(chapter_text)
            if embedding is None:
                return False
            
            # 벡터 저장
            self.chapters_vectors.append(embedding)
            
            # 메타데이터 저장
            metadata = {
                "chapter_number": chapter_data["number"],
                "title": chapter_data["title"],
                "summary": chapter_data["summary"],
                "keywords": chapter_data.get("keywords", []),
                "characters_mentioned": chapter_data.get("characters_mentioned", []),
                "plot_progression": chapter_data.get("plot_progression", ""),
                "emotional_tone": chapter_data.get("emotional_tone", ""),
                "setting": chapter_data.get("setting", ""),
                "key_events": chapter_data.get("key_events", []),
                "content": chapter_data["content"]  # 전체 내용도 저장
            }
            
            self.chapters_metadata.append(metadata)
            
            return True
            
        except Exception as e:
            st.error(f"챕터 벡터 저장 실패: {str(e)}")
            return False
    
    def add_character_to_db(self, character_data: Dict[str, Any]):
        """캐릭터 데이터를 벡터 저장소에 추가"""
        try:
            # 캐릭터 정보로 임베딩 생성
            character_text = f"{character_data['name']} {character_data['personality']} {character_data['background']} {character_data['role']} {' '.join(character_data.get('key_traits', []))}"
            
            embedding = self.get_embedding(character_text)
            if embedding is None:
                return False
            
            # 벡터 저장
            self.characters_vectors.append(embedding)
            
            # 메타데이터 저장
            metadata = {
                "name": character_data["name"],
                "personality": character_data["personality"],
                "background": character_data["background"],
                "role": character_data["role"],
                "relationships": character_data.get("relationships", ""),
                "description": character_data.get("description", ""),
                "key_traits": character_data.get("key_traits", []),
                "character_arc": character_data.get("character_arc", ""),
                "motivations": character_data.get("motivations", ""),
                "chapters_appeared": character_data.get("chapters_appeared", [])
            }
            
            self.characters_metadata.append(metadata)
            
            return True
            
        except Exception as e:
            st.error(f"캐릭터 벡터 저장 실패: {str(e)}")
            return False
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """두 벡터 간의 코사인 유사도 계산"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def search_chapters(self, query: str, n_results: int = 5) -> List[Dict]:
        """챕터 검색"""
        try:
            if len(self.chapters_vectors) == 0 or len(self.chapters_metadata) == 0:
                return []
            
            # 쿼리 임베딩 생성
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                return []
            
            # 모든 챕터와의 유사도 계산
            similarities = []
            for i, chapter_vector in enumerate(self.chapters_vectors):
                similarity = self.cosine_similarity(query_embedding, chapter_vector)
                similarities.append((similarity, i))
            
            # 유사도 순으로 정렬
            similarities.sort(reverse=True)
            n_results = min(n_results, len(similarities))
            
            # 결과 구성
            chapters = []
            for similarity, idx in similarities[:n_results]:
                if idx < len(self.chapters_metadata):
                    metadata = self.chapters_metadata[idx].copy()
                    metadata['similarity_score'] = float(similarity)
                    chapters.append(metadata)
            
            return chapters
            
        except Exception as e:
            st.error(f"챕터 검색 실패: {str(e)}")
            return []
    
    def search_characters(self, query: str, n_results: int = 5) -> List[Dict]:
        """캐릭터 검색"""
        try:
            if len(self.characters_vectors) == 0 or len(self.characters_metadata) == 0:
                return []
            
            # 쿼리 임베딩 생성
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                return []
            
            # 모든 캐릭터와의 유사도 계산
            similarities = []
            for i, character_vector in enumerate(self.characters_vectors):
                similarity = self.cosine_similarity(query_embedding, character_vector)
                similarities.append((similarity, i))
            
            # 유사도 순으로 정렬
            similarities.sort(reverse=True)
            n_results = min(n_results, len(similarities))
            
            # 결과 구성
            characters = []
            for similarity, idx in similarities[:n_results]:
                if idx < len(self.characters_metadata):
                    metadata = self.characters_metadata[idx].copy()
                    metadata['similarity_score'] = float(similarity)
                    characters.append(metadata)
            
            return characters
            
        except Exception as e:
            st.error(f"캐릭터 검색 실패: {str(e)}")
            return []
    
    def get_chapter_context(self, chapter_number: int) -> Dict:
        """특정 챕터의 컨텍스트 정보 가져오기"""
        try:
            for metadata in self.chapters_metadata:
                if metadata['chapter_number'] == chapter_number:
                    return metadata.copy()
            return {}
            
        except Exception as e:
            st.error(f"챕터 컨텍스트 조회 실패: {str(e)}")
            return {}

    def save_to_disk(self, novel_title: str):
        """벡터와 메타데이터를 디스크에 저장"""
        try:
            novel_name = novel_title.replace(' ', '_')
            
            # 벡터 저장
            if self.chapters_vectors:
                np.save(f"{self.data_dir}/{novel_name}_chapters_vectors.npy", np.array(self.chapters_vectors))
            if self.characters_vectors:
                np.save(f"{self.data_dir}/{novel_name}_characters_vectors.npy", np.array(self.characters_vectors))
            
            # 메타데이터 저장
            with open(f"{self.data_dir}/{novel_name}_chapters_meta.pkl", 'wb') as f:
                pickle.dump(self.chapters_metadata, f)
            with open(f"{self.data_dir}/{novel_name}_characters_meta.pkl", 'wb') as f:
                pickle.dump(self.characters_metadata, f)
                
            return True
            
        except Exception as e:
            st.error(f"벡터 저장 실패: {str(e)}")
            return False

    def load_from_disk(self, novel_title: str):
        """디스크에서 벡터와 메타데이터를 로드"""
        try:
            novel_name = novel_title.replace(' ', '_')
            
            # 벡터 로드
            chapters_vectors_path = f"{self.data_dir}/{novel_name}_chapters_vectors.npy"
            characters_vectors_path = f"{self.data_dir}/{novel_name}_characters_vectors.npy"
            
            if os.path.exists(chapters_vectors_path):
                self.chapters_vectors = list(np.load(chapters_vectors_path))
            if os.path.exists(characters_vectors_path):
                self.characters_vectors = list(np.load(characters_vectors_path))
            
            # 메타데이터 로드
            chapters_meta_path = f"{self.data_dir}/{novel_name}_chapters_meta.pkl"
            characters_meta_path = f"{self.data_dir}/{novel_name}_characters_meta.pkl"
            
            if os.path.exists(chapters_meta_path):
                with open(chapters_meta_path, 'rb') as f:
                    self.chapters_metadata = pickle.load(f)
            if os.path.exists(characters_meta_path):
                with open(characters_meta_path, 'rb') as f:
                    self.characters_metadata = pickle.load(f)
                    
            return True
            
        except Exception as e:
            st.error(f"벡터 로드 실패: {str(e)}")
            return False
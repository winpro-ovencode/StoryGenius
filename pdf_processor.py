import pymupdf as fitz  # PyMuPDF
import streamlit as st

class PDFProcessor:
    """PDF 파일을 처리하고 텍스트를 추출하는 클래스"""
    
    def __init__(self):
        pass
    
    def extract_text(self, uploaded_file):
        """
        업로드된 PDF 파일에서 텍스트를 추출합니다.
        
        Args:
            uploaded_file: Streamlit의 UploadedFile 객체
            
        Returns:
            str: 추출된 텍스트
        """
        try:
            # PDF 문서 열기
            pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            
            text_content = ""
            total_pages = len(pdf_document)
            
            # 진행률 표시를 위한 progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for page_num in range(total_pages):
                # 페이지 텍스트 추출
                page = pdf_document[page_num]
                page_text = page.get_text()
                text_content += page_text + "\n"
                
                # 진행률 업데이트
                progress = (page_num + 1) / total_pages
                progress_bar.progress(progress)
                status_text.text(f"페이지 {page_num + 1}/{total_pages} 처리 중...")
            
            # PDF 문서 닫기
            pdf_document.close()
            
            # 진행률 표시 제거
            progress_bar.empty()
            status_text.empty()
            
            return self._clean_text(text_content)
            
        except Exception as e:
            raise Exception(f"PDF 텍스트 추출 실패: {str(e)}")
    
    def _clean_text(self, text):
        """
        추출된 텍스트를 정리합니다.
        
        Args:
            text (str): 원본 텍스트
            
        Returns:
            str: 정리된 텍스트
        """
        if not text:
            return ""
        
        # 불필요한 공백 제거
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 공백만 있는 줄 제거
            if line.strip():
                cleaned_lines.append(line.strip())
        
        # 줄바꿈으로 다시 결합
        cleaned_text = '\n'.join(cleaned_lines)
        
        # 연속된 줄바꿈 정리
        import re
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text
    
    def get_text_statistics(self, text):
        """
        텍스트 통계 정보를 반환합니다.
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            dict: 텍스트 통계 정보
        """
        if not text:
            return {
                'characters': 0,
                'words': 0,
                'lines': 0,
                'paragraphs': 0
            }
        
        # 문자 수 (공백 포함)
        char_count = len(text)
        
        # 단어 수 (공백으로 분할)
        word_count = len(text.split())
        
        # 줄 수
        line_count = len(text.split('\n'))
        
        # 문단 수 (빈 줄로 구분된 텍스트 블록)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        return {
            'characters': char_count,
            'words': word_count,
            'lines': line_count,
            'paragraphs': paragraph_count
        }

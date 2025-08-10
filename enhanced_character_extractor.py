import json
import os
import re
from openai import OpenAI
from llm_costs import (
    estimate_tokens_from_messages,
    estimate_tokens_from_text,
    estimate_chat_cost,
    should_show_cost_info,
)
from typing import List, Dict, Any, Optional
import streamlit as st

class EnhancedCharacterExtractor:
    """향상된 캐릭터 및 챕터 분석 클래스 (RAG 기반)"""

    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-5"

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
            # 우선 마이크로-분할 후 LLM 병합 방식 사용 (기본). 비활성화 시 창 기반 LLM 분할 사용
            use_micro_merge = os.environ.get("USE_MICRO_MERGE", "1") == "1"
            if use_micro_merge:
                chapters = self._split_chapters_micro_merge(text_content, progress_callback=progress_callback)
            else:
                # 먼저 LLM 기반 챕터 구분 시도(토큰 윈도우 확장)
                chapters = self._split_chapters_with_llm(text_content, max_input_chars=100000, progress_callback=progress_callback)

            # 최소 챕터 길이 설정 (환경변수로 조절 가능)
            min_len_env = os.environ.get("MIN_CHAPTER_LENGTH")
            try:
                minimum_length = int(min_len_env) if min_len_env else 8000
            except ValueError:
                minimum_length = 8000

            llm_only = os.environ.get("LLM_SPLIT_ONLY", "1") == "1"
            if not chapters:
                if llm_only:
                    # 강제 분할 없이 전체를 하나의 챕터로 취급
                    whole = text_content.strip()
                    chapters = [whole] if whole else []
                else:
                    # LLM 분할 실패 시 기존 자동 감지 → 길이 분할 순으로 폴백
                    chapters = self._auto_detect_chapters(text_content)
                    if not chapters:
                        chapters = self._split_by_length(text_content, min_length=minimum_length)
            else:
                # LLM-only 모드에서는 최소 길이 강제 병합을 건너뜀(LLM 결과 보존)
                if not llm_only and os.environ.get("ENFORCE_MIN_FOR_AUTO", "0") == "1":
                    chapters = self._ensure_min_length(chapters, minimum_length)

            # 디버깅: 완료 챕터 개수 제한
            debug_max_env = os.environ.get("DEBUG_MAX_CHAPTERS")
            try:
                debug_max = int(debug_max_env) if debug_max_env else 0
            except ValueError:
                debug_max = 0
            if debug_max and debug_max > 0:
                chapters = chapters[:debug_max]
            
            # 각 챕터를 상세 분석
            analyzed_chapters = []
            total_chapters = len(chapters)
            
            for i, chapter_content in enumerate(chapters, 1):
                if progress_callback:
                    progress_callback(i, total_chapters, f"챕터 {i} 분석 중...")
                
                chapter_info = self._analyze_chapter_enhanced(chapter_content, i)
                analyzed_chapters.append(chapter_info)

                # 챕터 분석 완료 알림 (제목과 글자 수 표시)
                if progress_callback:
                    try:
                        chapter_title = chapter_info.get('title', f'챕터 {i}')
                        chapter_len = len(chapter_content)
                        progress_callback(
                            i,
                            total_chapters,
                            f"완료: {chapter_title} ({chapter_len:,}자)"
                        )
                    except Exception:
                        # 콜백 실패는 전체 흐름에 영향 주지 않음
                        pass
                
                # 너무 많은 API 호출 방지를 위한 잠시 대기
                if i % 3 == 0:  # 3개마다 잠시 대기
                    import time
                    time.sleep(1)
            
            return analyzed_chapters

        except Exception as e:
            raise Exception(f"향상된 챕터 추출 실패: {str(e)}")

    def _micro_split_text(
        self,
        text: str,
        target_chars: int = 1600,
        hard_max_chars: int = 2400,
        progress_callback=None,
    ) -> List[str]:
        """문단/문장 경계를 우선해 작은 단위로 텍스트를 분할합니다.

        - target_chars를 우선 목표로 문장/문단 경계에서 자름
        - 그래도 경계를 못 찾으면 hard_max_chars에서 절단
        """
        if not text:
            return []

        paragraphs = [p for p in re.split(r"\n{2,}", text) if p.strip()]
        chunks: List[str] = []
        buffer = ""
        sentence_endings = re.compile(r"([\.\!\?。！？])\s+")

        def flush(buf: str):
            b = buf.strip()
            if b:
                chunks.append(b)

        total_paras = len(paragraphs)
        for idx, para in enumerate(paragraphs, start=1):
            para = para.strip()
            if not para:
                continue

            if not buffer:
                buffer = para
            else:
                buffer = buffer + "\n\n" + para

            # 필요하면 문장 경계 기반으로 분할
            while len(buffer) >= hard_max_chars:
                window = buffer[:hard_max_chars]
                # hard_max 내에서 마지막 문장 종료 지점 찾기
                last_sentence = -1
                for m in sentence_endings.finditer(window):
                    last_sentence = m.end()
                if last_sentence != -1 and last_sentence >= target_chars // 2:
                    flush(buffer[:last_sentence])
                    buffer = buffer[last_sentence:]
                else:
                    flush(buffer[:hard_max_chars])
                    buffer = buffer[hard_max_chars:]

            # target에 도달하면 가볍게 끊기 시도
            if len(buffer) >= target_chars:
                # 문단 경계 우선
                flush(buffer)
                buffer = ""

            if progress_callback and total_paras:
                try:
                    progress_callback(idx, total_paras, f"[분할] 마이크로 분할 진행 {idx}/{total_paras}")
                except Exception:
                    pass

        if buffer:
            flush(buffer)

        return chunks

    def _merge_micro_chunks_with_llm(
        self,
        micro_chunks: List[str],
        batch_size: int = 18,
        snippet_len: int = 300,
        progress_callback=None,
    ) -> List[List[int]]:
        """여러 개의 마이크로 청크를 LLM으로 묶어 챕터 경계를 찾습니다.

        반환: 각 챕터 그룹을 이루는 마이크로 청크 인덱스 리스트들의 배열
        예: [[0,1,2], [3,4], [5,6,7,8], ...]
        """
        if not micro_chunks:
            return []

        groups: List[List[int]] = []
        carry_start_idx = 0
        n = len(micro_chunks)

        total_batches = max(1, (n + batch_size - 1) // max(1, batch_size))
        batch_no = 0
        while carry_start_idx < n:
            batch_no += 1
            end_idx = min(carry_start_idx + batch_size, n)
            batch_indices = list(range(carry_start_idx, end_idx))

            if progress_callback:
                try:
                    progress_callback(batch_no, total_batches, f"[분할] 병합 배치 {batch_no}/{total_batches}")
                except Exception:
                    pass

            # 각 마이크로 청크의 앞/뒤 스니펫만 제공하여 토큰 절약
            summarized = []
            for i in batch_indices:
                t = micro_chunks[i]
                head = t[:snippet_len]
                tail = t[-snippet_len:] if len(t) > snippet_len else ""
                summarized.append({
                    "index": i,
                    "head": head,
                    "tail": tail,
                    "chars": len(t),
                })

            prompt = (
                "아래 마이크로 텍스트 조각들의 순서를 고려하여 문맥이 강하게 연결되는 연속 구간들을 '챕터'로 묶으세요.\n"
                "- 각 조각은 index로 식별됩니다.\n"
                "- 인접한 조각들만 묶을 수 있습니다(순서 유지).\n"
                "- 결과는 index의 배열들(각 배열이 한 챕터)을 담은 chapters로만 반환하세요.\n"
                "- 확신이 없으면 왼쪽(앞쪽)으로만 최대한 묶고, 애매한 꼬리는 leftover_from_index 이후로 넘기세요.\n"
                "반환 형식(JSON): {\n  \"chapters\": [[i,i+1,...], ...],\n  \"leftover_from_index\": number\n}\n\n"
                f"입력: {json.dumps(summarized, ensure_ascii=False)}"
            )

            try:
                # 비용/토큰 추정용 메시지 사전 구성
                msg = [
                    {"role": "system", "content": "당신은 소설 챕터 경계 병합 전문가입니다. JSON만 반환합니다."},
                    {"role": "user", "content": prompt},
                ]
                est_prompt_tokens = estimate_tokens_from_messages(msg)
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=msg,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("빈 응답")
                data = json.loads(content)
                if should_show_cost_info():
                    try:
                        import streamlit as st
                        est_completion_tokens = estimate_tokens_from_text(content)
                        costs = estimate_chat_cost(self.model, est_prompt_tokens, est_completion_tokens)
                        st.caption(
                            f"[병합] 토큰 예상 — 입력 ~{est_prompt_tokens:,} / 출력 ~{est_completion_tokens:,}, 비용 ${costs['total_cost']:.4f}"
                        )
                    except Exception:
                        pass
                batch_groups = data.get("chapters", []) or []
                leftover_from = data.get("leftover_from_index", end_idx)
                if not isinstance(leftover_from, int) or leftover_from < carry_start_idx:
                    leftover_from = end_idx
                leftover_from = min(leftover_from, end_idx)

                for g in batch_groups:
                    safe = [int(x) for x in g if isinstance(x, int)]
                    if not safe:
                        continue
                    # 연속성 보장 및 범위 체크
                    if all(carry_start_idx <= x < end_idx for x in safe):
                        safe_sorted = sorted(safe)
                        # 인접한 인덱스 연속만 허용
                        if all(safe_sorted[i] + 1 == safe_sorted[i + 1] for i in range(len(safe_sorted) - 1)):
                            groups.append(safe_sorted)

                if leftover_from >= end_idx:
                    carry_start_idx = end_idx
                else:
                    carry_start_idx = leftover_from

            except Exception:
                # 실패 시 현재 배치를 단일 그룹으로 취급
                groups.append(batch_indices)
                carry_start_idx = end_idx

        return groups

    def _split_chapters_micro_merge(self, text: str, progress_callback=None) -> List[str]:
        """본문을 작은 단위로 먼저 나누고, 문맥 연결성이 강한 단위들을 챕터로 병합합니다."""
        # 1) 마이크로 분할
        micro = self._micro_split_text(text, progress_callback=progress_callback)
        if not micro:
            return []

        # 2) LLM으로 병합 경계 계산
        index_groups = self._merge_micro_chunks_with_llm(micro, progress_callback=progress_callback)
        if not index_groups:
            # 아무 것도 못 받으면 전체를 하나로
            return [text.strip()] if text.strip() else []

        # 3) 인덱스 그룹을 실제 텍스트로 결합
        chapters: List[str] = []
        used = set()
        for group in index_groups:
            parts = []
            for idx in group:
                if 0 <= idx < len(micro) and idx not in used:
                    parts.append(micro[idx])
                    used.add(idx)
            if parts:
                chapters.append("\n\n".join(parts).strip())

        # 4) 빠진 잔여 마이크로 청크가 있으면 뒤에 합치기
        leftovers = [micro[i] for i in range(len(micro)) if i not in used]
        if leftovers:
            chapters.append("\n\n".join(leftovers).strip())

        return [c for c in chapters if c]

    def _split_chapters_with_llm(
        self,
        text: str,
        approx_tokens_per_call: int = 4000,
        max_input_chars: Optional[int] = None,
        progress_callback=None,
    ) -> List[str]:
        """LLM을 이용해 텍스트를 안정적으로 챕터 단위로 분할합니다.

        원리:
        - 약 4000 토큰 분량(문자수로 근사)씩 창을 만들어 전달
        - 모델은 창 안에서 '완전한' 챕터들만 인덱스 범위(start,end)로 반환하고, 애매한 꼬리는 leftover로 남김
        - leftover를 다음 창 앞부분에 붙여 더 많은 컨텍스트로 재시도
        - 결과적으로 자연 경계 기준의 챕터 분할을 얻음(텍스트는 로컬 슬라이싱으로 복원, 모델이 본문을 재출력하지 않음)
        """
        if not text:
            return []

        # 디버깅용: 입력 텍스트 최대 길이 제한 (환경변수 LLM_SPLIT_MAX_INPUT_CHARS 또는 매개변수)
        if max_input_chars is None:
            max_chars_env = os.environ.get("LLM_SPLIT_MAX_INPUT_CHARS")
            try:
                max_input_chars = int(max_chars_env) if max_chars_env else None
            except ValueError:
                max_input_chars = None
        if max_input_chars and max_input_chars > 0 and len(text) > max_input_chars:
            text = text[:max_input_chars]

        # 문자수 기반 토큰 근사치 설정(환경변수 CHARS_PER_TOKEN로 조절 가능)
        chars_per_token_env = os.environ.get("CHARS_PER_TOKEN")
        try:
            chars_per_token = int(chars_per_token_env) if chars_per_token_env else 3
        except ValueError:
            chars_per_token = 3

        # 분할 크기(문자)
        chunk_chars = max(approx_tokens_per_call * chars_per_token, 8000)

        # LLM-only 모드 여부
        llm_only = os.environ.get("LLM_SPLIT_ONLY", "1") == "1"

        chapters: List[str] = []
        carryover: str = ""
        cursor = 0
        text_len = len(text)
        stall_count = 0
        max_stall = 2  # carryover가 줄지 않고 새 챕터도 안 생기는 상태가 연속 2회면 폴백

        # 무한루프 방지용 진행 추적
        last_progress_signature = (-1, -1)
        max_iterations = 1000
        iterations = 0

        total_windows_est = max(1, (text_len + max(1, chunk_chars) - 1) // max(1, chunk_chars))
        processed_windows = 0

        while cursor < text_len or carryover:
            iterations += 1
            if iterations > max_iterations:
                # 예외적인 경우 안전 종료: 남은 텍스트를 하나로 추가
                remainder = (carryover + text[cursor:]).strip()
                if remainder:
                    chapters.append(remainder)
                break

            window = carryover + text[cursor: min(cursor + chunk_chars, text_len)]
            if not window:
                break

            processed_windows += 1
            if progress_callback:
                try:
                    progress_callback(processed_windows, total_windows_est, f"[분할] 윈도우 {processed_windows}/{total_windows_est} 처리 중...")
                except Exception:
                    pass

            prompt = (
                "주어진 소설 텍스트 창(window)에서 완전하게 끝나는 챕터만 찾아 분리하세요.\n"
                "반드시 JSON으로만 응답하고, 본문 텍스트를 재출력하지 마세요.\n\n"
                "규칙:\n"
                "- segments: 창 내부에서 완전한 챕터 경계만 포함한 배열입니다. 각 항목은 {title, start, end}를 가져야 합니다.\n"
                "- start, end는 창 문자열에 대한 0-기반 인덱스이며, Python 슬라이싱 기준으로 [start, end) 구간입니다.\n"
                "- segments는 서로 겹치지 않고, 오름차순이어야 하며, 제목이 명시적이면 사용하고 없으면 간단히 생성합니다.\n"
                "- leftover_from: 창의 끝부분이 애매하여 다음 창에 더 많은 컨텍스트가 필요하다면, 애매함이 시작되는 0-기반 인덱스(창 기준)를 지정합니다.\n"
                "  애매한 꼬리가 없다면 leftover_from는 창 길이로 설정하세요.\n"
                "- 본문을 만들어내지 말고, 오직 인덱스와 제목만 반환하세요.\n\n"
                "반환 형식(JSON):\n"
                "{\n  \"segments\": [ { \"title\": string, \"start\": number, \"end\": number } ],\n  \"leftover_from\": number\n}"
            )

            try:
                prev_chapters_len = len(chapters)
                prev_carry_len = len(carryover)
                msg = [
                    {
                        "role": "system",
                        "content": (
                            "당신은 소설 텍스트의 챕터 경계를 식별하는 전문가입니다.\n"
                            "정확한 인덱스만 반환하고, 본문을 재출력하지 마세요."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            prompt
                            + "\n\n[창 시작]\n" + window + "\n[창 끝]"
                        ),
                    },
                ]
                est_prompt_tokens = estimate_tokens_from_messages(msg)
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=msg,
                    response_format={"type": "json_object"},
                    
                )

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("빈 응답")

                data = json.loads(content)
                if should_show_cost_info():
                    try:
                        import streamlit as st
                        est_completion_tokens = estimate_tokens_from_text(content)
                        costs = estimate_chat_cost(self.model, est_prompt_tokens, est_completion_tokens)
                        st.caption(
                            f"[LLM분할] 토큰 예상 — 입력 ~{est_prompt_tokens:,} / 출력 ~{est_completion_tokens:,}, 비용 ${costs['total_cost']:.4f}"
                        )
                    except Exception:
                        pass
                segments = data.get("segments", []) or []
                leftover_from = data.get("leftover_from", len(window))

                # 세이프가드
                if not isinstance(leftover_from, int) or leftover_from < 0:
                    leftover_from = len(window)
                leftover_from = min(leftover_from, len(window))

                # 세그먼트 정합성 검사 및 추가
                last_end = 0
                for seg in segments:
                    try:
                        start = int(seg.get("start", 0))
                        end = int(seg.get("end", 0))
                        title = seg.get("title", "") or "무제"
                    except Exception:
                        continue

                    if 0 <= start < end <= len(window) and start >= last_end and end <= leftover_from:
                        chapter_text = window[start:end].strip()
                        if chapter_text:
                            chapters.append(chapter_text)
                            last_end = end

                # leftover 계산 및 다음 루프 준비
                new_carry = window[leftover_from:]
                # 진행 상황 서명(커서, carry 길이)으로 루프 활착 감지
                progress_signature = (cursor, len(new_carry))
                if progress_signature == last_progress_signature and len(new_carry) == len(carryover):
                    # 진행이 전혀 없다면 강제 전진
                    cursor = min(cursor + chunk_chars, text_len)
                    carryover = new_carry
                else:
                    cursor = min(cursor + chunk_chars, text_len)
                    carryover = new_carry
                    last_progress_signature = progress_signature

                # 마지막 반복에서 더 이상 입력이 없고 carry만 남았을 경우 처리
                if cursor >= text_len and not carryover.strip():
                    break

                # 무한루프 방지: 새 챕터 추가 없음 + carryover가 줄지 않음 + 더 붙일 원본문도 없음 → 폴백 분할
                no_new_chapters = len(chapters) == prev_chapters_len
                no_carry_shrink = len(carryover) >= prev_carry_len
                no_more_source = cursor >= text_len
                if no_new_chapters and no_carry_shrink and no_more_source:
                    stall_count += 1
                else:
                    stall_count = 0

                if stall_count >= max_stall:
                    remainder = (carryover + text[cursor:]).strip()
                    if remainder:
                        if llm_only:
                            # 강제 분할 없이 남은 전체를 하나의 챕터로 처리
                            chapters.append(remainder)
                        else:
                            # 폴백 허용 모드에서는 길이 기반 분할 사용
                            fb_min_env = os.environ.get("MIN_CHAPTER_LENGTH")
                            try:
                                fb_min = int(fb_min_env) if fb_min_env else 8000
                            except ValueError:
                                fb_min = 8000
                            fallback_parts = self._split_by_length(remainder, min_length=fb_min)
                            for part in fallback_parts:
                                p = part.strip()
                                if p:
                                    chapters.append(p)
                    break

            except Exception:
                # 오류 시 처리: LLM-only면 강제 분할 없이 창 전체를 하나의 챕터로, 아니면 길이 분할
                if llm_only:
                    p = window.strip()
                    if p:
                        chapters.append(p)
                    carryover = ""
                    cursor = min(cursor + chunk_chars, text_len)
                else:
                    fb_min_env = os.environ.get("MIN_CHAPTER_LENGTH")
                    try:
                        fb_min = int(fb_min_env) if fb_min_env else 8000
                    except ValueError:
                        fb_min = 8000
                    fallback_parts = self._split_by_length(window, min_length=fb_min)
                    # 첫 파트만 챕터로 채택, 나머지는 다음 창으로 넘김
                    if fallback_parts:
                        chapters.append(fallback_parts[0])
                        tail = "\n\n".join(fallback_parts[1:])
                        carryover = tail
                    cursor = min(cursor + chunk_chars, text_len)

        # 마지막 carryover가 남아 있으면 챕터로 추가
        if carryover and carryover.strip():
            chapters.append(carryover.strip())

        # 최소 길이 강제 병합 옵션 (LLM-only 모드에서는 적용하지 않음)
        if not llm_only:
            min_len_env = os.environ.get("MIN_CHAPTER_LENGTH")
            try:
                minimum_length = int(min_len_env) if min_len_env else 8000
            except ValueError:
                minimum_length = 8000
            if os.environ.get("ENFORCE_MIN_FOR_AUTO", "1") == "1":
                chapters = self._ensure_min_length(chapters, minimum_length)

        return chapters

    def _auto_detect_chapters(self, text: str) -> List[str]:
        """텍스트에서 자동으로 챕터를 감지합니다.

        개선사항:
        - 줄 시작(anchor) 기준으로만 제목 패턴을 감지해 오인식을 줄임
        - 한국어(장/화/부/파트/프롤로그/에필로그)와 영어(Chapter/Part), 로마 숫자까지 포괄
        - 다중 패턴의 결과를 통합·정렬하여 안정적인 분할 지점 생성
        """
        # 줄 시작 기준의 강한 챕터/장/화/부 패턴들 (multiline)
        anchored_patterns = [
            r'^\s*프롤로그\s*$',
            r'^\s*에필로그\s*$',
            r'^\s*제\s*\d+\s*(장|화|부)\s*$',
            r'^\s*\d+\s*(장|화|부)\s*$',
            r'^\s*파트\s*\d+\s*$',
            r'^\s*PART\s*\d+\s*$',
            r'^\s*Chapter\s*\d+\s*$',
            r'^\s*CHAPTER\s*\d+\s*$',
            r'^\s*CHAPTER\s*[IVXLCDM]+\s*$',
            r'^\s*Chapter\s*[IVXLCDM]+\s*$',
            r'^\s*챕터\s*\d+\s*$',
        ]

        # 약한 장면 구분자(씬 브레이크)
        scene_separators = [
            r'^\s*[-]{3,}\s*$',
            r'^\s*[\*]{3,}\s*$',
            r'^\s*[=]{3,}\s*$',
            r'^\s*#{1,6}\s+.+$',
            r'^\s*[◇■※○◆]+\s*$',
        ]

        # 모든 패턴에 대해 후보 수집
        candidate_starts: List[int] = []
        for pattern in anchored_patterns + scene_separators:
            for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                candidate_starts.append(m.start())

        # 중복 제거 및 정렬
        unique_starts = sorted(set(candidate_starts))

        # 분할 지점 최소 간격(너무 촘촘한 분할 방지)
        MIN_GAP = 800  # 문자 수 기준
        filtered_starts: List[int] = []
        last_added = -MIN_GAP
        for pos in unique_starts:
            if pos - last_added >= MIN_GAP:
                filtered_starts.append(pos)
                last_added = pos

        chapters: List[str] = []
        if len(filtered_starts) > 1:
            # 구간별로 자르기
            for i, start in enumerate(filtered_starts):
                if i == len(filtered_starts) - 1:
                    segment = text[start:]
                else:
                    segment = text[start:filtered_starts[i + 1]]
                segment = segment.strip()
                if segment:
                    chapters.append(segment)

        return chapters

    def _split_by_length(
        self,
        text: str,
        max_length: int = None,
        min_length: int = 8000,
        lookahead: int = 4000,
    ) -> List[str]:
        """길이 기반 분할을 하되 자연스러운 경계를 우선합니다.

        동작 원리:
        1) 최소 길이(min_length)에 도달하면 lookahead 범위 내에서 '제목/장/화' 패턴, 장면 분리선(***, ---),
           문단 경계(빈 줄 2개 이상), 문장 종료+줄바꿈 등을 탐색합니다.
        2) 적절한 경계가 없으면 문장부호 기반으로 자르고, 그래도 없으면 max_length에서 절단합니다.
        3) max_length는 환경변수 MAX_CHAPTER_LENGTH로 오버라이드 가능.
        """

        # 동적 최대/최소 길이 설정
        if max_length is None:
            env_max = os.environ.get("MAX_CHAPTER_LENGTH")
            try:
                max_length = int(env_max) if env_max else 14000
            except ValueError:
                max_length = 14000
        env_min = os.environ.get("MIN_CHAPTER_LENGTH")
        try:
            min_length = int(env_min) if env_min else min_length
        except ValueError:
            pass

        # 최소가 최대를 초과하면 최소를 최대값으로 보정
        if min_length > max_length:
            min_length = max_length

        chapters: List[str] = []
        current_pos = 0
        text_len = len(text)

        # 경계 후보 정규식들
        heading_regex = re.compile(
            r"^\s*(프롤로그|에필로그|제\s*\d+\s*(장|화|부)|\d+\s*(장|화|부)|파트\s*\d+|PART\s*\d+|Chapter\s*(\d+|[IVXLCDM]+)|CHAPTER\s*(\d+|[IVXLCDM]+)|챕터\s*\d+)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        scene_regex = re.compile(r"^\s*(?:[-]{3,}|\*{3,}|={3,}|#{1,6}\s+.+|[◇■※○◆]+)\s*$", re.MULTILINE)
        paragraph_break_regex = re.compile(r"\n{2,}")
        sentence_break_regex = re.compile(r"([\.!\?。！？])\s*\n")

        while current_pos < text_len:
            # 남은 길이가 짧으면 그대로 추가
            if text_len - current_pos <= max_length:
                segment = text[current_pos:].strip()
                if segment:
                    chapters.append(segment)
                break

            search_start = current_pos + max(min_length, 1)
            search_end = min(current_pos + max_length, text_len)
            window = text[search_start:search_end]

            # 1) 강한 경계(제목/장/화)를 lookahead 범위 내에서 탐색
            strong_points = [m.start() for m in heading_regex.finditer(window)]
            if strong_points:
                cut = search_start + strong_points[0]
            else:
                # 2) 장면 분리선, 문단 경계, 문장 종료+줄바꿈 순으로 탐색
                scene_points = [m.start() for m in scene_regex.finditer(window)]
                para_points = [m.start() for m in paragraph_break_regex.finditer(window)]
                sent_points = [m.start(0) for m in sentence_break_regex.finditer(window)]

                candidate_points = []
                candidate_points.extend(scene_points)
                candidate_points.extend(para_points)
                candidate_points.extend(sent_points)

                candidate_points = sorted(set(candidate_points))
                if candidate_points:
                    cut = search_start + candidate_points[0]
                else:
                    # 3) 마지막 수단: max_length 바로 앞에서 문장부호를 역방향으로 탐색
                    backscan_region_start = max(current_pos, search_end - lookahead)
                    back_region = text[backscan_region_start:search_end]
                    best_end = -1
                    for ch in ['.', '!', '?', '。', '！', '？']:
                        pos = back_region.rfind(ch)
                        if pos > best_end:
                            best_end = pos
                    if best_end != -1:
                        cut = backscan_region_start + best_end + 1
                    else:
                        # 그래도 없으면 강제 절단
                        cut = search_end

            segment = text[current_pos:cut].strip()
            if segment:
                chapters.append(segment)
            current_pos = cut

        return chapters

    def _ensure_min_length(self, segments: List[str], minimum: int) -> List[str]:
        """인접 구간을 병합해 각 구간이 최소 길이를 만족하도록 보정합니다.

        마지막 구간이 짧으면 직전 구간과 병합합니다. 전체 텍스트가 최소 길이보다 짧은 경우는 그대로 반환합니다.
        """
        if not segments:
            return []

        if sum(len(s) for s in segments) <= minimum:
            return ["\n\n".join(segments).strip()]

        merged: List[str] = []
        buffer = ""
        for seg in segments:
            if not buffer:
                buffer = seg
            else:
                buffer = buffer + "\n\n" + seg

            if len(buffer) >= minimum:
                merged.append(buffer.strip())
                buffer = ""

        if buffer:
            if merged and len(buffer) < minimum:
                merged[-1] = (merged[-1] + "\n\n" + buffer).strip()
            else:
                merged.append(buffer.strip())

        return merged

    def _analyze_chapter_enhanced(self, chapter_content: str, chapter_number: int) -> Dict[str, Any]:
        """
        개별 챕터를 상세 분석합니다.
        """
        try:
            # 챕터 내용을 적절한 길이로 제한
            content_sample = chapter_content
            
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

            msg = [
                {"role": "system", "content": "당신은 소설 분석 전문가입니다. 한국어 소설을 정확히 분석하고 구조화된 JSON 형태로 응답합니다."},
                {"role": "user", "content": prompt},
            ]
            est_prompt_tokens = estimate_tokens_from_messages(msg)
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=msg,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content:
                analysis = json.loads(content)
            else:
                analysis = {}

            if should_show_cost_info() and content is not None:
                try:
                    import streamlit as st
                    est_completion_tokens = estimate_tokens_from_text(content)
                    costs = estimate_chat_cost(self.model, est_prompt_tokens, est_completion_tokens)
                    st.caption(
                        f"[챕터분석] 토큰 예상 — 입력 ~{est_prompt_tokens:,} / 출력 ~{est_completion_tokens:,}, 비용 ${costs['total_cost']:.4f}"
                    )
                except Exception:
                    pass

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

            # 간단한 대사/어록 후보 스니펫 추출(문자 기준 근처 맥락 일부)
            def collect_dialogue_samples(max_samples: int = 5, window: int = 120) -> str:
                samples = []
                quote_marks = ['"', '“', '”', '‘', '’', '「', '」', '『', '』']
                for chapter_num in appeared_chapters:
                    if len(samples) >= max_samples:
                        break
                    chapter = next((ch for ch in chapters if ch['number'] == chapter_num), None)
                    if not chapter:
                        continue
                    content = chapter.get('content', '') or ''
                    if not content:
                        continue
                    # 이름이 등장하는 지점 탐색
                    idx = content.find(character_name)
                    if idx == -1:
                        continue
                    # 주변에 인용부호 있으면 우선 사용
                    start = max(0, idx - window)
                    end = min(len(content), idx + window)
                    snippet = content[start:end]
                    if any(q in snippet for q in quote_marks):
                        samples.append(snippet.strip())
                    else:
                        # 인용부호가 없으면 근처 한 문단
                        samples.append(snippet.strip())
                return "\n\n".join(samples[:max_samples])

            dialogue_samples = collect_dialogue_samples()

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
            11. speech_style: 말투/어미/1인칭/구어체 특징 요약 (문장형)
            12. quotes: 대표 어록 또는 말버릇/상투구 (배열, 최대 5개, 20자 내외)

            컨텍스트:
            {context_text}

            (참고용 대사/문맥 스니펫 — 가능하면 여기서 대표 어록을 발굴)
            {dialogue_samples}

            JSON 형태로 응답해주세요.
            """

            msg = [
                {"role": "system", "content": "당신은 소설 캐릭터 분석 전문가입니다. 주어진 정보에서 캐릭터의 특성을 정확히 파악하고 구조화합니다."},
                {"role": "user", "content": prompt},
            ]
            est_prompt_tokens = estimate_tokens_from_messages(msg)
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=msg,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content:
                character_info = json.loads(content)
            else:
                character_info = {}

            if should_show_cost_info() and content is not None:
                try:
                    import streamlit as st
                    est_completion_tokens = estimate_tokens_from_text(content)
                    costs = estimate_chat_cost(self.model, est_prompt_tokens, est_completion_tokens)
                    st.caption(
                        f"[캐릭터분석] 토큰 예상 — 입력 ~{est_prompt_tokens:,} / 출력 ~{est_completion_tokens:,}, 비용 ${costs['total_cost']:.4f}"
                    )
                except Exception:
                    pass

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
                'speech_style': character_info.get('speech_style', ''),
                'quotes': character_info.get('quotes', []),
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
                'speech_style': '',
                'quotes': [],
                'chapters_appeared': appeared_chapters
            }
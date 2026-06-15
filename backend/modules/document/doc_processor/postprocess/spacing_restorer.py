"""자간 분리 텍스트 복원기.

PDF 내부에서 자간(letter-spacing)이 크게 적용된 한글 텍스트가
한 글자씩 공백으로 분리된 상태로 추출되는 현상을 복원합니다.

    브 랜 드 운 영  →  브랜드운영
    전 세 계 누 적 바 이 어  →  전세계누적바이어
    자 기 자 본 이 익 률  →  자기자본이익률

감지 조건:
    한글 1자(가-힣)인 토큰이 공백으로 분리되어 3개 이상 연속될 때

복원 방식:
    연속 구간의 공백을 모두 제거하여 붙여쓰기

복원 제외:
    - 영문 단독 (A B C D → 유지)
    - 숫자 단독 (1 2 3 4 → 유지)
    - 이미 정상적으로 띄어진 다음절 단어 (로그인 회원가입 → 유지)
    - 연속 2개 이하 (최소 3개 연속만 복원)

Kiwi 띄어쓰기 복원 (실험 모드):
    ENABLE_KIWI_SPACING = True 로 설정하면
    spacing_restorer 적용 후 kiwipiepy로 띄어쓰기를 추가합니다.
        브랜드운영 → 브랜드 운영
        전세계누적바이어 → 전세계 누적 바이어
    기본값: False (전역 적용 안 함)
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

# ── Kiwi 실험 옵션 ────────────────────────────────────────────────────────────
# True 로 바꾸면 spacing_restorer 이후 Kiwi 띄어쓰기 복원이 추가 적용됩니다.
# 전역 활성화하지 말고 실험/비교 목적으로만 사용하세요.
ENABLE_KIWI_SPACING: bool = False

# 단일 한글 문자 토큰 판별 (정확히 한글 1자)
_SINGLE_KO = re.compile(r'^[가-힣]$')

# 최소 연속 한글 단글자 수
_MIN_RUN = 3

# Kiwi 인스턴스 (ENABLE_KIWI_SPACING=True 일 때만 초기화)
_kiwi = None


def _get_kiwi():
    """Kiwi 인스턴스를 지연 초기화합니다."""
    global _kiwi
    if _kiwi is None:
        try:
            from kiwipiepy import Kiwi
            _kiwi = Kiwi()
        except ImportError:
            raise ImportError(
                "kiwipiepy가 설치되지 않았습니다.\n"
                "pip install kiwipiepy 로 설치하거나 "
                "ENABLE_KIWI_SPACING = False 로 설정하세요."
            )
    return _kiwi


def restore_spacing(text: str) -> str:
    """자간 분리된 한글 텍스트를 복원합니다.

    ENABLE_KIWI_SPACING = True 이면 복원 후 Kiwi 띄어쓰기도 적용합니다.

    Args:
        text: 정제 전 텍스트 (개행 포함 가능)

    Returns:
        자간 분리가 복원된 텍스트
    """
    result = _restore_spacing_only(text)
    if ENABLE_KIWI_SPACING:
        result = apply_kiwi_spacing(result)
    return result


def _restore_spacing_only(text: str) -> str:
    """Kiwi 없이 자간 분리만 복원합니다 (내부용)."""
    lines = text.split('\n')
    restored = [_restore_line(line) for line in lines]
    return '\n'.join(restored)


def apply_kiwi_spacing(text: str) -> str:
    """kiwipiepy로 띄어쓰기를 복원합니다 (실험용).

    줄바꿈을 보존하며 줄 단위로 처리합니다.
    """
    kiwi = _get_kiwi()
    lines = text.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            result.append(kiwi.space(stripped))
        else:
            result.append(line)
    return '\n'.join(result)


def _restore_line(line: str) -> str:
    """한 줄 내의 자간 분리 패턴을 복원합니다."""
    tokens = line.split(' ')
    result: list[str] = []
    i = 0

    while i < len(tokens):
        # 현재 위치부터 단일 한글 문자 토큰 연속 구간 탐색
        j = i
        while j < len(tokens) and _SINGLE_KO.match(tokens[j]):
            j += 1

        run_len = j - i

        if run_len >= _MIN_RUN:
            # 연속 한글 단글자 → 공백 없이 병합
            result.append(''.join(tokens[i:j]))
            i = j
        else:
            result.append(tokens[i])
            i += 1

    return ' '.join(result)

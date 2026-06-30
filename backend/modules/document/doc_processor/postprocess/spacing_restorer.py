"""자간 분리 텍스트 복원기.

PDF 내부에서 자간(letter-spacing)이 크게 적용된 한글 텍스트가
한 글자씩 공백으로 분리된 상태로 추출되는 현상을 복원합니다.

    브 랜 드 운 영  →  브랜드운영
    전 세 계 누 적 바 이 어  →  전세계누적바이어
"""
from __future__ import annotations

import re

_SINGLE_KO = re.compile(r'^[가-힣]$')
_MIN_RUN = 3


def restore_spacing(text: str) -> str:
    lines = text.split('\n')
    return '\n'.join(_restore_line(line) for line in lines)


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

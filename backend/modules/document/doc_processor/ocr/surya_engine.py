from __future__ import annotations

import re

from PIL import Image
from surya.detection import DetectionPredictor
from surya.recognition import RecognitionPredictor


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class SuryaEngine:
    def __init__(self) -> None:
        self._det = DetectionPredictor()
        self._rec = RecognitionPredictor()

    def run(self, image: Image.Image) -> list[str]:
        results = self._rec([image], det_predictor=self._det, sort_lines=True)
        if not results:
            return []
        lines = [_normalize(line.text) for line in results[0].text_lines if _normalize(line.text)]
        return list(dict.fromkeys(lines))

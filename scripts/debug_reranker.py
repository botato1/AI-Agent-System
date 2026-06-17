# scripts/debug_reranker.py
# reranker 초기화/호출의 각 단계별로 시간을 측정해서
# 정확히 어디서 멈추는지 확인하는 디버그 스크립트

import time

print("[0] 시작")

t0 = time.time()
from FlagEmbedding import FlagReranker
print(f"[1] import 완료: {time.time() - t0:.1f}초")

t1 = time.time()
print("[2] FlagReranker 모델 로딩 시작 (CPU, fp32)...")
reranker = FlagReranker(
    "BAAI/bge-reranker-v2-m3",
    use_fp16=False,
    devices=["cpu"],
)
print(f"[3] 모델 로딩 완료: {time.time() - t1:.1f}초")

t2 = time.time()
print("[4] compute_score 호출 시작...")
pairs = [
    ["쿠버네티스 파드가 OOM으로 죽었는데 어떻게 해결해", "쿠버네티스 파드는 리소스 제한을 초과하면 OOMKilled 상태가 된다."],
    ["쿠버네티스 파드가 OOM으로 죽었는데 어떻게 해결해", "도커 네트워크는 bridge, host, overlay 세 가지가 있다."],
]
scores = reranker.compute_score(pairs, normalize=True)
print(f"[5] compute_score 완료: {time.time() - t2:.1f}초")
print(f"[6] 결과: {scores}")

print("\n전체 완료!")
# Intel Mac 포함 평가 준비

- 사용자 확인: 깨끗한 환경 평가는 다른 Mac에서, Intel Mac 포함
- 사전 확인(arm64 Mac의 의존성 해석): requirements는 x86_64 macOS(cp311)용으로 해석 성공, 단 **torch 2.2.2 / torchvision 0.17.2**(arm64는 2.14.1 / 0.29.1) — 시험된 적 없는 조합
- Ollama 0.34.4(로컬 설치본)는 유니버설·macOS 14.0 이상 요구; 최신 zip의 구성은 미확인
- 설치기에 아키텍처 사전 점검이 없고 Apple Silicon 가정이 일부 있음(brew shellenv 경로)
- 절차서 §10과 스냅샷 수집기 보강 완료. Intel 결과는 아키텍처별로 따로 판정; Intel 지원 여부는 HQ 결정
- 한계: 의존성 해석 수준, Intel 실행 결과 아님

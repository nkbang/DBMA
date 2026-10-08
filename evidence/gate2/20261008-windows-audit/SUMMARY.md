# Windows 지원 현황 점검 (설계 착수 전)

- 앱 코드(core/ui)는 이식성이 좋은 편: POSIX 전용 API 0, macOS 전용 호출 0, 하드코딩 경로 1(우아하게 degrade), 경로는 Path/os.path 사용
- 위험: 인코딩 미지정 15곳(cp949에서 헬라어·히브리어), hunspell Windows wheel 없음, 외부 바이너리(poppler/tesseract)
- 설치·배포 계층은 전부 macOS 전용 → Windows 설치기 신규 작성 필요
- 의존성은 wheel 기준 대부분 해석 가능(chromadb는 pip 크로스 해석 한계로 inconclusive, 마커 보정 시 해석됨)
- Ollama는 Windows 공식 제공(OllamaSetup.exe 1.58GB)
- 한계: Windows 실행 결과 없음. 결정 필요: 배포 형태, 최소 사양, 서명, 범위, 평가 환경

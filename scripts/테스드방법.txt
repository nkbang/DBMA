cd /Users/David/DBMA
python3 scripts/benchmark_pipeline.py --glob "data/**/*.txt" --limit 5 --output output/bench


====




동작 방식
이래 스크립트는 다음 순서로 움직임

1.	 python -m pytest tests/ -v --tb=short .
2.	pytest가 실패하면 즉시 종료.
3.	pytest가 통과하면  benchmark_pipeline.py  실행.
4.	benchmark가 끝나면 성공 메시지 출력.



===

cd /Users/David/DBMA
python3 scripts/validate_pipeline.py


=====
# pytest만 먼저 보고 싶으면:

python3 scripts/validate_pipeline.py --skip-benchmark




====



cd /Users/David/DBMA
python3 scripts/validate_pipeline.py




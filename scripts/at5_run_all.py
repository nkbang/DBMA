#!/usr/bin/env python3
"""AT-5: 13개 질의 원문 답변 수집 (my-theology-bot-v2, HTTP API)"""
import urllib.request, json, sys, os

questions = [
    '오직 믿음으로 구원받는다는 것은 무엇을 뜻하는가?',
    '회개와 믿음의 관계를 설명해 달라.',
    '그리스도의 속죄가 모든 사람을 위한 것인가, 선택된 자만을 위한 것인가?',
    '중생(거듭남)은 믿음보다 먼저 일어나는가?',
    '복음을 모든 사람에게 값없이 제시해야 하는 근거는 무엇인가?',
    '침례의 합당한 대상은 누구인가?',
    '침례의 방식(침수)이 왜 중요한가?',
    '지역 교회의 회원권은 어떻게 결정되는가?',
    '교회의 권징(치리)은 어떤 절차로 이루어지는가?',
    '장로(감독)와 집사의 직분은 어떻게 다른가?',
    '성찬(주의 만찬)에 참여할 자격은 무엇인가?',
    '교회의 독립성(회중정치)을 성경적으로 어떻게 뒷받침하는가?',
    '신자의 견인(구원의 확신)은 어떤 근거로 주장되는가?',
]

os.makedirs('/tmp/at5', exist_ok=True)

for i, q in enumerate(questions, 1):
    payload = json.dumps({'model': 'my-theology-bot-v2', 'prompt': q, 'stream': False}).encode()
    req = urllib.request.Request('http://localhost:11434/api/generate', data=payload, headers={'Content-Type': 'application/json'})
    print(f'Q{i}: {q}', flush=True)
    with urllib.request.urlopen(req, timeout=150) as resp:
        result = json.loads(resp.read())
        response = result.get('response', '')
        with open(f'/tmp/at5/q{i}.txt', 'w', encoding='utf-8') as f:
            f.write(response)
        print(f'  -> {len(response)} chars, saved to /tmp/at5/q{i}.txt', flush=True)

print('ALL DONE', flush=True)

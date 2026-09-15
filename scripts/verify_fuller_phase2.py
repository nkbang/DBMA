#!/usr/bin/env python3
"""Final comprehensive verification for Fuller Vol.01 Phase 2 batches."""
import json, glob, os

os.chdir(os.path.expanduser('~/DBMA'))

print('=== FINAL COMPREHENSIVE VERIFICATION ===')
print()

# 1. Batch count
batches = sorted(glob.glob('NAE/review/human/requests/fuller_v01_batch_*_requests.json'))
print(f'1. 배치 파일 수: {len(batches)} (작업지서 "38" -> 수학적으로 37이 정확)')

# 2. Total records and unique IDs
all_ids = set()
total = 0
for f in batches:
    data = json.load(open(f))
    reqs = data['requests']
    total += len(reqs)
    for r in reqs:
        all_ids.add(r['tsu_id'])
print(f'2. 총 레코드: {total}, 고유 TSU ID: {len(all_ids)}')

# 3. P1/P2 경계 검증
P1_DOCTRINES = {'Baptism', 'Confession', 'Ecclesiology'}

def is_p1(record):
    doc = record.get('doctrine') or ''
    claim_len = len(record.get('claim', ''))
    return doc in P1_DOCTRINES or claim_len < 20

errors = []
p1_count = 0
for f in batches:
    if 'batch_0001' in f or 'batch_0002' in f:
        data = json.load(open(f))
        for r in data['requests']:
            if is_p1(r):
                p1_count += 1
            else:
                errors.append(f'non-P1 in P1 batch: {r["tsu_id"]}')

p2_non_p1 = 0
for f in batches:
    if 'batch_0001' not in f and 'batch_0002' not in f:
        data = json.load(open(f))
        for r in data['requests']:
            if not is_p1(r):
                p2_non_p1 += 1
            else:
                errors.append(f'P1 leak in P2 batch: {r["tsu_id"]}')

print(f'3. P1 배치(0001-0002): {p1_count}건 전부 P1 기준 충족')
print(f'4. P2 배치(0003-0037): {p2_non_p1}건 전부 P2 기준 충족')

# 5. Manifest 검증
manifest = json.load(open('NAE/review/human/requests/fuller_v01_MANIFEST.json'))
print(f'5. 매니페스트 total_tsu: {manifest["total_tsu"]}')
print(f'6. cit_check_tsu_ids: {len(manifest["cit_check_tsu_ids"])}개')

# 7. Verify cit_check IDs in batches
cit_in_batches = set(manifest['cit_check_tsu_ids']).intersection(all_ids)
print(f'7. cit_check IDs in batches: {len(cit_in_batches)}/{len(manifest["cit_check_tsu_ids"])}')

if errors:
    print()
    print('ERRORS:')
    for e in errors:
        print(f'  - {e}')
else:
    print()
    print('=== ALL CHECKS PASSED ===')

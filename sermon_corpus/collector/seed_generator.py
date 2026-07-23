# DBMA Sermon Corpus - 대규모 시드 데이터 생성기
# 성경 본문 기반 설교 제목 및 키워드 데이터셋 생성 (10만 건 목표)

import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 성경 전체 권/장 목록
BIBLE_BOOKS = {
    # OT 율법서
    "창세기": {"book_id": 1, "chapters": 50, "testament": "OT", "category": "율법서"},
    "출애굽기": {"book_id": 2, "chapters": 40, "testament": "OT", "category": "율법서"},
    "레위기": {"book_id": 3, "chapters": 27, "testament": "OT", "category": "율법서"},
    "민수기": {"book_id": 4, "chapters": 36, "testament": "OT", "category": "율법서"},
    "신명기": {"book_id": 5, "chapters": 34, "testament": "OT", "category": "율법서"},
    # OT 역사서
    "여호수아": {"book_id": 6, "chapters": 24, "testament": "OT", "category": "역사서"},
    "사사기": {"book_id": 7, "chapters": 21, "testament": "OT", "category": "역사서"},
    "룻": {"book_id": 8, "chapters": 4, "testament": "OT", "category": "역사서"},
    "사무엘상": {"book_id": 9, "chapters": 31, "testament": "OT", "category": "역사서"},
    "사무엘하": {"book_id": 10, "chapters": 24, "testament": "OT", "category": "역사서"},
    "열왕기상": {"book_id": 11, "chapters": 22, "testament": "OT", "category": "역사서"},
    "열왕기하": {"book_id": 12, "chapters": 25, "testament": "OT", "category": "역사서"},
    "역대상": {"book_id": 13, "chapters": 29, "testament": "OT", "category": "역사서"},
    "역대하": {"book_id": 14, "chapters": 36, "testament": "OT", "category": "역사서"},
    "에스라": {"book_id": 15, "chapters": 10, "testament": "OT", "category": "역사서"},
    "느헤미야": {"book_id": 16, "chapters": 13, "testament": "OT", "category": "역사서"},
    "에스더": {"book_id": 17, "chapters": 10, "testament": "OT", "category": "역사서"},
    # OT 시가서
    "욥": {"book_id": 18, "chapters": 42, "testament": "OT", "category": "시가서"},
    "시편": {"book_id": 19, "chapters": 150, "testament": "OT", "category": "시가서"},
    "잠언": {"book_id": 20, "chapters": 31, "testament": "OT", "category": "시가서"},
    "전도서": {"book_id": 21, "chapters": 12, "testament": "OT", "category": "시가서"},
    "아가": {"book_id": 22, "chapters": 8, "testament": "OT", "category": "시가서"},
    # OT 예언서
    "이사야": {"book_id": 23, "chapters": 66, "testament": "OT", "category": "예언서"},
    "예레미야": {"book_id": 24, "chapters": 52, "testament": "OT", "category": "예언서"},
    "예레미야애가": {"book_id": 25, "chapters": 5, "testament": "OT", "category": "예언서"},
    "에스겔": {"book_id": 26, "chapters": 48, "testament": "OT", "category": "예언서"},
    "다니엘": {"book_id": 27, "chapters": 12, "testament": "OT", "category": "예언서"},
    "호세아": {"book_id": 28, "chapters": 14, "testament": "OT", "category": "소예언서"},
    "요엘": {"book_id": 29, "chapters": 3, "testament": "OT", "category": "소예언서"},
    "아모스": {"book_id": 30, "chapters": 9, "testament": "OT", "category": "소예언서"},
    "오바댜": {"book_id": 31, "chapters": 1, "testament": "OT", "category": "소예언서"},
    "요나": {"book_id": 32, "chapters": 4, "testament": "OT", "category": "소예언서"},
    "미가": {"book_id": 33, "chapters": 7, "testament": "OT", "category": "소예언서"},
    "나훔": {"book_id": 34, "chapters": 3, "testament": "OT", "category": "소예언서"},
    "하박국": {"book_id": 35, "chapters": 3, "testament": "OT", "category": "소예언서"},
    "스바냐": {"book_id": 36, "chapters": 3, "testament": "OT", "category": "소예언서"},
    "학개": {"book_id": 37, "chapters": 2, "testament": "OT", "category": "소예언서"},
    "스가랴": {"book_id": 38, "chapters": 14, "testament": "OT", "category": "소예언서"},
    "말라기": {"book_id": 39, "chapters": 4, "testament": "OT", "category": "소예언서"},
    # NT 사복음서
    "마태복음": {"book_id": 40, "chapters": 28, "testament": "NT", "category": "사복음서"},
    "마가복음": {"book_id": 41, "chapters": 16, "testament": "NT", "category": "사복음서"},
    "누가복음": {"book_id": 42, "chapters": 24, "testament": "NT", "category": "사복음서"},
    "요한복음": {"book_id": 43, "chapters": 21, "testament": "NT", "category": "사복음서"},
    # NT 사도행전
    "사도행전": {"book_id": 44, "chapters": 28, "testament": "NT", "category": "교회사"},
    # NT 바울 서신
    "로마서": {"book_id": 45, "chapters": 16, "testament": "NT", "category": "바울서신"},
    "고린도전서": {"book_id": 46, "chapters": 16, "testament": "NT", "category": "바울서신"},
    "고린도후서": {"book_id": 47, "chapters": 13, "testament": "NT", "category": "바울서신"},
    "갈라디아서": {"book_id": 48, "chapters": 6, "testament": "NT", "category": "바울서신"},
    "에베소서": {"book_id": 49, "chapters": 6, "testament": "NT", "category": "바울서신"},
    "빌립보서": {"book_id": 50, "chapters": 4, "testament": "NT", "category": "바울서신"},
    "골로새서": {"book_id": 51, "chapters": 4, "testament": "NT", "category": "바울서신"},
    "데살로니가전서": {"book_id": 52, "chapters": 5, "testament": "NT", "category": "바울서신"},
    "데살로니가후서": {"book_id": 53, "chapters": 5, "testament": "NT", "category": "바울서신"},
    "디모데전": {"book_id": 54, "chapters": 6, "testament": "NT", "category": "목회서신"},
    "디모데후": {"book_id": 55, "chapters": 4, "testament": "NT", "category": "목회서신"},
    "디도": {"book_id": 56, "chapters": 3, "testament": "NT", "category": "목회서신"},
    "빌레몬": {"book_id": 57, "chapters": 1, "testament": "NT", "category": "바울서신"},
    # NT 일반 서신
    "히브리서": {"book_id": 58, "chapters": 13, "testament": "NT", "category": "일반서신"},
    "야고보서": {"book_id": 59, "chapters": 5, "testament": "NT", "category": "일반서신"},
    "베드로전서": {"book_id": 60, "chapters": 5, "testament": "NT", "category": "일반서신"},
    "베드로후서": {"book_id": 61, "chapters": 5, "testament": "NT", "category": "일반서신"},
    "요한일서": {"book_id": 62, "chapters": 5, "testament": "NT", "category": "요한서신"},
    "요한이서": {"book_id": 63, "chapters": 1, "testament": "NT", "category": "요한서신"},
    "요한삼서": {"book_id": 64, "chapters": 1, "testament": "NT", "category": "요한서신"},
    "유다": {"book_id": 65, "chapters": 1, "testament": "NT", "category": "일반서신"},
    # NT 예언서
    "요한계시록": {"book_id": 66, "chapters": 22, "testament": "NT", "category": "예언서"},
}

# 성경 권별 핵심 주제 (진리)
BOOK_THEMES = {
    "창세기": {"theme": "창조와 언약", "core_truth": "하나님은 만물을 창조하시고 아브라함과 언약을 맺으심", "keywords": ["창조", "언약", "믿음", "약속", "시작"]},
    "출애굽기": {"theme": "해방과 율법", "core_truth": "하나님은 백성을 종의 집에서 해방하시고 시나이에서 율법을 주심", "keywords": ["해방", "율법", "구원", "언약", "거룩"]},
    "레위기": {"theme": "거룩함과 예배", "core_truth": "하나님은 백성이 거룩하게 살도록 제사와 예배 방식을 정하심", "keywords": ["거룩", "제사", "정결", "예배", "헌신"]},
    "민수기": {"theme": "광야의 여정", "core_truth": "하나님은 불순한 백성을 인도하시지만 약속의 땅으로 이끌어가심", "keywords": ["인도", "불순", "광야", "진리", "주권"]},
    "신명기": {"theme": "사랑과 순종", "core_truth": "하나님을 사랑하고 명령을 지키는 것이 복의 길", "keywords": ["사랑", "순종", "명령", "복", "회복"]},
    "여호수아": {"theme": "약속의 성취", "core_truth": "하나님은 믿은 자에게 약속의 땅을 상속하심", "keywords": ["약속", "정복", "용기", "상속", "신뢰"]},
    "사사기": {"theme": "죄와 회복", "core_truth": "백성이 죄에 빠지면 하나님이 심판하시고 회개하면 구원하심", "keywords": ["죄", "심판", "회개", "구원", "방패"]},
    "룻": {"theme": "사랑과 속량", "core_truth": "하나님은 충성스러운 자에게 메시아의 혈통을 준비하심", "keywords": ["사랑", "충성", "속량", "인연", "은혜"]},
    "사무엘상": {"theme": "하나님의 선택", "core_truth": "사람은 외모로 보지만 하나님은 마음으로 선택하심", "keywords": ["선택", "기름부음", "왕", "믿음", "순종"]},
    "사무엘하": {"theme": "왕국의 확립", "core_truth": "다윗 왕조에게 영원한 왕국을 약속하심", "keywords": ["왕국", "언약", "회개", "통치", "은혜"]},
    "열왕기상": {"theme": "성전과 영광", "core_truth": "하나님은 성전에 임재하시고 지혜로 다스리심", "keywords": ["성전", "임재", "지혜", "기도", "영광"]},
    "열왕기하": {"theme": "심판과 보존", "core_truth": "불순으로 심판을 받으나 하나님은 남은 자를 보존하심", "keywords": ["심판", "남은자", "보존", "회복", "예수"]},
    "역대상": {"theme": "기억과 계승", "core_truth": "하나님의 역사를 기억하고 다음 세대에 전달함", "keywords": ["기억", "계승", "제사", "찬양", "통계"]},
    "역대하": {"theme": "회개와 회복", "core_truth": "백성이 회개하면 성전이 회복되고 하나님이 응답하심", "keywords": ["회개", "회복", "기도", "성전", "응답"]},
    "에스라": {"theme": "재건과 정결", "core_truth": "성전과 성벽을 재건하고 백성을 정결하게 함", "keywords": ["재건", "정결", "회복", "순종", "기독교"]},
    "느헤미야": {"theme": "성벽 재건", "core_truth": "기도와 실천으로 하나님의 일을 성취함", "keywords": ["기도", "재건", "용기", "지도력", "성공"]},
    "에스더": {"theme": "하나님의 주권", "core_truth": "하나님은 비밀리에 백성을 보호하시고 계획을 성취하심", "keywords": ["주권", "보호", "적응", "위험", "기독교"]},
    "욥": {"theme": "고난과 신뢰", "core_truth": "이해할 수 없는 고난 속에서도 하나님을 신뢰함", "keywords": ["고난", "신뢰", "인내", "주권", "회복"]},
    "시편": {"theme": "찬양과 기도", "core_truth": "모든 상황에서 하나님을 찬양하고 기도하는 삶", "keywords": ["찬양", "기도", "감사", "고난", "구원"]},
    "잠언": {"theme": "지혜와 생활", "core_truth": "여호와를 경외하는 것이 지혜의 시작이며 일상에서 실천함", "keywords": ["지혜", "경외", "생활", "교훈", "분별"]},
    "전도서": {"theme": "삶의 의미", "core_truth": "모든 것이 시가 있으며 하나님을 두려워함이 사람의 본분", "keywords": ["의미", "시간", "허무", "하나님", "목적"]},
    "아가": {"theme": "신앙의 사랑", "core_truth": "하나님과 백성 사이의 깊은 사랑을 시적으로 표현", "keywords": ["사랑", "결혼", "열정", "아름다움", "관계"]},
    "이사야": {"theme": "심판과 구원", "core_truth": "심판 후 메시아가 와서 새로운 시대를 열으심", "keywords": ["메시아", "심판", "구원", "예언", "평화"]},
    "예레미야": {"theme": "새 언약", "core_truth": "파괴 후 새 마음을 베푸시는 하나님의 새 언약", "keywords": ["새언약", "회복", "망명", "기독교", "소망"]},
    "예레미야애가": {"theme": "통회와 위로", "core_truth": "재앙 중에서도 하나님의 인자와 자비를 기억함", "keywords": ["통회", "애곡", "위로", "인자", "소망"]},
    "에스겔": {"theme": "영적인 회복", "core_truth": "마른 뼈처럼 죽은 자성도 하나님의 영으로 살아남", "keywords": ["영", "회복", "생명", "영광", "예수"]},
    "다니엘": {"theme": "신앙의 충성", "core_truth": "어떤 상황에서도 하나님께 충성하면 하나님이 보호하심", "keywords": ["충성", "보호", "환상", "예언", "승리"]},
    "호세아": {"theme": "하나님의 사랑", "core_truth": "배신당한 하나님의 변치 않는 사랑을 예언으로 보여줌", "keywords": ["사랑", "배신", "회개", "용서", "결혼"]},
    "요엘": {"theme": "성령과 심판", "core_truth": "주의 날에 성령을 부어 모든 사람에게 구원을 주심", "keywords": ["성령", "심판", "부어하심", "구원", "예수"]},
    "아모스": {"theme": "정의와 공의", "core_truth": "하나님은 종교적 외식과 사회적 불의를 심판하심", "keywords": ["정의", "공의", "심판", "외식", "회개"]},
    "오바댜": {"theme": "교만과 겸손", "core_truth": "교만한 자는 심판받고 겸손한 자는 구원받음", "keywords": ["교만", "심판", "에돔", "겸손", "구원"]},
    "요나": {"theme": "자비와 회개", "core_truth": "하나님은 모든 민족의 회개를 기다리시고 자비하심", "keywords": ["자비", "회개", "명종", "니느바", "복음"]},
    "미가": {"theme": "정의와 겸손", "core_truth": "정의롭게 행하고 겸손히 하나님과 동행함", "keywords": ["정의", "겸손", "메시아", "벧레헴", "동행"]},
    "나훔": {"theme": "하나님의 심판", "core_truth": "하나님은 의로우시니 악한 자를 반드시 심판하심", "keywords": ["심판", "니네베", "의", "분노", "정의"]},
    "하박국": {"theme": "믿음과 의", "core_truth": "의인은 믿음으로 살며 하나님은 때를 정하여 심판하심", "keywords": ["믿음", "의", "질문", "답", "기다림"]},
    "스바냐": {"theme": "주의 날", "core_truth": "주의 날이 오나 남은 자가 있어 회복됨", "keywords": ["주의날", "심판", "남은자", "회복", "찬양"]},
    "학개": {"theme": "성전 재건", "core_truth": "하나님의 집을 먼저 구하면 모든 것이 복을 받음", "keywords": ["재건", "우선", "영광", "격려", "약속"]},
    "스가랴": {"theme": "메시아의 도래", "core_truth": "하나님은 메시아를 통해 나라를 회복하고 다스리심", "keywords": ["메시아", "회복", "제사장", "왕", "영광"]},
    "말라기": {"theme": "십일조와 언약", "core_truth": "십일조를 드리면 하나님이 복의 문을 열고 부으심", "keywords": ["십일조", "복", "언약", "회개", "엘리야"]},
    "마태복음": {"theme": "왕국의 설교", "core_truth": "예수님은 산상설교로 하나님의 왕국 가치를 가르침", "keywords": ["산상설교", "왕국", "복", "제자", "가치"]},
    "마가복음": {"theme": "종으로서의 예수", "core_truth": "예수님은 많은 사람을 구원하기 위해 종으로 사심", "keywords": ["종", "봉사", "고난", "제자", "희생"]},
    "누가복음": {"theme": "구원의 보편성", "core_truth": "예수님은 잃어버린 자를 찾아 모든 사람에게 구원을 베풀심", "keywords": ["구원", "잃어버린", "자비", "기도", "성령"]},
    "요한복음": {"theme": "신앙과 생명", "core_truth": "예수 그리스도를 믿으면 영생을 얻고 하나님의 아들이 됨", "keywords": ["영생", "믿음", "생명", "광명", "사랑"]},
    "사도행전": {"theme": "성령과 교회", "core_truth": "성령이 사도들을 통해 교회를 세우고 복음을 전파함", "keywords": ["성령", "교회", "전도", "기적", "고난"]},
    "로마서": {"theme": "복음의 능력", "core_truth": "복음은 모든 믿는 자에게 구원의 힘이 됨", "keywords": ["복음", "구원", "믿음", "의", "율법"]},
    "고린도전서": {"theme": "교회의 통일", "core_truth": "교회는 그리스도의 몸으로 통일되고 사랑으로 운영됨", "keywords": ["사랑", "몸", "통일", "은사", "거룩"]},
    "고린도후서": {"theme": "고난과 능력", "core_truth": "약함 가운데 그리스도의 능력이 나타나심", "keywords": ["능력", "약함", "고난", "격려", "자비"]},
    "갈라디아서": {"theme": "기독교의 자유", "core_truth": "그리스도 안에서 얻은 자유로 성령의 열매를 맺음", "keywords": ["자유", "성령", "열매", "율법", "믿음"]},
    "에베소서": {"theme": "교회의 신비", "core_truth": "교회는 그리스도의 몸으로 모든 민족을 포용함", "keywords": ["신비", "몸", "통일", "영적무기", "은혜"]},
    "빌립보서": {"theme": "기쁨의 생활", "core_truth": "그리스도를 아는 지식이 모든 기쁨의 근원이 됨", "keywords": ["기쁨", "그리스도", "종교", "감사", "평안"]},
    "골로새서": {"theme": "그리스도의 우위", "core_truth": "그리스도는 모든 것 위에 계시니 세상 철학을 배격함", "keywords": ["우위", "만물", "철학", "충만", "지혜"]},
    "데살로니가전서": {"theme": "재림의 소망", "core_truth": "주의 재림을 소망하며 경건하게 살음", "keywords": ["재림", "소망", "경건", "기도", "권면"]},
    "데살로니가후서": {"theme": "주의 날 준비", "core_truth": "주의 날이 갑자기 오니 준비하여 경건히 살음", "keywords": ["주의날", "준비", "교만", "일", "경건"]},
    "디모데전": {"theme": "교회의 질서", "core_truth": "건강한 교리와 거룩한 생활로 교회를 다스림", "keywords": ["질서", "기도", "거룩", "지도력", "기독교"]},
    "디모데후": {"theme": "믿음의 유산", "core_truth": "좋은 싸움 싸우고 달려가고 믿음을 지킴", "keywords": ["싸움", "달려감", "믿음", "유산", "충성"]},
    "디도": {"theme": "건강한 교리", "core_truth": "바른 교리로 선을 행하고 모든 사람을 위한 기도", "keywords": ["교리", "선", "기도", "질서", "은혜"]},
    "빌레몬": {"theme": "용서와 화해", "core_truth": "그리스도 안에서 주종 관계를 넘어 형제로 용서함", "keywords": ["용서", "화해", "형제", "사랑", "자유"]},
    "히브리서": {"theme": "더 나은 약속", "core_truth": "그리스도의 제사는 완전하므로 옛 언약은 필요 없음", "keywords": ["제사", "완전", "믿음", "약속", "더나음"]},
    "야고보서": {"theme": "행하는 믿음", "core_truth": "믿음은 행수로 나타나며 시험 가운데 인내함", "keywords": ["행위", "시험", "인내", "지혜", "기도"]},
    "베드로전서": {"theme": "거룩한 삶", "core_truth": "거룩한 제사장으로 살아 하나님의 아름다움을 알림", "keywords": ["거룩", "제사장", "고난", "영광", "복음"]},
    "베드로후서": {"theme": "바른 지식", "core_truth": "주의 오심을 기억하며 바른 지식으로 살음", "keywords": ["지식", "오심", "거짓", "인내", "영광"]},
    "요한일서": {"theme": "사랑과 조명", "core_truth": "하나님은 사랑이시니 서로 사랑하면 하나님 안에 거함", "keywords": ["사랑", "조명", "진리", "기도", "생명"]},
    "요한이서": {"theme": "진리와 사랑", "core_truth": "진리 안에서 사랑하며 거짓을 분별함", "keywords": ["진리", "사랑", "분별", "거짓", "권면"]},
    "요한삼서": {"theme": "영적인 교제", "core_truth": "진리를 위해 서로 교제하며 돕는 것이 복", "keywords": ["교제", "돕음", "진리", "영적", "선"]},
    "유다": {"theme": "믿음의 싸움", "core_truth": "믿음을 지키고 거짓 교사를 분별하여 하나님께 영광", "keywords": ["싸움", "분별", "거짓", "보존", "영광"]},
    "요한계시록": {"theme": "새 하늘과 새 땅", "core_truth": "하나님은 모든 것을 새롭게 하시고 의인들을 영원으로 모심", "keywords": ["새하늘", "새땅", "예루살렘", "영원", "왕국"]},
}

# 설교 제목 템플릿
SERMON_TITLES = [
    "{passage}에서 발견하는 {theme}",
    "{theme}: {keyword}의 기쁨",
    "{keyword} — {passage}의 핵심 메시지",
    "하나님의 {theme}을(를) 경험하는 삶",
    "{passage}가 말하는 {keyword}의 비밀",
    "{keyword}로 사는 사람의 신앙",
    "{theme} — {keyword}를 통한 하나님의 인도",
    "오늘날 우리에게 말하는 {passage}의 {theme}",
    "{keyword}: {theme}의 실천적 적용",
    "믿음의 여정: {passage}와 {theme}",
    "{theme}의 신학적 기초 — {passage} 연구",
    "{keyword}가 바꾸는 삶의 방향",
    "하나님의 {theme}과(와) 우리의 응답",
    "{passage}에서 배우는 {keyword}의 지혜",
    "{theme} — {keyword}로 완성되는 신앙",
    "복음의 본질: {passage}의 {theme}",
    "{keyword}의 힘으로 사는 성도",
    "{theme}을(를) 통한 하나님의 은혜",
    "성경이 가르치는 {keyword}의 진정한 의미",
    "{passage}가 전하는 {theme}의 소망",
]

# 설교 본문 참조 형식
PASSAGE_FORMATS = [
    "{book} {chapter}장 {verse}절",
    "{book} {chapter}:{verse}",
    "{book} {chapter}장",
    "{book} {chapter}편 {verse}절",  # 시편용
]

# 한국 대형교회 설교 제목 스타일
KOREAN_SERMON_STYLES = [
    "새로운 시작: {passage}의 {theme}",
    "{keyword} — {passage}가 주는 메시지",
    "{passage}에서 찾은 {theme}의 길",
    "하나님의 {theme}: {keyword}로 가는 길",
    "{theme}의 기적: {keyword}의 힘",
    "오늘의 설교: {passage}와 {theme}",
    "{keyword}의 놀라운 경험 — {passage}",
    "믿음의 도약: {passage}의 {theme}",
    "{theme}을(를) 통한 회복과 치유",
    "{keyword}로 여는 새로운 시대",
]

# 영어 설교 제목 스타일 (국제 교회)
ENGLISH_SERMON_TITLES = [
    "Finding {theme} in {passage}",
    "{theme}: The Power of {keyword}",
    "Living by {keyword} — A Study of {passage}",
    "God's {theme} and Our Response",
    "The Hidden Meaning of {keyword} in {passage}",
    "{keyword}: Transforming Your Life Through {passage}",
    "Discovering {theme} in the Word of God",
    "Walking by {keyword} — Lessons from {passage}",
    "The Hope of {theme}: A Message from {passage}",
    "Embracing {keyword}: God's Plan Revealed",
]


def generate_passage_reference(book_name: str, book_info: Dict) -> List[str]:
    """성경 권과 장/절 번호로 본문 참조를 생성합니다"""
    references = []
    max_chapters = min(book_info["chapters"], 50)  # 너무 많은 장은 생략
    
    for chapter in range(1, max_chapters + 1):
        # 시편은 편 단위, 요한계시록은 장 단위
        if book_name == "시편":
            verse = random.choice([1, 4, 7, 10, 14, 18, 23, 27, 32, 37, 42, 51, 66, 91, 103, 119, 139, 150])
            ref = f"{book_name} {chapter}편 {verse}절"
        else:
            verse = random.choice([1, 5, 10, 16, 23, 28, 32, 42, 51])
            ref = f"{book_name} {chapter}장 {verse}절"
        references.append(ref)
    
    return references


def extract_chapter(passage_ref: str) -> int:
    """본문 참조에서 장 번호를 추출합니다"""
    parts = passage_ref.split()
    for part in parts:
        # 숫자로 시작하는 부분 찾기
        cleaned = part.replace("장", "").replace("편", "").replace("절", "")
        if cleaned.isdigit():
            return int(cleaned)
    return 1


def generate_sermon_record(
    record_id: int,
    book_name: str,
    book_info: Dict,
    passage_ref: str,
    source: str = "seed",
    use_korean_style: bool = True,
) -> Dict:
    """단일 설교 레코드를 생성합니다"""
    theme_info = BOOK_THEMES.get(book_name, {"theme": "성경의 교훈", "core_truth": "하나님의 말씀을 통해 배우는 삶의 지혜", "keywords": ["믿음", "순종", "기도"]})
    
    # 키워드 3-5개 선택
    keywords = theme_info["keywords"].copy()
    if len(keywords) > 5:
        random.shuffle(keywords)
        keywords = keywords[:5]
    
    # 제목 생성
    template = random.choice(KOREAN_SERMON_STYLES if use_korean_style else ENGLISH_SERMON_TITLES)
    title = template.format(
        passage=passage_ref,
        theme=theme_info["theme"],
        keyword=random.choice(keywords),
    )
    
    # 날짜 생성 (2020-2026 사이)
    year = random.randint(2020, 2026)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    collected_at = f"{year}-{month:02d}-{day:02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
    
    # bible_book은 FrequencyAnalyzer 매핑과 호환되도록 전체명 사용
    # 한국어 전체명 (FrequencyAnalyzer.KOREAN_ABBREVIATIONS에 등록됨)
    bible_book_full = book_name
    
    return {
        "record_id": f"seed_{record_id:06d}",
        "source": source,
        "title": title,
        "passage_raw": passage_ref,
        "bible_book": bible_book_full,
        "chapter_start": extract_chapter(passage_ref),
        "verse_start": random.choice([1, 5, 10, 16]),
        "testament": book_info["testament"],
        "book_category": book_info["category"],
        "theme": theme_info["theme"],
        "core_truth": theme_info["core_truth"],
        "keywords": keywords,
        "collected_at": collected_at,
    }


def generate_large_seed_dataset(
    target_count: int = 100000,
        output_path: str | None = None,
) -> List[Dict]:
    """
    대규모 시드 데이터셋을 생성합니다.
    
    Args:
        target_count: 목표 건수 (기본값: 100,000)
        output_path: 출력 파일 경로
    
    Returns:
        생성된 레코드 목록
    """
    if output_path is None:
        output_path = "data/sermon_corpus/raw/large_seed_sermons.jsonl"
    
    records = []
    record_id = 1
    
    # 각 권별로 균등하게 분배
    books_list = list(BIBLE_BOOKS.items())
    total_books = len(books_list)
    per_book = max(target_count // total_books, 100)  # 최소 100건/권
    
    print(f"총 {total_books}개 권에서 각 {per_book}건 생성 중...")
    
    for book_name, book_info in books_list:
        if record_id > target_count:
            break
        
        print(f"  {book_name} ({book_info['chapters']}장) 생성 중...")
        
        # 본문 참조 생성
        passages = generate_passage_reference(book_name, book_info)
        
        # 목표 건수까지 생성
        for _ in range(per_book):
            if record_id > target_count:
                break
            
            passage = random.choice(passages)
            
            # 80% 한국어, 20% 영어 스타일
            use_ko = random.random() < 0.8
            record = generate_sermon_record(
                record_id=record_id,
                book_name=book_name,
                book_info=book_info,
                passage_ref=passage,
                source="seed",
                use_korean_style=use_ko,
            )
            records.append(record)
            record_id += 1
    
    # 저장
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"\n대규모 시드 데이터 {len(records)}건 저장 완료: {output_path}")
    return records


if __name__ == "__main__":
    generate_large_seed_dataset(target_count=100000)
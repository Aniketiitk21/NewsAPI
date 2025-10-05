from typing import Dict, List

# ==== Core config ============================================================

INDIA_STATES: List[str] = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
    "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
    "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
    "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh",
    "Uttarakhand","West Bengal","Delhi","Jammu and Kashmir","Ladakh","Puducherry","Chandigarh"
]

# Set to None if unknown → stance_for_state_politics returns neutral
RULING_PARTY_BY_STATE: Dict[str, str] = {
    "Andhra Pradesh": "TDP",
    "Tamil Nadu": "DMK",
    "Telangana": "INC",
    "Karnataka": "INC",
    "Uttar Pradesh": "BJP",
    "Maharashtra": "Shinde-BJP",
    "Kerala": "LDF",
    "Delhi": "AAP",
}

# ==== Category heuristics (recall over precision) ===========================

CATEGORY_KEYWORDS = {
    "politics": [
        "assembly","minister","cabinet","election","poll","mp","mla","governor",
        "chief minister","cm","party","opposition","government","govt","parliament",
        "policy","yatra","coalition","alliance","ordinance"
    ],
    "sports": [
        "cricket","football","badminton","hockey","kabaddi","olympics","t20","ipl",
        "world cup","stadium","athlete","coach","match","series","medal","tournament"
    ],
    "education": [
        "school","college","university","ugc","cbse","exam","results","admission",
        "scholarship","curriculum","neet","jee","semester","syllabus","nta","hall ticket"
    ],
    "science": [
        "isro","space","satellite","launch","research","ai","artificial intelligence",
        "quantum","bio","vaccine","science","laboratory","csir","iit","scientist",
        "technology","tech","mission","computer vision","deep learning","ml"
    ],
    "business": [
        "market","stock","investors","funding","startup","gdp","inflation","rbi","bank",
        "industry","exports","imports","economy","ipo","merger","acquisition","earnings",
        "results","quarterly","revenue","profit","loss","listing","bonus","split"
    ],
    "entertainment": [
        "film","movie","bollywood","tollywood","kollywood","box office","trailer",
        "actor","actress","web series","song","music","teaser","cinema","OTT"
    ],
}

# Sentiment lexicons for governance stance (very small, interpretable)
POS_WORDS = [
    "support","supports","backs","praised","lauded","ally","clean chit",
    "acquitted","cleared","vindicated","won","victory","benefit","relief",
    "development","boost","approved","sanctioned","inaugurated","launched",
    "implemented","rolled out","granted","allocated","opened","reduced","cut"
]
NEG_WORDS = [
    "slam","slams","critic","criticised","criticized","attack","attacks",
    "probe","arrest","arrested","scam","corruption","blame","charges",
    "fir","raid","accused","allegation","allegations","controversy","irregularities",
    "violations","protest","strike","boycott","backlash","setback","censure","rebuke",
    "delay","stalled","scrapped","fraud","misuse"
]

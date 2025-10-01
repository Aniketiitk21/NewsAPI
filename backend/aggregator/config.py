# backend/aggregator/config.py
from typing import Dict

INDIA_STATES = [
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
    "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
    "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
    "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh",
    "Uttarakhand","West Bengal","Delhi","Jammu and Kashmir","Ladakh","Puducherry","Chandigarh"
]

# Use a simple mapping for Gov≡Party stance; update as needed, or set to None for neutral.
RULING_PARTY_BY_STATE: Dict[str, str] = {
    "Andhra Pradesh": "TDP",
    "Tamil Nadu": "DMK",
    "Telangana": "INC",
    "Karnataka": "INC",
    "Uttar Pradesh": "BJP",
    "Maharashtra": "Shinde-BJP",
    "Kerala": "LDF",
    "Delhi": "AAP",
    # …extend/adjust anytime
}

CATEGORY_KEYWORDS = {
    "politics": ["assembly","minister","cabinet","election","poll","mp","mla","governor",
                 "chief minister","cm","party","opposition","government","govt","parliament",
                 "policy","yatra","coalition","alliance"],
    "sports": ["cricket","football","badminton","hockey","kabaddi","olympics","t20","ipl",
               "world cup","stadium","athlete","coach","match","series","medal","tournament"],
    "education": ["school","college","university","ugc","cbse","exam","results","admission",
                  "scholarship","curriculum","neet","jee","semester","syllabus"],
    "science": ["isro","space","satellite","launch","research","ai","quantum","bio","vaccine",
                "science","laboratory","csir","iit","scientist","technology","tech","mission"],
    "business": ["market","stock","investors","funding","startup","gdp","inflation","rbi","bank",
                 "industry","exports","imports","economy","ipo","merger","acquisition"],
    "entertainment": ["film","movie","bollywood","tollywood","kollywood","box office","trailer",
                      "actor","actress","web series","song","music","teaser","cinema"]
}

POS_WORDS = [
    "support","supports","backs","praised","lauded","ally","clean chit",
    "acquitted","cleared","vindicated","won","victory","benefit","relief",
    "development","boost","approved","sanctioned","inaugurated","launched","implemented","rolled out",
    "granted","allocated","opened"
]
NEG_WORDS = [
    "slam","slams","critic","criticised","criticized","attack","attacks",
    "probe","arrest","arrested","scam","corruption","blame","charges",
    "fir","raid","accused","allegation","allegations","controversy","irregularities",
    "violations","protest","strike","boycott","backlash","setback","censure","rebuke","delay","stalled","scrapped"
]

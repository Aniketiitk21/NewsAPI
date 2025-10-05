from typing import Dict, List

# National feeds
NATIONAL_FEEDS: List[str] = [
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://indianexpress.com/section/india/feed/",
    "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "https://www.ndtv.com/rss",
]

# State feeds (expand slowly; Render free dynos appreciate small lists)
STATE_FEEDS: Dict[str, List[str]] = {
    "Andhra Pradesh": [
        "https://www.thehindu.com/news/national/andhra-pradesh/feeder/default.rss",
        "https://www.newindianexpress.com/States/Andhra-Pradesh/rssfeed/?id=170&getXmlFeed=true",
        "https://www.deccanchronicle.com/rss/andhra-pradesh.xml",
        "https://english.sakshi.com/rss.xml",
        "https://www.thehansindia.com/rss/andhra-pradesh",
    ],
    "Telangana": [
        "https://www.thehindu.com/news/national/telangana/feeder/default.rss",
        "https://www.newindianexpress.com/States/Telangana/rssfeed/?id=182&getXmlFeed=true",
        "https://www.deccanchronicle.com/rss/telangana.xml",
    ],
    "Tamil Nadu": [
        "https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss",
        "https://www.newindianexpress.com/States/Tamil-Nadu/rssfeed/?id=181&getXmlFeed=true",
        "https://www.dtnext.in/rss",
    ],
    "Karnataka": [
        "https://www.thehindu.com/news/national/karnataka/feeder/default.rss",
        "https://www.newindianexpress.com/States/Karnataka/rssfeed/?id=179&getXmlFeed=true",
        "https://www.deccanherald.com/rss-feeds",
    ],
    "Kerala": [
        "https://www.thehindu.com/news/national/kerala/feeder/default.rss",
        "https://www.newindianexpress.com/States/Kerala/rssfeed/?id=178&getXmlFeed=true",
    ],
    "Maharashtra": [
        "https://www.thehindu.com/news/national/other-states/feeder/default.rss",
        "https://indianexpress.com/section/cities/mumbai/feed/",
        "https://www.hindustantimes.com/feeds/rss/cities/mumbai-news/rssfeed.xml",
    ],
    "Gujarat": [
        "https://indianexpress.com/section/cities/ahmedabad/feed/",
        "https://timesofindia.indiatimes.com/rssfeeds/3947065.cms",
    ],
    "Uttar Pradesh": [
        "https://www.hindustantimes.com/feeds/rss/cities/lucknow-news/rssfeed.xml",
        "https://timesofindia.indiatimes.com/rssfeeds/3947067.cms",
    ],
    "West Bengal": [
        "https://www.hindustantimes.com/feeds/rss/cities/kolkata-news/rssfeed.xml",
        "https://timesofindia.indiatimes.com/rssfeeds/3947063.cms",
    ],
    "Rajasthan": [
        "https://timesofindia.indiatimes.com/rssfeeds/3012544.cms",
        "https://www.hindustantimes.com/feeds/rss/cities/jaipur-news/rssfeed.xml",
    ],
    "Punjab": [
        "https://timesofindia.indiatimes.com/rssfeeds/3947051.cms",
        "https://indianexpress.com/section/cities/chandigarh/feed/",
    ],
    "Haryana": [
        "https://timesofindia.indiatimes.com/rssfeeds/3947066.cms",
        "https://indianexpress.com/section/cities/chandigarh/feed/",
    ],
    "Bihar": [
        "https://timesofindia.indiatimes.com/rssfeeds/3947022.cms",
        "https://www.hindustantimes.com/feeds/rss/cities/patna-news/rssfeed.xml",
    ],
    "Madhya Pradesh": [
        "https://timesofindia.indiatimes.com/rssfeeds/3947060.cms",
        "https://www.hindustantimes.com/feeds/rss/cities/bhopal-news/rssfeed.xml",
    ],
    "Odisha": [
        "https://www.newindianexpress.com/States/Odisha/rssfeed/?id=175&getXmlFeed=true",
        "https://timesofindia.indiatimes.com/rssfeeds/3947061.cms",
    ],
    "Assam": [
        "https://timesofindia.indiatimes.com/rssfeeds/3947069.cms",
        "https://indianexpress.com/section/north-east-india/feed/",
    ],
    "Delhi": [
        "https://indianexpress.com/section/cities/delhi/feed/",
        "https://www.hindustantimes.com/feeds/rss/cities/delhi-news/rssfeed.xml",
        "https://timesofindia.indiatimes.com/rssfeeds/3947062.cms",
    ],
}

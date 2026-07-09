"""
Domain Knowledge Base for Query Enrichment

Maps user query topics to high-authority domains for targeted search.
The classifier is rule-based (no LLM, no API calls) using keyword matching
with weighted category scoring. The top-matching topic's domains are appended
as site: filters to improve search result quality.
"""

from typing import Dict, List, Optional, Tuple
import logging
import re


class TopicDomain:
    def __init__(
        self,
        name: str,
        keywords: List[str],
        sub_keywords: Dict[str, List[str]],
        domains: List[str],
        priority: int = 5,
    ):
        self.name = name
        self.keywords = keywords
        self.sub_keywords = sub_keywords
        self.domains = domains
        self.priority = priority


TOPIC_DATABASE: List[TopicDomain] = [
    # ============================================================
    # SHOPPING / E-COMMERCE / PRICE COMPARISON
    # ============================================================
    TopicDomain(
        name="shopping",
        keywords=[
            "buy", "price", "cheap", "deal", "discount", "cost", "affordable",
            "purchase", "shop", "retail", "store", "online store", "marketplace",
            "bargain", "sale", "clearance", "offer", "coupon", "promo",
            "shipping", "delivery", "order", "cart", "checkout",
            "under €", "under $", "under £", "under euro", "under dollar",
            "under eur", "under usd", "under gbp", "euros", "dollars",
            "best price", "lowest price", "compare price", "price comparison",
            "preisvergleich", "günstig", "billig", "rabatt", "angebot",
            "top 5", "top 10", "best 5", "best 10", "recommended",
            "should i buy", "which", "best", "top",
        ],
        sub_keywords={
            "electronics": [
                "smartphone", "laptop", "tablet", "headphone", "earbuds",
                "monitor", "tv", "television", "camera", "console",
                "gadget", "tech", "electronic", "computer", "notebook",
                "processor", "gpu", "graphics card", "ssd", "hard drive",
                "router", "speaker", "smart home", "wearable", "smartwatch",
            ],
            "clothing": [
                "shirt", "dress", "jeans", "jacket", "shoe", "sneaker",
                "fashion", "clothing", "apparel", "outfit", "coat",
                "trousers", "hoodie", "sweater", "boots", "accessory",
            ],
            "home": [
                "furniture", "sofa", "bed", "table", "chair", "lamp",
                "decor", "kitchen", "appliance", "vacuum", "microwave",
                "refrigerator", "washing machine", "dryer", "dishwasher",
            ],
            "books": [
                "book", "textbook", "novel", "kindle", "ebook",
                "bestseller", "paperback", "hardcover",
            ],
        },
        domains=[
            "amazon.de", "amazon.com", "amazon.co.uk",
            "ebay.de", "ebay.com", "ebay-kleinanzeigen.de",
            "idealo.de", "geizhals.de", "geizhals.eu",
            "otto.de", "zalando.de", "zalando.com",
            "mediamarkt.de", "saturn.de", "notebooksbilliger.de",
            "computeruniverse.de", "cyberport.de", "alternate.de",
            "retailmenot.com", "honey.com", "coupons.com",
            "bestbuy.com", "walmart.com", "target.com",
            "costco.com", "kohl.com", "macys.com",
            "alibaba.com", "aliexpress.com", "wish.com",
            "etsy.com", "shopify.com",
            "pricegrabber.com", "shopzilla.com", "nextag.com",
            "camelcamelcamel.com", "keepa.com",
            "mydealz.de", "dealdoktor.de", "sparwelt.de",
        ],
    ),

    # ============================================================
    # FINANCE / INVESTING / BANKING
    # ============================================================
    TopicDomain(
        name="finance",
        keywords=[
            "stock", "share", "market", "trading", "invest", "investment",
            "portfolio", "dividend", "nasdaq", "dow jones", "s&p 500",
            "etf", "mutual fund", "bond", "commodity", "futures",
            "option", "crypto", "cryptocurrency", "bitcoin", "ethereum",
            "blockchain", "defi", "nft", "token",
            "bank", "banking", "account", "interest rate", "mortgage",
            "loan", "credit", "credit card", "debt", "savings",
            "retirement", "401k", "ira", "roth", "pension",
            "forex", "fx", "currency", "exchange rate",
            "inflation", "gdp", "economic", "economy", "recession",
            "ipo", "earnings", "quarterly", "annual report",
            "balance sheet", "income statement", "cash flow",
            "broker", "robinhood", "schwab", "fidelity", "vanguard",
            "capital gains", "tax", "finance", "financial",
            "aktie", "börse", "anlage", "investition", "kapital",
            "steuer", "finanzamt", "kredit", "versicherung",
        ],
        sub_keywords={
            "us_stocks": [
                "nyse", "nasdaq", "wall street", "dow", "s&p",
                "apple stock", "microsoft stock", "google stock",
                "nvda", "aapl", "msft", "googl", "amzn", "meta",
            ],
            "crypto": [
                "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
                "cardano", "ada", "polkadot", "dot", "chainlink",
                "crypto trading", "crypto exchange", "binance", "coinbase",
                "defi", "decentralized finance", "yield farming", "staking",
                "nft", "blockchain", "web3", "token", "altcoin",
            ],
            "real_estate": [
                "mortgage", "home loan", "refinance", "rental property",
                "real estate investment", "reit", "property market",
                "housing market", "home price", "real estate agent",
            ],
            "retirement": [
                "401k", "ira", "roth ira", "traditional ira", "pension",
                "retirement planning", "social security", "annuity",
            ],
        },
        domains=[
            "finance.yahoo.com", "yahoo.com/finance",
            "reuters.com", "bloomberg.com", "cnbc.com",
            "marketwatch.com", "investopedia.com",
            "morningstar.com", "seekingalpha.com",
            "fool.com", "thestreet.com", "barrons.com",
            "ft.com", "wsj.com", "economist.com",
            "coindesk.com", "cointelegraph.com",
            "tradingview.com", "finviz.com",
            "sec.gov", "nasdaq.com", "nyse.com",
            "finanzen.net", "boerse-online.de",
            "handelsblatt.com", "manager-magazin.de",
            "wiwo.de", "finance.google.com",
            "bankrate.com", "nerdwallet.com", "creditkarma.com",
            "mint.com", "personalcapital.com",
            "kaggle.com", "quantopian.com",
        ],
    ),

    # ============================================================
    # TECHNOLOGY / COMPUTING / SOFTWARE
    # ============================================================
    TopicDomain(
        name="technology",
        keywords=[
            "technology", "tech", "software", "hardware", "computer",
            "programming", "code", "coding", "developer", "development",
            "app", "application", "website", "web", "cloud", "saas",
            "api", "framework", "library", "language", "compiler",
            "algorithm", "data structure", "database", "sql", "nosql",
            "microservice", "docker", "kubernetes", "devops", "ci/cd",
            "linux", "windows", "macos", "ubuntu", "debian",
            "android", "ios", "mobile", "cross-platform",
            "frontend", "backend", "fullstack", "stack",
            "machine learning", "deep learning", "ai", "artificial intelligence",
            "neural network", "gpt", "llm", "transformer", "model",
            "data science", "analytics", "big data", "data engineering",
            "cybersecurity", "security", "encryption", "hacking",
            "network", "server", "infrastructure", "hosting",
            "blockchain", "web3", "smart contract", "solidity",
            "operating system", "kernel", "driver", "firmware",
            "open source", "github", "gitlab", "bitbucket",
            "rest api", "graphql", "grpc", "websocket",
            "testing", "qa", "quality assurance", "automation",
            "agile", "scrum", "jira", "confluence", "notion",
            "virtualization", "vmware", "virtualbox", "hypervisor",
        ],
        sub_keywords={
            "ai_ml": [
                "machine learning", "deep learning", "neural network",
                "tensorflow", "pytorch", "keras", "scikit-learn",
                "nlp", "natural language", "computer vision", "cv",
                "llm", "large language model", "gpt", "bert", "transformer",
                "diffusion model", "gan", "reinforcement learning",
                "embeddings", "rag", "retrieval augmented generation",
                "fine-tuning", "training", "inference", "tokenization",
                "vector database", "chromadb", "pinecone", "weaviate",
                "huggingface", "civitai", "replicate", "together.ai",
            ],
            "programming": [
                "python", "javascript", "typescript", "java", "c++", "c#",
                "go", "golang", "rust", "swift", "kotlin", "ruby", "php",
                "react", "vue", "angular", "svelte", "nextjs", "nuxt",
                "node", "deno", "bun", "express", "fastify", "django",
                "flask", "fastapi", "spring", "rails", "laravel",
                "sql", "postgresql", "mysql", "mongodb", "redis",
                "docker", "kubernetes", "terraform", "ansible",
            ],
            "cybersecurity": [
                "cybersecurity", "security", "hacking", "penetration testing",
                "vulnerability", "cve", "exploit", "malware", "ransomware",
                "firewall", "ids", "ips", "siem", "soc", "zero trust",
                "authentication", "authorization", "oauth", "jwt",
                "encryption", "aes", "rsa", "tls", "ssl", "https",
            ],
        },
        domains=[
            "github.com", "gitlab.com", "bitbucket.org",
            "stackoverflow.com", "stackexchange.com",
            "medium.com", "dev.to", "hashnode.com",
            "arstechnica.com", "theverge.com",
            "techcrunch.com", "wired.com",
            "hackernews.com", "news.ycombinator.com",
            "reddit.com/r/programming", "reddit.com/r/MachineLearning",
            "reddit.com/r/technology",
            "towardsdatascience.com", "analyticsvidhya.com",
            "kdnuggets.com", "datasciencecentral.com",
            "arxiv.org", "paperswithcode.com",
            "huggingface.co", "modelscope.cn",
            "pytorch.org", "tensorflow.org",
            "python.org", "pip.pypa.io", "pypi.org",
            "npmjs.com", "crates.io", "rubygems.org",
            "docker.com", "kubernetes.io", "helm.sh",
            "cloudflare.com", "aws.amazon.com",
            "docs.microsoft.com", "learn.microsoft.com",
            "oracle.com", "ibm.com", "redhat.com",
            "digitalocean.com", "linode.com", "vultr.com",
            "nginx.com", "apache.org", "nginx.org",
            "mysql.com", "postgresql.org", "mongodb.com",
            "redis.io", "elastic.co", "grafana.com",
            "heise.de", "golem.de", "c't.de",
            "chip.de", "computerbase.de",
        ],
    ),

    # ============================================================
    # SCIENCE / RESEARCH / ACADEMIA
    # ============================================================
    TopicDomain(
        name="science",
        keywords=[
            "research", "study", "scientific", "science", "experiment",
            "paper", "publication", "journal", "peer review",
            "hypothesis", "theory", "discovery", "breakthrough",
            "laboratory", "lab", "clinical trial", "trial",
            "physics", "chemistry", "biology", "astronomy", "geology",
            "mathematics", "math", "statistics", "probability",
            "quantum", "relativity", "genetics", "genome", "dna",
            "evolution", "ecology", "climate", "environment",
            "particle", "nuclear", "fusion", "fission",
            "telescope", "microscope", "spectroscopy",
            "psychology", "neuroscience", "cognitive science",
            "phd", "dissertation", "thesis", "postdoc",
            "citation", "bibliography", "doi", "impact factor",
            "university", "institute", "academia", "scholar",
        ],
        sub_keywords={
            "physics": [
                "quantum mechanics", "particle physics", "string theory",
                "relativity", "cosmology", "astrophysics",
                "nuclear physics", "condensed matter", "photonics",
                "cern", "lhc", "large hadron collider",
            ],
            "biology": [
                "genetics", "genomics", "proteomics", "cell biology",
                "molecular biology", "neuroscience", "ecology",
                "evolution", "microbiology", "immunology",
            ],
            "climate": [
                "climate change", "global warming", "carbon emissions",
                "renewable energy", "solar", "wind", "sustainability",
                "environmental science", "conservation", "biodiversity",
            ],
        },
        domains=[
            "nature.com", "science.org", "sciencedirect.com",
            "springer.com", "wiley.com", "tandfonline.com",
            "arxiv.org", "pubmed.ncbi.nlm.nih.gov",
            "ncbi.nlm.nih.gov", "nih.gov",
            "plos.org", "cell.com", "thelancet.com",
            "nejm.org", "bmj.com", "jamanetwork.com",
            "researchgate.net", "academia.edu",
            "scholar.google.com", "semanticscholar.org",
            "sci-hub.se", "libgen.is",
            "newscientist.com", "scientificamerican.com",
            "phys.org", "eurekalert.org",
            "npr.org/sections/science",
            "bbc.com/news/science",
            "theguardian.com/science",
            "spektrum.de", "wissenschaft.de",
            "mpg.de", "max-planck-gesellschaft",
            "helmholtz.de", "fraunhofer.de",
            "dfg.de", "leopoldina.org",
        ],
    ),

    # ============================================================
    # HEALTH / MEDICINE / WELLNESS
    # ============================================================
    TopicDomain(
        name="health",
        keywords=[
            "symptom", "treatment", "medication", "drug", "medicine",
            "diagnosis", "disease", "illness", "condition", "disorder",
            "doctor", "physician", "hospital", "clinic", "pharmacy",
            "surgery", "therapy", "rehabilitation", "recovery",
            "vaccine", "vaccination", "immunization", "covid",
            "cancer", "diabetes", "heart disease", "hypertension",
            "pain", "fever", "cough", "cold", "flu", "infection",
            "nutrition", "diet", "supplement", "vitamin", "mineral",
            "exercise", "fitness", "workout", "wellness", "health",
            "mental health", "depression", "anxiety", "stress",
            "sleep", "insomnia", "fatigue", "chronic",
            "pregnancy", "childbirth", "pediatric", "infant",
            "allergy", "asthma", "arthritis", "osteoporosis",
            "dental", "tooth", "oral health", "vision", "eye",
            "health insurance", "medicare", "medicaid",
            "gesundheit", "krankheit", "behandlung", "medikament",
            "krankenhaus", "arzt", "apotheke", "krankenkasse",
            "prävention", "vorsorge", "reha", "kur",
        ],
        sub_keywords={
            "medication": [
                "dosage", "side effect", "interaction", "prescription",
                "over the counter", "otc", "generic", "brand name",
                "antibiotic", "antidepressant", "painkiller", "opioid",
                "statin", "blood thinner", "insulin", "inhaler",
                "ibuprofen", "paracetamol", "aspirin",
            ],
            "alternative": [
                "acupuncture", "homeopathy", "naturopathy", "chiropractic",
                "herbal medicine", "essential oil", "supplement",
                "meditation", "yoga", "mindfulness", "ayurveda",
            ],
            "mental_health": [
                "depression", "anxiety", "bipolar", "ptsd", "ocd",
                "adhd", "autism", "therapy", "counseling", "psychiatrist",
                "psychologist", "cognitive behavioral", "cbt",
            ],
        },
        domains=[
            "who.int", "cdc.gov", "nih.gov", "nlm.nih.gov",
            "mayoclinic.org", "clevelandclinic.org",
            "webmd.com", "healthline.com", "verywellhealth.com",
            "medscape.com", "uptodate.com",
            "pubmed.ncbi.nlm.nih.gov", "cochrane.org",
            "fda.gov", "ema.europa.eu",
            "nih.gov/medlineplus",
            "nhs.uk", "ninds.nih.gov",
            "apotheken-umschau.de", "gesundheitsinformation.de",
            "aerzteblatt.de", "apotheke.advent.de",
            "msdmanuals.com", "msdmanuals.de",
            "psychiatry.org", "apa.org",
            "diabetes.org", "heart.org", "cancer.org",
            "nationalmssociety.org", "alz.org",
            "everydayhealth.com", "medicinenet.com",
            "rxlist.com", "drugs.com",
            "sportmedizin.de", "gesundheit.de",
        ],
    ),

    # ============================================================
    # NEWS / CURRENT EVENTS / POLITICS
    # ============================================================
    TopicDomain(
        name="news",
        keywords=[
            "news", "breaking", "headline", "report", "coverage",
            "today", "this week", "this month", "latest", "update",
            "announced", "declared", "launch", "revealed", "unveiled",
            "election", "president", "prime minister", "government",
            "parliament", "congress", "policy", "legislation", "law",
            "war", "conflict", "attack", "protest", "sanction",
            "treaty", "summit", "diplomacy", "foreign policy",
            "economy", "trade", "tariff", "regulation", "deregulation",
            "supreme court", "judge", "ruling", "verdict",
            "scandal", "investigation", "inquiry", "hearing",
            "press release", "press conference", "interview",
            "crisis", "disaster", "emergency", "relief",
            "aktuell", "nachrichten", "bericht", "meldung",
            "politik", "regierung", "wahl", "bundestag",
        ],
        sub_keywords={
            "politics": [
                "election", "president", "vote", "campaign",
                "congress", "senate", "parliament", "legislation",
                "political party", "democrat", "republican",
                "lobby", "campaign finance", "poll", "survey",
            ],
            "world": [
                "ukraine", "russia", "china", "usa", "europe",
                "middle east", "asia", "africa", "latin america",
                "united nations", "nato", "european union",
                "international", "global", "world affairs",
            ],
            "business": [
                "merger", "acquisition", "ipo", "market",
                "corporation", "ceo", "startup", "funding",
                "layoff", "hiring", "revenue", "profit",
            ],
        },
        domains=[
            "reuters.com", "apnews.com",
            "bbc.com", "bbc.co.uk", "bbc.com/news",
            "cnn.com", "nytimes.com", "washingtonpost.com",
            "wsj.com", "ft.com", "bloomberg.com",
            "theguardian.com", "economist.com",
            "politico.com", "thehill.com", "axios.com",
            "npr.org", "pbs.org", "cbsnews.com",
            "abcnews.go.com", "nbcnews.com",
            "aljazeera.com", "france24.com", "dw.com",
            "spiegel.de", "zeit.de", "faz.net", "sueddeutsche.de",
            "tagesschau.de", "welt.de", "t-online.de",
            "n-tv.de", "stern.de", "focus.de",
            "berliner-zeitung.de", "rbb24.de",
            "euronews.com", "scmp.com", "nikkei.com",
            "thelocal.de", "deutschlandfunk.de",
            "tagesspiegel.de", "morgenpost.de",
        ],
    ),

    # ============================================================
    # LOCAL / TRAVEL / DINING
    # ============================================================
    TopicDomain(
        name="local",
        keywords=[
            "near me", "in berlin", "in munich", "in hamburg",
            "in cologne", "in frankfurt", "in stuttgart", "in düsseldorf",
            "nearby", "local", "neighborhood", "district", "area",
            "berlin", "munich", "berlin mitte", "kreuzberg", "neukölln",
            "prenzlauer berg", "friedrichshain", "schöneberg",
            "restaurant", "café", "bar", "club", "pub", "bakery",
            "hotel", "hostel", "accommodation", "lodging",
            "attraction", "museum", "gallery", "park", "landmark",
            "tour", "tourist", "sightseeing", "guide",
            "transport", "train", "bus", "ubahn", "sbahn", "taxi",
            "station", "airport", "flight", "ticket",
            "event", "concert", "festival", "exhibition", "show",
            "delivery", "takeout", "takeaway", "reservation",
            "Öffnungszeiten", "adresse", "telefon", "kontakt",
            "kiez", "bezirk", "stadtteil", "ortsteil",
        ],
        sub_keywords={
            "food_dining": [
                "restaurant", "café", "bistro", "diner", "food",
                "lunch", "dinner", "breakfast", "brunch",
                "italian", "chinese", "japanese", "vietnamese",
                "thai", "indian", "mexican", "german", "turkish",
                "pizza", "pasta", "sushi", "burger", "döner",
                "vegan", "vegetarian", "halal", "kosher",
                "michelin", "gourmet", "fine dining", "street food",
            ],
            "transport": [
                "train", "bus", "subway", "ubahn", "sbahn",
                "tram", "taxi", "uber", "rental", "bike",
                "parking", "ticket", "schedule", "route",
                "deutsche bahn", "bvg", "berlin transport",
            ],
            "shopping_local": [
                "market", "flea market", "farmer market", "mall",
                "boutique", "antique", "thrift", "second hand",
                "flohmarkt", "kaDeWe", "alexanderplatz",
            ],
        },
        domains=[
            "google.com/maps", "maps.google.com",
            "yelp.com", "yelp.de", "tripadvisor.com",
            "tripadvisor.de", "booking.com",
            "airbnb.com", "expedia.com", "hotels.com",
            "trivago.de", "kayak.com", "skyscanner.net",
            "rome2rio.com", "omio.com",
            "visitberlin.de", "berlin.de", "berlin-tourismus.de",
            "berliner-verkehr.de", "bvg.de", "vbb.de",
            "bahn.de", "deutschebahn.com",
            "ebay-kleinanzeigen.de", "quoka.de",
            "meinestadt.de", "dasoertliche.de",
            "gelbeseiten.de", "11880.com",
            "restaurant-kritik.de", "speisekarte.de",
            "lieferando.de", "wolt.com", "uber-eats.com",
            "city-map.com", "stadtplandienst.de",
            "foursquare.com", "untappd.com",
            "opentable.com", "resy.com",
            "immobilienscout24.de", "wg-gesucht.de",
        ],
    ),

    # ============================================================
    # ENTERTAINMENT / MOVIES / MUSIC
    # ============================================================
    TopicDomain(
        name="entertainment",
        keywords=[
            "movie", "film", "cinema", "theater", "show", "series",
            "netflix", "disney+", "hbo", "prime video", "streaming",
            "music", "song", "album", "artist", "band", "concert",
            "spotify", "apple music", "youtube", "tiktok",
            "tv", "television", "episode", "season", "broadcast",
            "actor", "actress", "director", "producer", "screenplay",
            "review", "rating", "imdb", "rotten tomatoes",
            "award", "oscar", "grammy", "emmy", "golden globe",
            "pop culture", "celebrity", "interview", "behind the scenes",
            "trailer", "teaser", "preview", "coming soon",
            "game show", "reality", "documentary", "docuseries",
            "kino", "filmstart", "blockbuster", "premiere",
        ],
        sub_keywords={
            "movies": [
                "film review", "movie review", "imdb", "rotten tomatoes",
                "box office", "opening weekend", "critic score",
                "best film", "top movie", "must watch",
            ],
            "music": [
                "album review", "song lyrics", "new release",
                "billboard", "charts", "spotify", "playlist",
                "genre", "rock", "pop", "hip hop", "jazz", "classical",
                "live performance", "tour", "festival line-up",
            ],
            "gaming": [
                "game review", "video game", "gaming", "esports",
                "steam", "epic games", "playstation", "xbox", "nintendo",
                "rpg", "fps", "strategy", "simulation",
                "gameplay", "walkthrough", "guide",
            ],
        },
        domains=[
            "imdb.com", "rottentomatoes.com", "metacritic.com",
            "themoviedb.org", "letterboxd.com",
            "filmstarts.de", "moviepilot.de", "kino.de",
            "variety.com", "hollywoodreporter.com",
            "deadline.com", "ew.com", "thewrap.com",
            "netflix.com", "disneyplus.com", "hbomax.com",
            "billboard.com", "rollingstone.com",
            "pitchfork.com", "nme.com",
            "stereogum.com", "consequence.net",
            "grammy.com", "oscar.org",
            "youtube.com", "vimeo.com",
            "last.fm", "discogs.com", "allmusic.com",
            "musicbrainz.org", "setlist.fm",
            "songkick.com", "bandsintown.com",
            "spotifycharts.com", "soundcloud.com",
            "tiktok.com", "instagram.com",
            "reddit.com/r/movies", "reddit.com/r/television",
            "reddit.com/r/music", "reddit.com/r/gaming",
            "twitch.tv", "mixer.com",
        ],
    ),

    # ============================================================
    # FOOD / COOKING / RECIPES
    # ============================================================
    TopicDomain(
        name="food",
        keywords=[
            "recipe", "cook", "cooking", "bake", "baking", "kitchen",
            "ingredient", "meal", "dish", "cuisine", "gourmet",
            "breakfast", "lunch", "dinner", "dessert", "snack",
            "appetizer", "main course", "side dish", "soup", "salad",
            "grill", "bbq", "roast", "steam", "fry", "saute",
            "bake", "roast", "broil", "poach", "boil", "simmer",
            "vegetarian", "vegan", "gluten-free", "keto", "paleo",
            "nutrition", "calorie", "protein", "carb", "fat",
            "wine", "beer", "cocktail", "drink", "beverage",
            "chocolate", "cake", "cookie", "pie", "bread",
            "pasta", "pizza", "sushi", "curry", "taco", "burger",
            "sauce", "spice", "herb", "seasoning", "marinade",
            "food blog", "home cooking", "comfort food",
            "rezept", "kochen", "backen", "zutat", "gericht",
            "küche", "kochbuch", "kochrezept", "lebensmittel",
        ],
        sub_keywords={
            "dietary": [
                "vegetarian", "vegan", "gluten-free", "dairy-free",
                "keto", "paleo", "low carb", "whole30", "mediterranean",
                "plant-based", "organic", "non-gmo",
            ],
            "baking": [
                "bread", "cake", "cookie", "pie", "pastry",
                "sourdough", "yeast", "flour", "dough",
                "icing", "frosting", "filling", "crust",
            ],
            "beverages": [
                "coffee", "tea", "wine", "beer", "cocktail",
                "smoothie", "juice", "latte", "espresso",
                "brew", "ferment", "kombucha",
            ],
        },
        domains=[
            "allrecipes.com", "foodnetwork.com",
            "seriouseats.com", "epicurious.com",
            "bonappetit.com", "saveur.com",
            "tasty.co", "kitchn.com", "simplyrecipes.com",
            "smittenkitchen.com", "loveandlemons.com",
            "minimalistbaker.com", "cookieandkate.com",
            "chefkoch.de", "lecker.de", "essen-und-trinken.de",
            "kuechengoetter.de", "einfach-tasty.de",
            "springlane.de", "rewe.de/rezepte",
            "nyt.com/cooking", "bbcgoodfood.com",
            "delish.com", "foodandwine.com",
            "eatingwell.com", "health.com/food",
            "thespruceeats.com", "thepioneerwoman.com",
            "pinchofyum.com", "damndelicious.net",
            "joythebaker.com", "101cookbooks.com",
            "yummly.com", "food.com",
            "geniuskitchen.com", "tasteofhome.com",
            "supercook.com", "budgetbytes.com",
        ],
    ),

    # ============================================================
    # SPORTS / FITNESS
    # ============================================================
    TopicDomain(
        name="sports",
        keywords=[
            "sport", "game", "match", "tournament", "championship",
            "league", "cup", "final", "quarterfinal", "semifinal",
            "team", "player", "coach", "manager", "athlete",
            "score", "result", "standings", "table", "ranking",
            "transfer", "signing", "contract", "trade",
            "football", "soccer", "basketball", "baseball", "tennis",
            "golf", "hockey", "rugby", "cricket", "boxing", "mma",
            "olympics", "olympic", "world cup", "champions league",
            "nfl", "nba", "mlb", "nhl", "epl", "bundesliga",
            "formula 1", "f1", "motogp", "racing", "rally",
            "marathon", "triathlon", "cycling", "swimming",
            "skiing", "snowboarding", "climbing", "hiking",
            "workout", "exercise", "gym", "training", "fitness",
            "yoga", "pilates", "crossfit", "calisthenics",
            "bodybuilding", "strength", "cardio", "hiit",
            "personal trainer", "workout plan", "diet plan",
            "supplement", "pre-workout", "protein powder",
            "sport", "fußball", "verein", "trainer", "spieler",
            "bundesliga", "champions league", "weltmeisterschaft",
        ],
        sub_keywords={
            "football": [
                "bundesliga", "premier league", "la liga", "serie a",
                "champions league", "europa league", "world cup",
                "bayern", "dortmund", "real madrid", "barcelona",
                "manchester united", "liverpool", "arsenal",
            ],
            "fitness": [
                "workout", "exercise", "gym", "training", "muscle",
                "weight loss", "fat loss", "strength training",
                "cardio", "hiit", "crossfit", "bodybuilding",
                "bench press", "squat", "deadlift", "curl",
            ],
            "outdoor": [
                "hiking", "camping", "climbing", "trail running",
                "cycling", "mountain bike", "kayak", "paddle",
                "skateboarding", "surfing", "skate",
            ],
        },
        domains=[
            "espn.com", "sports.yahoo.com",
            "skysports.com", "bbc.com/sport",
            "theathletic.com", "bleacherreport.com",
            "cbssports.com", "nbcsports.com",
            "foxsports.com", "sport1.de",
            "kicker.de", "transfermarkt.de",
            "spox.com", "sportbild.de",
            "bild.de/sport", "sueddeutsche.de/sport",
            "kicker.de", "liga3-online.de",
            "nfl.com", "nba.com", "mlb.com", "nhl.com",
            "fifa.com", "uefa.com", "euroleague.net",
            "tournamentsoftware.com", "atptour.com",
            "formula1.com", "motogp.com", "wrc.com",
            "olympics.com", "paralympic.org",
            "cyclingnews.com", "velonews.com",
            "runnersworld.com", "triathlete.com",
            "bodybuilding.com", "muscleandstrength.com",
            "t-nation.com", "menshealth.com/fitness",
            "muscleandfitness.com", "fitnessmagazine.com",
            "yogajournal.com", "doctoryoga.com",
            "crossfit.com", "boxrox.com",
            "strava.com", "zwift.com",
            "myfitnesspal.com", "fatsecret.com",
            "vitaminde.de", "fitnessfirst.de",
        ],
    ),

    # ============================================================
    # AUTOMOTIVE / CARS
    # ============================================================
    TopicDomain(
        name="automotive",
        keywords=[
            "car", "vehicle", "automobile", "auto", "truck", "suv",
            "electric car", "ev", "electric vehicle", "hybrid", "tesla",
            "engine", "motor", "transmission", "brake", "tire",
            "mpg", "fuel economy", "range", "charging", "battery",
            "dealership", "dealer", "price", "msrp", "invoice price",
            "lease", "financing", "loan", "trade-in", "warranty",
            "insurance", "registration", "title", "inspection",
            "repair", "maintenance", "mechanic", "garage",
            "oil change", "brake pad", "timing belt", "spark plug",
            "review", "test drive", "road test", "comparison",
            "sedan", "coupe", "convertible", "hatchback", "wagon",
            "luxury", "sports car", "supercar", "off-road", "4x4",
            "motorcycle", "bike", "scooter", "moped",
            "auto", "fahrzeug", "pkw", "lkw", "elektroauto",
            "werkstatt", "reparatur", "versicherung", "zulassung",
            "tüv", "hauptuntersuchung", "neu", "gebraucht",
        ],
        sub_keywords={
            "electric": [
                "tesla", "model 3", "model y", "model s", "model x",
                "cybertruck", "volkswagen id", "vw id", "id4", "id3",
                "bmw i4", "bmw ix", "mercedes eq", "eqs", "eqe",
                "hyundai ioniq", "kia ev6", "kia ev9",
                "polestar", "rivian", "lucid", "nio", "xpeng",
                "charging", "supercharger", "wallbox", "charging station",
                "range", "kwh", "battery degradation",
            ],
            "maintenance": [
                "oil change", "tire rotation", "brake pad replacement",
                "timing belt", "spark plug", "air filter", "coolant",
                "transmission fluid", "differential", "wheel alignment",
                "diagnostic", "check engine", "obd2",
            ],
        },
        domains=[
            "caranddriver.com", "motortrend.com",
            "autoblog.com", "jalopnik.com",
            "autocar.co.uk", "topgear.com",
            "edmunds.com", "kbb.com", "truecar.com",
            "cars.com", "autotrader.com", "carvana.com",
            "cargurus.com", "autotempest.com",
            "saabplanet.com", "bmwblog.com",
            "auto-motor-und-sport.de", "autobild.de",
            "motor1.com", "insideevs.com",
            "electrek.co", "cleantechnica.com",
            "teslarati.com", "notateslaapp.com",
            "mobile.de", "autoscout24.de",
            "autoscout24.at", "autoscout24.ch",
            "autouncle.de", "automobile.it",
            "carwow.de", "meinauto.de",
            "dat.de", "schecke.de",
            "adac.de", "ace.de",
            "nhtsa.gov", "iihs.org",
            "tüv-nord.de", "tüv-süd.de", "dekra.de",
            "totalcarcheck.de", "carvertical.com",
            "epicvin.com", "faxvin.com",
        ],
    ),

    # ============================================================
    # REAL ESTATE / HOUSING
    # ============================================================
    TopicDomain(
        name="real_estate",
        keywords=[
            "house", "apartment", "condo", "property", "home",
            "rent", "rental", "lease", "tenant", "landlord",
            "buy", "sell", "purchase", "closing", "offer",
            "mortgage", "refinance", "home loan", "rate",
            "agent", "realtor", "broker", "appraiser",
            "listing", "mls", "for sale", "for rent",
            "price", "valuation", "appraisal", "assessment",
            "neighborhood", "suburb", "downtown", "area",
            "square footage", "sqft", "acre", "lot",
            "bedroom", "bathroom", "kitchen", "basement",
            "garage", "yard", "garden", "pool", "parking",
            "hoa", "homeowners association", "condo fee",
            "property tax", "insurance", "inspection",
            "school district", "commute", "walkability",
            "new construction", "new home", "model home",
            "first-time buyer", "down payment", "closing cost",
            "immobilie", "wohnung", "haus", "mietwohnung",
            "eigentumswohnung", "reihenhaus", "doppelhaushälfte",
            "miete", "kauf", "immobilienmakler", "besichtigung",
            "kaution", "nebenkosten", "mietpreisbremse",
            "wohngeld", "bauzins", "grundbuch", "notar",
            "wg-gesucht", "studentenwohnheim",
        ],
        sub_keywords={
            "rental": [
                "apartment for rent", "roommates", "sublet", "studio",
                "1 bedroom", "2 bedroom", "furnished", "utilities included",
                "security deposit", "first month", "lease term",
                "no fee", "broker fee", "section 8", "voucher",
                "wg", "wohnungsgenossenschaft", "sozialwohnung",
            ],
            "buying": [
                "first time home buyer", "down payment", "mortgage",
                "pre-approved", "pre-qualified", "closing costs",
                "home inspection", "appraisal", "offer", "counter offer",
                "earnest money", "escrow", "title insurance",
                "fixed rate", "adjustable rate", "arm",
            ],
            "commercial": [
                "commercial property", "office space", "retail space",
                "warehouse", "industrial", "triple net", "nnn",
                "cap rate", "cash flow", "commercial lease",
                "co-working", "flex space",
            ],
        },
        domains=[
            "zillow.com", "realtor.com", "redfin.com",
            "trulia.com", "apartments.com", "rent.com",
            "streeteasy.com", "padmapper.com",
            "immobilienscout24.de", "immowelt.de",
            "wg-gesucht.de", "kleinanzeigen.de",
            "immonet.de", "nestoria.de",
            "vonovia.de", "deutsche-wohnen.com",
            "homegate.ch", "immoscout24.ch",
            "makler-in-berlin.de", "berlin-hausverwaltung.de",
            "boersen-zeitung.de", "housinganywhere.com",
            "spotahome.com", "nestpick.com",
            "propertyguru.com", "99acres.com",
            "rightmove.co.uk", "zoopla.co.uk",
            "onthemarket.com", "primelocation.com",
            "moving.com", "homeadvisor.com",
            "neighborhoodscout.com", "niche.com",
            "greatschools.org", "schooldigger.com",
            "walk-score.com", "reddit.com/r/realestate",
            "biggerpockets.com", "reiclub.com",
        ],
    ),

    # ============================================================
    # CAREER / JOBS / PROFESSIONAL
    # ============================================================
    TopicDomain(
        name="career",
        keywords=[
            "job", "career", "employment", "position", "vacancy",
            "resume", "cv", "cover letter", "application",
            "interview", "hire", "hiring", "recruit", "recruitment",
            "salary", "compensation", "benefits", "bonus",
            "promotion", "raise", "career growth", "advancement",
            "remote", "hybrid", "on-site", "work from home",
            "internship", "apprenticeship", "entry level", "senior",
            "manager", "director", "vp", "executive", "c-level",
            "laid off", "layoff", "fired", "terminated", "quit",
            "notice period", "resignation", "severance",
            "company culture", "work-life balance", "perks",
            "network", "networking", "linkedin", "referral",
            "skill", "upskill", "reskill", "certification",
            "professional development", "training", "workshop",
            "coaching", "mentor", "mentorship",
            "arbeit", "job", "stelle", "ausbildung", "studium",
            "bewerbung", "lebenslauf", "anschreiben",
            "gehalt", "einkommen", "verhandlung",
            "kündigung", "kündigungsfrist", "abfindung",
            "arbeitsvertrag", "tarifvertrag", "betriebsrat",
            "selbstständig", "freiberufler", "unternehmer",
            "arbeitsagentur", "jobcenter", "arbeitslos",
            "elternzeit", "mutterschutz", "krankenstand",
            "homeoffice", "mobiles arbeiten", "gleitzeit",
        ],
        sub_keywords={
            "tech_jobs": [
                "software engineer", "developer", "programmer",
                "data scientist", "machine learning engineer",
                "devops", "sre", "site reliability",
                "product manager", "project manager",
                "ux designer", "ui designer", "product designer",
                "engineering manager", "tech lead",
                "frontend", "backend", "full stack", "mobile",
            ],
            "interviewing": [
                "interview questions", "technical interview",
                "coding interview", "leetcode", "system design",
                "behavioral interview", "whiteboard", "take-home",
                "interview preparation", "mock interview",
            ],
            "salary": [
                "salary negotiation", "compensation", "total comp",
                "base salary", "equity", "stock options", "rsu",
                "signing bonus", "annual bonus", "benefits package",
                "salary range", "pay scale", "cost of living adjustment",
            ],
        },
        domains=[
            "linkedin.com", "indeed.com", "glassdoor.com",
            "monster.com", "careerbuilder.com",
            "ziprecruiter.com", "snagajob.com",
            "dice.com", "stackoverflow.com/jobs",
            "levels.fyi", "teamblind.com",
            "honeypot.io", "angel.co", "wellfound.com",
            "hiring.cafe", "workable.com",
            "stepstone.de", "indeed.de", "monster.de",
            "jobware.de", "stellenonline.de",
            "interamt.de", "bundeskarriereportal.de",
            "arbeitsagentur.de", "jobboerse.arbeitsagentur.de",
            "xing.com", "kununu.com",
            "linkedin.com/jobs", "linkedin.com/salary",
            "reddit.com/r/jobs", "reddit.com/r/cscareerquestions",
            "reddit.com/r/experienceddevs",
            "usajobs.gov", "europe.eu/eures",
            "coursera.org", "udemy.com", "pluralsight.com",
            "udacity.com", "edx.org",
            "leetcode.com", "hackerrank.com",
            "crackingthecodinginterview.com",
            "pramp.com", "interviewing.io",
        ],
    ),

    # ============================================================
    # EDUCATION / LEARNING
    # ============================================================
    TopicDomain(
        name="education",
        keywords=[
            "course", "class", "lesson", "tutorial", "lecture",
            "learn", "study", "teach", "educate", "education",
            "school", "college", "university", "academy",
            "degree", "bachelor", "master", "phd", "doctorate",
            "diploma", "certificate", "certification",
            "online course", "mooc", "elearning", "distance learning",
            "student", "teacher", "professor", "instructor",
            "homework", "assignment", "exam", "test", "quiz",
            "grade", "gpa", "transcript", "credit", "semester",
            "scholarship", "grant", "financial aid", "tuition",
            "admission", "enrollment", "registration",
            "curriculum", "syllabus", "textbook", "reading list",
            "tutor", "tutoring", "study group", "peer learning",
            "self-study", "self-paced", "bootcamp", "workshop",
            "language learning", "learn language", "duolingo",
            "math", "science", "history", "english", "literature",
            "studium", "hochschule", "universität", "fachhochschule",
            "vorlesung", "seminar", "übung", "praktikum",
            "prüfung", "klausur", "schein", "leistungspunkt",
            "bafög", "ausbildung", "umschulung", "fortbildung",
            "weiterbildung", "vhs", "volkshochschule",
            "masterarbeit", "bachelorarbeit", "promotion",
        ],
        sub_keywords={
            "language_learning": [
                "learn english", "learn german", "learn spanish",
                "learn french", "learn japanese", "learn chinese",
                "duolingo", "babbel", "rosetta stone", "memrise",
                "anki", "flashcards", "vocabulary", "grammar",
                "language exchange", "tandem", "italki",
            ],
            "programming_courses": [
                "learn python", "learn javascript", "learn java",
                "web development", "data science course",
                "machine learning course", "cs course",
                "freecodecamp", "the odin project",
                "100 days of code", "codecademy",
            ],
            "study_tools": [
                "anki", "quizlet", "notion", "obsidian",
                "onenote", "evernote", "zotero", "mendeley",
                "citation machine", "grammarly", "turnitin",
            ],
        },
        domains=[
            "coursera.org", "edx.org", "udemy.com",
            "udacity.com", "khanacademy.org",
            "futurelearn.com", "classcentral.com",
            "codecademy.com", "freecodecamp.org",
            "theodinproject.com", "w3schools.com",
            "developer.mozilla.org", "geeksforgeeks.org",
            "khanacademy.org", "brilliant.org",
            "memrise.com", "duolingo.com",
            "babbel.com", "busuu.com",
            "haftadviseren.se", "studienwahl.de",
            "hochschulkompass.de", "uni-assist.de",
            "studieren.de", "studycheck.de",
            "hochschulstart.de", "e-fellows.net",
            "bafoeg-aktuell.de", "ausbildung.de",
            "berufenet.arbeitsagentur.de",
            "wikipedia.org", "britannica.com",
            "goodreads.com", "openlibrary.org",
            "quizlet.com", "ankiweb.net",
            "zotero.org", "mendeley.com",
            "overleaf.com", "sharelatex.com",
            "turnitin.com", "grammarly.com",
            "mit.edu/ocw", "ocw.mit.edu",
            "ted.com", "tedx.com",
            "instructables.com", "wikihow.com",
        ],
    ),

    # ============================================================
    # LEGAL / LAW
    # ============================================================
    TopicDomain(
        name="legal",
        keywords=[
            "law", "legal", "attorney", "lawyer", "solicitor",
            "court", "judge", "jury", "trial", "lawsuit",
            "sue", "suing", "plaintiff", "defendant", "defense",
            "contract", "agreement", "terms", "clause", "provision",
            "copyright", "trademark", "patent", "intellectual property",
            "divorce", "custody", "child support", "alimony",
            "will", "trust", "estate", "probate", "inheritance",
            "bankruptcy", "foreclosure", "debt settlement",
            "immigration", "visa", "green card", "citizenship",
            "tenant rights", "landlord rights", "eviction",
            "employment law", "labor law", "union", "collective bargaining",
            "discrimination", "harassment", "retaliation",
            "personal injury", "accident", "malpractice",
            "criminal defense", "dui", "dwai", "traffic ticket",
            "appeal", "appeals", "motion", "brief", "argument",
            "legal aid", "pro bono", "legal advice",
            "recht", "anwalt", "gericht", "urteil", "klage",
            "vertrag", "mietrecht", "familienrecht", "erbrecht",
            "strafrecht", "zivilrecht", "verwaltungsrecht",
            "mietvertrag", "arbeitsvertrag", "kaufvertrag",
            "rechtsanwalt", "fachanwalt", "rechtsberatung",
            "rechtschutzversicherung", "gerichtsverfahren",
        ],
        sub_keywords={
            "immigration": [
                "visa", "green card", "h1b", "l1", "eb2", "eb3",
                "student visa", "f1", "j1", "work visa",
                "asylum", "refugee", "citizenship", "naturalization",
                "deportation", "removal", "immigration court",
                "aufenthaltstitel", "niederlassungserlaubnis",
                "visum", "arbeitserlaubnis", "einbürgerung",
                "blauen karte", "blue card", "eu blueprint",
            ],
            "contract": [
                "breach of contract", "specific performance",
                "damages", "liquidated damages", "force majeure",
                "arbitration", "mediation", "non-disclosure", "nda",
                "non-compete", "non-solicit", "severability",
            ],
            "tenant_rights": [
                "tenant rights", "lease agreement", "rent control",
                "security deposit", "eviction notice", "habitability",
                "repair and deduct", "rent increase", "lease renewal",
                "sublease", "roommate agreement",
                "mietpreisbremse", "kaution", "betriebskostenabrechnung",
                "wohnungsmängel", "mieterhöhung", "kündigung",
            ],
        },
        domains=[
            "law.cornell.edu", "findlaw.com",
            "justia.com", "legalzoom.com",
            "rocketlawyer.com", "lawdepot.com",
            "avvo.com", "martindale.com",
            "law360.com", "scotusblog.com",
            "supremecourt.gov",
            "nolo.com", "lawhelp.org",
            "aclu.org", "eff.org",
            "wipo.int", "uspto.gov",
            "epo.org", "dpma.de",
            "dejure.org", "gesetze-im-internet.de",
            "buzer.de", "rechtsprechung-im-internet.de",
            "anwaltauskunft.de", "anwaltsuche.de",
            "frag-einen-anwalt.de", "123recht.de",
            "advocado.de", "anwalt.org",
            "kostenlose-urteile.de", "openjur.de",
            "mietrecht.org", "mieterbund.de",
            "haufe.de", "lexisnexis.com",
            "beck-online.beck.de", "wolterskluwer.com",
            "gdpr.eu", "privacyshield.gov",
            "irb-law.com", "buzer.de",
            "arbeitsgericht.de", "sozialgerichtsbarkeit.de",
        ],
    ),

    # ============================================================
    # FASHION / BEAUTY
    # ============================================================
    TopicDomain(
        name="fashion",
        keywords=[
            "fashion", "clothing", "apparel", "outfit", "wardrobe",
            "shirt", "blouse", "top", "dress", "skirt", "pants",
            "jeans", "shorts", "jacket", "coat", "blazer", "suit",
            "shoe", "sneaker", "boot", "sandal", "heel", "loafer",
            "accessory", "bag", "belt", "hat", "scarf", "watch",
            "jewelry", "necklace", "bracelet", "ring", "earring",
            "designer", "luxury", "high-end", "couture", "brand",
            "streetwear", "casual", "formal", "business casual",
            "trend", "season", "spring", "summer", "fall", "winter",
            "size", "fit", "measurement", "petite", "plus size", "tall",
            "fabric", "material", "cotton", "wool", "silk", "linen",
            "color", "pattern", "print", "stripe", "floral", "plaid",
            "makeup", "cosmetics", "skincare", "beauty", "hair",
            "lipstick", "foundation", "concealer", "eyeshadow",
            "moisturizer", "serum", "sunscreen", "cleanser", "toner",
            "nail polish", "manicure", "pedicure", "salon",
            "parfum", "perfume", "cologne", "fragrance",
            "mode", "kleidung", "schuhe", "accessoires",
            "schmuck", "designer", "luxus", "marke",
            "make-up", "kosmetik", "hautpflege", "haarpflege",
        ],
        sub_keywords={
            "brands": [
                "gucci", "prada", "louis vuitton", "channel",
                "hermes", "dior", "versace", "armani", "balenciaga",
                "supreme", "off-white", "yeezy", "nike", "adidas",
                "zara", "h&m", "uniqlo",
            ],
            "skincare": [
                "moisturizer", "sunscreen", "retinol", "vitamin c",
                "hyaluronic acid", "niacinamide", "peptides",
                "face wash", "toner", "serum", "eye cream",
                "anti-aging", "acne", "dark spots", "wrinkles",
            ],
            "sneakers": [
                "nike air force", "jordan", "yeezy", "new balance",
                "adidas ultraboost", "vans old skool", "converse",
                "sneaker release", "limited edition", "hype",
                "restock", "raffle", "resale", "stockx",
            ],
        },
        domains=[
            "vogue.com", "harpersbazaar.com", "elle.com",
            "cosmopolitan.com", "glamour.com",
            "wwd.com", "businessoffashion.com",
            "fashionista.com", "thefashionspot.com",
            "refinery29.com", "whowhatwear.com",
            "thecut.com", "manrepeller.com",
            "highsnobiety.com", "hypebeast.com",
            "complex.com", "ssense.com",
            "nike.com", "adidas.com", "zara.com",
            "farfetch.com", "net-a-porter.com",
            "ssense.com", "mrporter.com",
            "stockx.com", "grailed.com", "goat.com",
            "zalando.de", "zalando.com",
            "asos.com", "aboutyou.de",
            "stylebook.de", "gala.de",
            "bunte.de", "instyle.de",
            "vogue.de", "elle.de",
            "sephora.com", "ulta.com",
            "dermstore.com", "skincare.com",
            "paulaschoice.com", "theordinary.com",
            "cosmopolitan.com", "allure.com",
            "byrdie.com", "thebeautybrains.com",
            "incidecoder.com", "cosdna.com",
            "skincarisma.com", "reddit.com/r/SkincareAddiction",
            "reddit.com/r/femalefashionadvice",
            "reddit.com/r/sneakers", "reddit.com/r/streetwear",
        ],
    ),

    # ============================================================
    # PHOTOGRAPHY / VIDEO
    # ============================================================
    TopicDomain(
        name="photography",
        keywords=[
            "photography", "photo", "photograph", "camera", "lens",
            "dslr", "mirrorless", "compact camera", "point and shoot",
            "smartphone camera", "action camera", "gopro",
            "drone", "aerial photography", "cinematic",
            "aperture", "shutter speed", "iso", "exposure",
            "focus", "depth of field", "bokeh", "focal length",
            "wide angle", "telephoto", "macro", "prime", "zoom",
            "sensor", "megapixel", "resolution", "raw", "jpeg",
            "tripod", "gimbal", "stabilizer", "flash", "lighting",
            "portrait", "landscape", "street photography", "macro",
            "wedding photography", "event photography", "product",
            "editing", "photoshop", "lightroom", "capture one",
            "color grading", "retouching", "preset",
            "video", "cinematography", "film", "clip",
            "4k", "8k", "frame rate", "bitrate", "codec",
            "davinci resolve", "final cut", "premiere pro",
            "fotografie", "kamera", "objektiv", "fotograf",
            "bildbearbeitung", "fotobuch", "belichtung",
        ],
        sub_keywords={
            "camera_gear": [
                "sony a7", "canon eos", "nikon z", "fujifilm x",
                "panasonic lumix", "leica", "hasselblad",
                "rf lens", "ef lens", "z mount", "e mount",
                "sigma art", "tamron", "sony fe",
            ],
            "editing": [
                "lightroom preset", "photoshop tutorial", "action",
                "color grading", "lut", "masking", "layer",
                "retouching skin", "frequency separation",
                "dodge and burn", "blending mode",
            ],
            "cinematography": [
                "cinematography", "film look", "cinematic", "color grade",
                "camera movement", "dolly", "crane", "steadicam",
                "lighting setup", "three point lighting", "key light",
                "documentary", "narrative", "short film",
            ],
        },
        domains=[
            "dpreview.com", "imaging-resource.com",
            "the-digital-picture.com", "lenstip.com",
            "photographylife.com", "petapixel.com",
            "fstoppers.com", "fstoppers.com/gear",
            "digitalcameraworld.com", "camerajabber.com",
            "kenrockwell.com", "tomshardware.com/cameras",
            "cameradecision.com", "camerasize.com",
            "dxomark.com", "sensorscore.com",
            "sonyalpha.blog", "fujirumors.com",
            "canonrumors.com", "nikonrumors.com",
            "youtube.com/@gordonlaing", "youtube.com/@petapixel",
            "flickr.com", "500px.com", "instagram.com",
            "unsplash.com", "pexels.com",
            "adobe.com/photoshop", "adobe.com/lightroom",
            "captureone.com", "davincireslove.com",
            "affinity.serif.com", "gimp.org",
            "reddit.com/r/photography", "reddit.com/r/postprocessing",
            "reddit.com/r/cameras", "reddit.com/r/AskPhotography",
            "dpbestflow.org", "cambridgeincolour.com",
            "fotocommunity.de", "fotografen.de",
            "digitalphotographyschool.com",
            "improvephotography.com", "shotkit.com",
        ],
    ),
]


# ============================================================
# CLASSIFIER ENGINE
# ============================================================

def classify_query(query: str) -> Tuple[str, float, TopicDomain]:
    """
    Classify a user query into a topic category using keyword matching.
    
    Returns:
        Tuple of (topic_name, confidence_score, TopicDomain object)
    """
    query_lower = query.lower()
    best_topic: Optional[TopicDomain] = None
    best_score = 0.0

    for topic in TOPIC_DATABASE:
        score = 0.0

        for kw in topic.keywords:
            if kw.lower() in query_lower:
                score += topic.priority

        for sub_name, sub_kws in topic.sub_keywords.items():
            for skw in sub_kws:
                if skw.lower() in query_lower:
                    score += topic.priority * 2

        score = min(score, 100.0)

        if score > best_score:
            best_score = score
            best_topic = topic

    if best_topic is None:
        return ("general", best_score, None)

    return (best_topic.name, best_score, best_topic)


def enrich_query_with_domains(query: str) -> str:
    """
    Enrich a search query with site: domain hints based on topic classification.
    
    If the query matches a topic with high confidence (score >= 3),
    appends up to 8 domain filters as `site:` OR keywords 
    to guide the search engine toward authoritative sources.
    
    Examples:
        "best smartphone under 300 euros"
        → "best smartphone under 300 euros (site:idealo.de OR site:geizhals.de OR site:notebookcheck.com OR site:mediamarkt.de)"
        
        "nvidia stock performance 2026"
        → "nvidia stock performance 2026 (site:finance.yahoo.com OR site:reuters.com OR site:bloomberg.com OR site:morningstar.com)"
    """
    topic_name, confidence, topic = classify_query(query)
    logger = logging.getLogger("ai_ensemble.rag")

    if confidence < 3 or topic is None or not topic.domains:
        logger.info(f"[RAG] Query enrichment: no topic match (confidence={confidence}), using raw query")
        return query

    domains = topic.domains[:8]
    domain_filters = " OR ".join(f"site:{d}" for d in domains)
    enriched = f"{query} ({domain_filters})"

    logger.info(
        f"[RAG] Query enrichment: topic='{topic_name}' confidence={confidence} "
        f"domains={len(domains)} -> {enriched[:120]}..."
    )

    return enriched

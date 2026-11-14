"""PLAYMAX Uzbekistan bot — texts, catalog and links (Uzbek, Latin)."""
import os

TOKEN = os.environ.get("TG_UZ_TOKEN", "")
CHANNEL = "@playmax_box"
ADMINS = [int(x) for x in os.environ.get("ADMIN_IDS", "8942046452").split(",") if x.strip()]
RAW = "https://raw.githubusercontent.com/playmaxuzb/playmax-uz-bot/main/media/"

P1, P2 = "+998 97 089 94 99", "+998 50 780 02 79"
EMAIL = "playmax.uzb@gmail.com"
SITE = "https://playmaxuz.com"
IG = "https://www.instagram.com/playmax.uz/?hl=en"
CH_URL = "https://t.me/playmax_box"
CATALOG_POST = "https://t.me/playmax_box/185"
OFFICE = (41.199058, 69.236804)
FACTORY = (41.209238, 69.151245)
ROUTE_OFFICE = f"https://yandex.com/maps/?rtext=~{OFFICE[0]},{OFFICE[1]}&rtt=auto"
ROUTE_FACTORY = f"https://yandex.com/maps/?rtext=~{FACTORY[0]},{FACTORY[1]}&rtt=auto"
SHOWROOM = "INDEX Sergeli bozori, E1-1-1098 doʻkon"

FOOT = f"\n\n📞 {P1}\n📞 {P2}\n✉️ {EMAIL}\n🌐 playmaxuz.com"

# key: (title, [(machine_key, name, photo, description)])
CATALOG = {
    "boks": ("🥊 Boks avtomatlari", [
        ("king", "KING FIGHTERS", "01-boxing-king-red", "Qizil dizayn, kuchli koʻrinish. Zarb kuchini oʻlchaydi va natijani tabloda koʻrsatadi."),
        ("tour", "Boxing Tournament", "02-boxing-tournament-white", "Oq rangli boks avtomati — savdo markazi va oʻyin zallari uchun."),
        ("champ_b", "Boxer Champion (qora)", "03-boxing-champion-black", "Qora-oltin dizayn, premium koʻrinish."),
        ("boxer_y", "Boxer (sariq)", "04-boxing-yellow-boxer", "Yorqin sariq — uzoqdan koʻrinadi."),
        ("champ_r", "Champion (qizil)", "06-boxing-champion-red", "Qizil boks avtomati — rekord tablosi bilan."),
        ("kicker", "Boxer + Kicker", "07-boxing-yellow-kicker", "Ham zarb, ham tepish — ikki oʻyin bitta avtomatda."),
    ]),
    "sovga": ("🎁 Sovgʻa avtomatlari", [
        ("space1", "SPACE — Play Game", "09-space-claw-machine-playgame", "Oq-pushti dizayn, yorqin chiroqlar."),
        ("space2", "SPACE — Ducks", "10-space-claw-machine-ducks", "Sariq rangli, bolalarga juda yoqadi."),
        ("space3", "SPACE — Astronaut", "11-space-claw-machine-astronaut", "Yashil-binafsha, kosmik dizayn."),
    ]),
    "kuch": ("💪 Kuch va mergan oʻyinlari", [
        ("hammer", "KING OF THE HAMMER", "24-king-of-the-hammer-game", "Bolgʻa bilan zarb — baland tabloda natija."),
        ("balloon", "Shar otish oʻyini", "26-balloon-shooting-game", "Aniqlik va tezlik uchun oʻyin."),
    ]),
    "stol": ("🎮 Stol oʻyinlari", [
        ("hockey_b", "AIR HOCKEY (qora)", "17-air-hockey-table-black", "Ikki kishilik tez oʻyin."),
        ("hockey_w", "AIR HOCKEY (oq)", "18-air-hockey-table-white", "Oq dizaynli havo xokkeyi."),
        ("hockey_c", "AIR HOCKEY (klassik)", "19-air-hockey-table", "Klassik havo xokkeyi stoli."),
        ("foosball", "Stol futboli", "20-foosball-table", "Doʻstlar bilan qiziqarli oʻyin."),
    ]),
    "vr": ("🥽 VR va dam olish", [
        ("vr", "VR ZONE", "29-arcade-charging-station", "Virtual reallik — yangi tajriba, kam joy."),
        ("massage", "Massaj kreslosi", "12-massage-chair", "Bir tugma bilan dam olish."),
    ]),
    "bolalar": ("🎠 Bolalar maydonchalari", [
        ("pg1", "Maydoncha — tepalik va argʻimchoq", "13-playground-slide-swings", "Tepalik, tunnel va argʻimchoqlar."),
        ("pg2", "Mavzuli maydoncha (qovoq)", "14-pumpkin-themed-playground", "Rangli mavzuli maydoncha."),
        ("pg3", "Ikki tepalikli maydoncha", "15-themed-double-slide-playground", "Ikkita tepalikli katta maydoncha."),
        ("pg4", "Quyosh mavzuli maydoncha", "16-sun-themed-playground", "Quyosh mavzusidagi yorqin maydoncha."),
        ("carousel", "Bolalar karuseli", "27-childrens-carousel-ride", "Rangli aylanma karusel."),
        ("bungee", "Bungee batut", "28-bungee-trampoline", "Sakrash attraksioni."),
        ("castle", "Puflama qasr", "31-inflatable-play-castle", "Bolalar uchun puflama oʻyin qasri."),
    ]),
}
MACHINES = {k: (name, photo, desc, cat) for cat, (_, items) in CATALOG.items() for k, name, photo, desc in items}

REGIONS = ["Toshkent shahri", "Toshkent viloyati", "Andijon", "Buxoro", "Fargʻona", "Jizzax", "Xorazm",
           "Namangan", "Navoiy", "Qashqadaryo", "Qoraqalpogʻiston", "Samarqand", "Sirdaryo", "Surxondaryo"]

# --- profit calculator assumptions (rough, shown as an estimate) ---
CALC_MACHINES = {"boks": ("🥊 Boks avtomati", 0.05), "sovga": ("🎁 Sovgʻa avtomati", 0.06),
                 "kuch": ("💪 KING OF THE HAMMER", 0.04), "stol": ("🎮 Air hockey / stol futboli", 0.03),
                 "vr": ("🥽 VR ZONE", 0.02), "massaj": ("💺 Massaj kreslosi", 0.015)}
CALC_PLACES = {"mall": ("🛍 Savdo markazi", 1.0), "cafe": ("☕ Kafe / restoran", 0.9), "park": ("🌳 Park", 1.1),
               "zal": ("🎮 Oʻyin zali", 1.4), "dokon": ("🏪 Doʻkon / bozor", 0.8), "azs": ("⛽ Yoqilgʻi shoxobchasi", 0.6)}
CALC_TRAFFIC = {"300": "300 tagacha", "800": "300–1000", "2000": "1000–3000", "5000": "3000 dan koʻp"}

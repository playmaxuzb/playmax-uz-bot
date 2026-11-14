"""PLAYMAX Uzbekistan bot — services for @playmax_box.

Runs as long polling inside GitHub Actions in ~5h50m shifts (see .github/workflows/bot.yml).
All user-facing text is Uzbek (Latin). Requests are forwarded to ADMINS in a readable card.
"""
import datetime as dt
import html
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from data import *  # noqa: F401,F403

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = f"https://api.telegram.org/bot{TOKEN}/"
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", str(5 * 3600 + 50 * 60)))
TZ = dt.timezone(dt.timedelta(hours=5))
CH_F = os.path.join(ROOT, "data", "challenge.json")
PEND_F = os.path.join(ROOT, "data", "pending.json")
STATE = {}  # user_id -> {"flow": str, "step": str, "d": {...}}


# ---------------------------------------------------------------- telegram
def call(method, **params):
    files = params.pop("_files", None)
    if files:
        import uuid
        b = uuid.uuid4().hex
        body = b""
        for k, v in params.items():
            if v is None:
                continue
            v = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, (name, data) in files.items():
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\n\r\n'.encode() + data + b"\r\n"
        body += f"--{b}--\r\n".encode()
        headers = {"Content-Type": f"multipart/form-data; boundary={b}"}
    else:
        body = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
        headers = {"Content-Type": "application/json"}
    for attempt in range(4):
        try:
            req = urllib.request.Request(API + method, body, headers)
            with urllib.request.urlopen(req, timeout=70) as r:
                return json.loads(r.read()).get("result")
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read() or b"{}")
            except Exception:
                err = {}
            ra = err.get("parameters", {}).get("retry_after")
            if ra:
                time.sleep(ra + 1)
                continue
            print(f"[tg] {method}: {err.get('description')}")
            return None
        except Exception as e:
            print(f"[tg] {method} error: {e}")
            time.sleep(3 * (attempt + 1))
    return None


def ikb(rows):
    out = []
    for row in rows:
        r = []
        for text, target in row:
            if target.startswith(("http", "tg:")):
                r.append({"text": text, "url": target})
            else:
                r.append({"text": text, "callback_data": target})
        out.append(r)
    return {"inline_keyboard": out}


def say(chat, text, rows=None, **kw):
    return call("sendMessage", chat_id=chat, text=text, parse_mode="HTML",
                link_preview_options={"is_disabled": True},
                reply_markup=ikb(rows) if rows else kw.pop("reply_markup", None), **kw)


def ask_phone(chat, text):
    kb = {"keyboard": [[{"text": "📱 Raqamni yuborish", "request_contact": True}], [{"text": "❌ Bekor qilish"}]],
          "resize_keyboard": True, "one_time_keyboard": True}
    return call("sendMessage", chat_id=chat, text=text, parse_mode="HTML", reply_markup=kb)


def drop_kb(chat, text):
    return call("sendMessage", chat_id=chat, text=text, parse_mode="HTML", reply_markup={"remove_keyboard": True})


def esc(s):
    return html.escape(str(s or ""))


# ---------------------------------------------------------------- screens
MENU = [
    [("📋 Katalog", "cat"), ("🛒 Buyurtma berish", "order")],
    [("💰 Narxni bilish", "price"), ("🧮 Daromad kalkulyatori", "calc")],
    [("🛠 Servis va taʼmirlash", "service"), ("🏆 Eng kuchli zarba", "chal")],
    [("📅 Koʻrgazmaga yozilish", "visit"), ("🚚 Yetkazish narxi", "deliv")],
    [("🎥 Jonli video soʻrash", "live"), ("📸 Avtomatim — joyimda", "show")],
    [("🤝 Diler boʻlish", "dealer"), ("📍 Manzillar", "loc")],
    [("📞 Aloqa", "contact"), ("🌐 Sayt", SITE)],
]
BACK = [("⬅️ Bosh menyu", "menu")]


def home(chat, name=""):
    hi = f"Assalomu alaykum, {esc(name)}! 👋\n\n" if name else ""
    return call("sendPhoto", chat_id=chat, photo=RAW + "showcase-product-lineup.jpg", parse_mode="HTML",
                caption=hi + "<b>PLAYMAX</b> — oʻyin avtomatlari Oʻzbekistonda 🇺🇿\n\n"
                "Bu yerda katalogni koʻrishingiz, buyurtma berishingiz, daromadingizni hisoblashingiz "
                "va servis soʻrashingiz mumkin. Tanlang 👇",
                reply_markup=ikb(MENU))


def contact(chat):
    say(chat, "📞 <b>Biz bilan bogʻlaning</b>\n\n"
        f"📞 {P1}\n📞 {P2}\n✉️ {EMAIL}\n🌐 playmaxuz.com\n\n📍 Koʻrgazma: {SHOWROOM}",
        [[("🌐 Sayt", SITE), ("📸 Instagram", IG)], [("📢 Kanal", CH_URL)], BACK])


def locations(chat):
    call("sendVenue", chat_id=chat, latitude=OFFICE[0], longitude=OFFICE[1], title="🏢 PLAYMAX ofisi",
         address="Toshkent", reply_markup=ikb([[("🚗 Ofisga yoʻl (Yandex)", ROUTE_OFFICE)]]))
    call("sendVenue", chat_id=chat, latitude=FACTORY[0], longitude=FACTORY[1], title="🏭 PLAYMAX zavodi",
         address="Toshkent", reply_markup=ikb([[("🚗 Zavodga yoʻl (Yandex)", ROUTE_FACTORY)]]))
    say(chat, f"📍 Koʻrgazma: {SHOWROOM}\n\nKelishdan oldin qoʻngʻiroq qiling 👇" + FOOT,
        [[("📅 Koʻrgazmaga yozilish", "visit")], BACK])


def catalog(chat):
    rows = [[(t, f"c:{k}")] for k, (t, _) in CATALOG.items()]
    say(chat, "📋 <b>Katalog</b> — turini tanlang 👇", rows + [BACK])


def category(chat, key):
    title, items = CATALOG[key]
    say(chat, f"{title} — avtomatni tanlang 👇", [[(n, f"m:{k}")] for k, n, _, _ in items] + [[("⬅️ Katalog", "cat")]])


def machine(chat, key):
    name, photo, desc, cat = MACHINES[key]
    call("sendPhoto", chat_id=chat, photo=RAW + photo + ".jpg", parse_mode="HTML",
         caption=f"<b>{esc(name)}</b>\n\n{esc(desc)}\n\n✅ Yetkazish va oʻrnatish\n✅ Ehtiyot qismlar va servis" + FOOT,
         reply_markup=ikb([[("🛒 Buyurtma berish", f"om:{key}"), ("💰 Narxni bilish", f"pm:{key}")],
                           [("🎥 Jonli video", f"lm:{key}")],
                           [("⬅️ Orqaga", f"c:{cat}"), ("🏠 Menyu", "menu")]]))


# ---------------------------------------------------------------- admin cards
def user_line(u):
    name = esc(" ".join(x for x in (u.get("first_name"), u.get("last_name")) if x))
    uname = f" @{u['username']}" if u.get("username") else ""
    return f'👤 <a href="tg://user?id={u["id"]}">{name or "Mijoz"}</a>{esc(uname)} · ID <code>{u["id"]}</code>'


def notify(kind, u, fields, media=None, approve=None):
    now = dt.datetime.now(TZ).strftime("%d.%m %H:%M")
    text = f"🔔 <b>{kind}</b> · {now}\n{user_line(u)}\n\n" + "\n".join(f"<b>{esc(k)}:</b> {esc(v)}" for k, v in fields if v)
    rows = [[("💬 Mijozga yozish", f"tg://user?id={u['id']}")]]
    if approve:
        rows = [[("✅ Kanalga chiqarish", f"ok:{approve}"), ("❌ Rad etish", f"no:{approve}")]] + rows
    for a in ADMINS:
        if media:
            typ, fid = media
            m = {"photo": "sendPhoto", "video": "sendVideo", "document": "sendDocument"}[typ]
            call(m, chat_id=a, **{typ: fid}, caption=text[:1024], parse_mode="HTML", reply_markup=ikb(rows))
        else:
            say(a, text, rows)


# ---------------------------------------------------------------- flows
def start_flow(u, chat, flow, **d):
    STATE[u["id"]] = {"flow": flow, "step": "", "d": d}
    st = STATE[u["id"]]
    if flow == "order":
        if d.get("machine"):
            st["step"] = "city"
            return ask_city(chat, "🛒 <b>" + esc(MACHINES[d["machine"]][0]) + "</b>\n\nQaysi shahar yoki viloyatga kerak?")
        st["step"] = "what"
        return say(chat, "🛒 <b>Buyurtma</b>\n\nQaysi avtomat kerak? Katalogdan tanlang yoki yozing / rasm yuboring 👇",
                   [[("📋 Katalogdan tanlash", "cat")], [("❌ Bekor qilish", "cancel")]])
    if flow == "price":
        st["step"] = "phone"
        what = f" (<b>{esc(MACHINES[d['machine']][0])}</b>)" if d.get("machine") else ""
        return ask_phone(chat, f"💰 Narxni bilish{what}\n\nRaqamingizni yuboring — menejer siz bilan bogʻlanib, narx va shartlarni aytadi 👇")
    if flow == "service":
        st["step"] = "problem"
        return say(chat, "🛠 <b>Servis va taʼmirlash</b>\n\nMuammoni yozing. Rasm yoki video ham yuborishingiz mumkin 👇",
                   [[("❌ Bekor qilish", "cancel")]])
    if flow == "chal":
        st["step"] = "video"
        return say(chat, "🏆 <b>Eng kuchli zarba</b>\n\nBoks avtomatida zarbangiz videosini yuboring (natija tabloda koʻrinib tursin). "
                   "Eng yaxshilari kanalda chiqadi va har hafta TOP-5 eʼlon qilinadi 💪",
                   [[("🏅 Haftalik reyting", "top")], [("❌ Bekor qilish", "cancel")]])
    if flow == "visit":
        st["step"] = "day"
        today = dt.datetime.now(TZ).date()
        names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
        days = [today + dt.timedelta(days=i) for i in range(1, 8)]
        rows, row = [], []
        for dday in days:
            row.append((f"{names[dday.weekday()]} {dday:%d.%m}", f"vd:{dday:%d.%m}"))
            if len(row) == 3:
                rows.append(row); row = []
        if row:
            rows.append(row)
        return say(chat, f"📅 <b>Koʻrgazmaga yozilish</b>\n📍 {SHOWROOM}\n\nQaysi kuni kelasiz?", rows + [[("❌ Bekor qilish", "cancel")]])
    if flow == "deliv":
        st["step"] = "region"
        return ask_city(chat, "🚚 <b>Yetkazish narxi</b>\n\nViloyatingizni tanlang 👇")
    if flow == "live":
        if d.get("machine"):
            st["step"] = "phone"
            return ask_phone(chat, f"🎥 <b>{esc(MACHINES[d['machine']][0])}</b> — jonli video\n\nRaqamingizni yuboring, avtomat ishlayotgan videoni Telegram orqali yuboramiz 👇")
        st["step"] = "what"
        return say(chat, "🎥 <b>Jonli video</b>\n\nQaysi avtomatni ishlayotgan holda koʻrmoqchisiz?", [[("📋 Katalogdan tanlash", "cat")], [("❌ Bekor qilish", "cancel")]])
    if flow == "show":
        st["step"] = "photo"
        return say(chat, "📸 <b>Avtomatim — joyimda</b>\n\nPLAYMAX avtomati sizning joyingizda turibdimi? Rasmini yuboring — kanalda koʻrsatamiz! 🙌",
                   [[("❌ Bekor qilish", "cancel")]])
    if flow == "dealer":
        st["step"] = "city"
        return ask_city(chat, "🤝 <b>Diler boʻlish</b>\n\nQaysi shahar / viloyatda ishlamoqchisiz?")
    if flow == "calc":
        st["step"] = "m"
        return say(chat, "🧮 <b>Daromad kalkulyatori</b>\n\nQaysi avtomat? 👇",
                   [[(t, f"k:m:{k}")] for k, (t, _) in CALC_MACHINES.items()] + [[("❌ Bekor qilish", "cancel")]])


def ask_city(chat, text):
    rows, row = [], []
    for i, r in enumerate(REGIONS):
        row.append((r, f"rg:{i}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return say(chat, text, rows + [[("❌ Bekor qilish", "cancel")]])


def finish(u, chat, text):
    STATE.pop(u["id"], None)
    drop_kb(chat, text)
    say(chat, "Yana nima kerak? 👇", [BACK])


def handle_flow(u, chat, msg=None, cb=None):
    st = STATE.get(u["id"])
    if not st:
        return False
    f, step, d = st["flow"], st["step"], st["d"]
    text = (msg or {}).get("text", "") if msg else ""
    contact_ = (msg or {}).get("contact") if msg else None
    media = None
    if msg:
        if msg.get("photo"):
            media = ("photo", msg["photo"][-1]["file_id"])
        elif msg.get("video"):
            media = ("video", msg["video"]["file_id"])
        elif msg.get("document"):
            media = ("document", msg["document"]["file_id"])
        if msg.get("caption"):
            text = msg["caption"]
    if text == "❌ Bekor qilish":
        STATE.pop(u["id"], None)
        drop_kb(chat, "Bekor qilindi.")
        return home(chat) or True
    phone = (contact_ or {}).get("phone_number") or (text if step == "phone" and any(ch.isdigit() for ch in text) else None)

    # --- region / city selection shared
    if cb and cb.startswith("rg:"):
        d["city"] = REGIONS[int(cb[3:])]
        if f == "order":
            st["step"] = "phone"
            return ask_phone(chat, "📱 Raqamingizni yuboring — menejer siz bilan bogʻlanadi 👇") or True
        if f == "deliv":
            st["step"] = "phone"
            return ask_phone(chat, f"🚚 {esc(d['city'])}\n\nRaqamingizni yuboring — yetkazish narxini aytamiz 👇") or True
        if f == "dealer":
            st["step"] = "exp"
            return say(chat, "Oʻzingiz haqingizda qisqacha yozing: tajribangiz, joyingiz yoki doʻkoningiz bormi? 👇") or True

    if f == "order":
        if step == "what" and (text or media):
            d["what"], d["media"] = text, media
            st["step"] = "city"
            return ask_city(chat, "Qaysi shahar yoki viloyatga kerak?") or True
        if step == "phone" and phone:
            m = MACHINES.get(d.get("machine"), ("",))[0]
            notify("🛒 YANGI BUYURTMA", u, [("Avtomat", m or d.get("what")), ("Shahar", d.get("city")), ("Telefon", phone)], d.get("media"))
            return finish(u, chat, "✅ Buyurtmangiz qabul qilindi! Menejer tez orada siz bilan bogʻlanadi.\n\n"
                          f"Shoshilinch boʻlsa: {P1} / {P2}") or True
    if f == "price" and step == "phone" and phone:
        m = MACHINES.get(d.get("machine"), ("",))[0]
        notify("💰 NARX SOʻRALDI", u, [("Avtomat", m or "Umumiy"), ("Telefon", phone)])
        return finish(u, chat, "✅ Rahmat! Menejer tez orada qoʻngʻiroq qilib, narxlarni aytadi.") or True
    if f == "service":
        if step == "problem" and (text or media):
            d["problem"], d["media"] = text, media
            st["step"] = "model"
            return say(chat, "Qaysi avtomat? (nomini yozing yoki «bilmayman»)") or True
        if step == "model" and text:
            d["model"] = text
            st["step"] = "phone"
            return ask_phone(chat, "📱 Raqamingizni yuboring — usta siz bilan bogʻlanadi 👇") or True
        if step == "phone" and phone:
            notify("🛠 SERVIS SOʻROVI", u, [("Muammo", d.get("problem") or "(rasm/video)"), ("Avtomat", d.get("model")), ("Telefon", phone)], d.get("media"))
            return finish(u, chat, "✅ Soʻrovingiz qabul qilindi! Usta tez orada bogʻlanadi.") or True
    if f == "chal":
        if step == "video" and media and media[0] in ("video", "document"):
            d["media"] = media
            st["step"] = "score"
            return say(chat, "💪 Zoʻr! Natijangiz nechchi? Faqat raqam yozing (masalan 987):") or True
        if step == "score" and text.strip().isdigit():
            d["score"] = int(text.strip())
            st["step"] = "where"
            return say(chat, "📍 Qayerda urdingiz? (shahar va joy nomi):") or True
        if step == "where" and text:
            pid = f"c{int(time.time())}{u['id'] % 1000}"
            pend = load(PEND_F, {})
            pend[pid] = {"type": "chal", "user": {k: u.get(k) for k in ("id", "first_name", "username")},
                         "media": d["media"], "score": d["score"], "where": text}
            save(PEND_F, pend)
            notify("🏆 TOP ZARBA — tasdiqlash", u, [("Natija", d["score"]), ("Joy", text)], d["media"], approve=pid)
            return finish(u, chat, "✅ Videongiz yuborildi! Tasdiqlangandan keyin kanalda chiqadi va reytingga qoʻshiladi 🏆") or True
    if f == "visit":
        if cb and cb.startswith("vd:"):
            d["day"] = cb[3:]
            st["step"] = "time"
            return say(chat, "Soat nechida? 👇", [[("10:00–12:00", "vt:10:00–12:00"), ("12:00–15:00", "vt:12:00–15:00")],
                                                  [("15:00–18:00", "vt:15:00–18:00"), ("18:00 dan keyin", "vt:18:00+")]]) or True
        if cb and cb.startswith("vt:"):
            d["time"] = cb[3:]
            st["step"] = "phone"
            return ask_phone(chat, "📱 Raqamingizni yuboring — tashrifingizni tasdiqlaymiz 👇") or True
        if step == "phone" and phone:
            notify("📅 KOʻRGAZMAGA TASHRIF", u, [("Kun", d.get("day")), ("Vaqt", d.get("time")), ("Telefon", phone)])
            return finish(u, chat, f"✅ Siz {d.get('day')} kuni {d.get('time')} ga yozildingiz!\n📍 {SHOWROOM}\n\nMenejer tasdiqlash uchun qoʻngʻiroq qiladi.") or True
    if f == "deliv" and step == "phone" and phone:
        notify("🚚 YETKAZISH NARXI", u, [("Viloyat", d.get("city")), ("Telefon", phone)])
        return finish(u, chat, "✅ Rahmat! Yetkazish narxini tez orada aytamiz.") or True
    if f == "live":
        if step == "what" and text:
            d["what"] = text
            st["step"] = "phone"
            return ask_phone(chat, "📱 Raqamingizni yuboring 👇") or True
        if step == "phone" and phone:
            m = MACHINES.get(d.get("machine"), ("",))[0]
            notify("🎥 JONLI VIDEO SOʻRALDI", u, [("Avtomat", m or d.get("what")), ("Telefon", phone)])
            return finish(u, chat, "✅ Qabul qilindi! Video tez orada sizga yuboriladi.") or True
    if f == "show":
        if step == "photo" and media:
            d["media"] = media
            st["step"] = "place"
            return say(chat, "Joy nomi va shahar? (masalan: «Family Park, Samarqand»)") or True
        if step == "place" and text:
            pid = f"s{int(time.time())}{u['id'] % 1000}"
            pend = load(PEND_F, {})
            pend[pid] = {"type": "show", "user": {k: u.get(k) for k in ("id", "first_name", "username")}, "media": d["media"], "place": text}
            save(PEND_F, pend)
            notify("📸 MIJOZ JOYI — tasdiqlash", u, [("Joy", text)], d["media"], approve=pid)
            return finish(u, chat, "✅ Rahmat! Tasdiqlangandan keyin kanalda chiqadi 🙌") or True
    if f == "dealer":
        if step == "exp" and text:
            d["exp"] = text
            st["step"] = "phone"
            return ask_phone(chat, "📱 Raqamingizni yuboring 👇") or True
        if step == "phone" and phone:
            notify("🤝 DILERLIK ARIZASI", u, [("Hudud", d.get("city")), ("Maʼlumot", d.get("exp")), ("Telefon", phone)])
            return finish(u, chat, "✅ Arizangiz qabul qilindi! Hamkorlik boʻyicha menejer bogʻlanadi.") or True
    if f == "calc":
        if cb and cb.startswith("k:m:"):
            d["m"] = cb[4:]
            st["step"] = "p"
            return say(chat, "Avtomat qayerda turadi? 👇", [[(t, f"k:p:{k}")] for k, (t, _) in CALC_PLACES.items()]) or True
        if cb and cb.startswith("k:p:"):
            d["p"] = cb[4:]
            st["step"] = "t"
            return say(chat, "Kuniga taxminan necha kishi oʻtadi? 👇", [[(t, f"k:t:{k}")] for k, t in CALC_TRAFFIC.items()]) or True
        if cb and cb.startswith("k:t:"):
            d["t"] = int(cb[4:])
            st["step"] = "price"
            return say(chat, "Bitta oʻyin narxi necha soʻm boʻladi? Faqat raqam yozing (masalan 5000):") or True
        if step == "price" and text.replace(" ", "").isdigit():
            return calc_result(u, chat, d, int(text.replace(" ", ""))) or True
    return False


def calc_result(u, chat, d, price):
    mname, conv = CALC_MACHINES[d["m"]]
    pname, k = CALC_PLACES[d["p"]]
    plays = max(5, round(d["t"] * conv * k))
    lo, hi = round(plays * 0.7), round(plays * 1.3)
    day_lo, day_hi = lo * price, hi * price
    fmt = lambda x: f"{x:,}".replace(",", " ")
    tip = {"mall": "Kirish yoki oziq-ovqat zonasi yoniga qoʻying.", "cafe": "Kutish joyi yoniga — odamlar vaqt oʻtkazadi.",
           "park": "Yoʻlak boʻyida, yorugʻ joyda turgani yaxshi.", "zal": "Rekord tablosini kirishdan koʻrinadigan qiling.",
           "dokon": "Kassa yoki bolalar boʻlimi yoniga qoʻying.", "azs": "Doʻkon kirishida, yorugʻ joyda turgani yaxshi."}[d["p"]]
    STATE.pop(u["id"], None)
    say(chat, f"🧮 <b>Taxminiy hisob</b>\n\n{mname} · {pname}\n👥 Kuniga ~{d['t']} kishi · 🎟 {fmt(price)} soʻm\n\n"
        f"🎮 Kuniga taxminan <b>{lo}–{hi}</b> oʻyin\n💰 Kunlik: <b>{fmt(day_lo)} – {fmt(day_hi)} soʻm</b>\n"
        f"📅 Oylik (30 kun): <b>{fmt(day_lo * 30)} – {fmt(day_hi * 30)} soʻm</b>\n\n💡 {tip}\n\n"
        "⚠️ Bu taxminiy misol. Haqiqiy daromad joy, odamlar oqimi va oʻyin narxiga bogʻliq.",
        [[("📞 Aniq hisob uchun menejer", "price")], [("🔁 Qayta hisoblash", "calc")], BACK])
    notify("🧮 KALKULYATOR ishlatildi", u, [("Avtomat", mname), ("Joy", pname), ("Oqim", d["t"]), ("Oʻyin narxi", price),
                                           ("Natija (oy)", f"{fmt(day_lo*30)} – {fmt(day_hi*30)}")])


# ---------------------------------------------------------------- challenge
def top5():
    board = load(CH_F, [])
    week_ago = time.time() - 7 * 86400
    week = sorted([b for b in board if b["t"] > week_ago], key=lambda b: -b["score"])[:5]
    return week


def show_top(chat):
    rows = top5()
    if not rows:
        return say(chat, "🏅 Bu hafta hali natijalar yoʻq. Birinchi boʻling! 💪", [[("🏆 Video yuborish", "chal")], BACK])
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    txt = "🏅 <b>Haftaning TOP-5 zarbasi</b>\n\n" + "\n".join(
        f"{medals[i]} <b>{r['score']}</b> — {esc(r['name'])} ({esc(r['where'])})" for i, r in enumerate(rows))
    say(chat, txt, [[("🏆 Video yuborish", "chal")], BACK])


def admin_decide(u, data):
    if u["id"] not in ADMINS:
        return
    ok, pid = data.startswith("ok:"), data[3:]
    pend = load(PEND_F, {})
    p = pend.pop(pid, None)
    save(PEND_F, pend)
    if not p:
        return say(u["id"], "Bu soʻrov allaqachon koʻrib chiqilgan.")
    name = p["user"].get("first_name") or "Mijoz"
    if not ok:
        say(p["user"]["id"], "Afsuski, yuborgan materialingiz kanalga chiqmadi. Yana urinib koʻring! 🙏")
        return say(u["id"], "❌ Rad etildi.")
    typ, fid = p["media"]
    btn = {"inline_keyboard": [[{"text": "🏆 Ishtirok etish", "url": "https://t.me/playmax_uz_bot?start=chal"}],
                               [{"text": "🛒 Buyurtma berish", "url": SITE}]]}
    if p["type"] == "chal":
        cap = f"🏆 <b>Eng kuchli zarba!</b>\n\n💥 Natija: <b>{p['score']}</b>\n👤 {esc(name)}\n📍 {esc(p['where'])}\n\nSiz bundan kuchliroq ura olasizmi? Videongizni botga yuboring 👇" + FOOT
        board = load(CH_F, [])
        board.append({"t": time.time(), "score": p["score"], "name": name, "where": p["where"]})
        save(CH_F, board)
    else:
        cap = f"📸 <b>PLAYMAX avtomati — mijozimiz joyida</b>\n\n📍 {esc(p['place'])}\n\nRahmat, ishonchingiz uchun! 🙌\nSizning avtomatingiz ham shu yerda boʻlsin 👇" + FOOT
        btn = {"inline_keyboard": [[{"text": "🛒 Buyurtma berish", "url": SITE}], [{"text": "🤖 Xizmatlar", "url": "https://t.me/playmax_uz_bot"}]]}
    m = {"photo": "sendPhoto", "video": "sendVideo", "document": "sendDocument"}[typ]
    call(m, chat_id=CHANNEL, **{typ: fid}, caption=cap, parse_mode="HTML", reply_markup=btn)
    say(p["user"]["id"], "🎉 Materialingiz kanalda chiqdi! Rahmat 🙌\n" + CH_URL)
    say(u["id"], "✅ Kanalga chiqarildi.")


# ---------------------------------------------------------------- routing
def route(u, chat, key):
    if key == "menu":
        STATE.pop(u["id"], None)
        return home(chat)
    if key == "cancel":
        STATE.pop(u["id"], None)
        drop_kb(chat, "Bekor qilindi.")
        return home(chat)
    if key == "cat":
        return catalog(chat)
    if key.startswith("c:"):
        return category(chat, key[2:])
    if key.startswith("m:"):
        st = STATE.get(u["id"])
        if st and st["flow"] in ("order", "live") and st["step"] == "what":
            st["d"]["machine"] = key[2:]
            return start_flow(u, chat, st["flow"], machine=key[2:])
        return machine(chat, key[2:])
    if key.startswith("om:"):
        return start_flow(u, chat, "order", machine=key[3:])
    if key.startswith("pm:"):
        return start_flow(u, chat, "price", machine=key[3:])
    if key.startswith("lm:"):
        return start_flow(u, chat, "live", machine=key[3:])
    if key in ("order", "price", "service", "chal", "visit", "deliv", "live", "show", "dealer", "calc"):
        return start_flow(u, chat, key)
    if key == "top":
        STATE.pop(u["id"], None)
        return show_top(chat)
    if key == "contact":
        return contact(chat)
    if key == "loc":
        return locations(chat)
    return home(chat)


def on_message(msg):
    if msg["chat"]["type"] != "private":
        return
    u, chat = msg["from"], msg["chat"]["id"]
    text = msg.get("text", "") or ""
    if text.startswith("/start"):
        arg = text.split(" ", 1)[1] if " " in text else ""
        STATE.pop(u["id"], None)
        if arg in ("chal", "order", "price", "calc", "service", "visit", "dealer", "show", "live", "deliv"):
            return start_flow(u, chat, arg)
        if arg == "catalog":
            return catalog(chat)
        return home(chat, u.get("first_name", ""))
    cmds = {"/menu": "menu", "/katalog": "cat", "/buyurtma": "order", "/narx": "price", "/kalkulyator": "calc",
            "/servis": "service", "/aloqa": "contact", "/manzil": "loc", "/top": "top"}
    if text.split("@")[0] in cmds:
        STATE.pop(u["id"], None)
        return route(u, chat, cmds[text.split("@")[0]])
    if handle_flow(u, chat, msg=msg):
        return
    low = text.lower()
    if any(w in low for w in ("boks", "box", "бокс")):
        return category(chat, "boks")
    if any(w in low for w in ("narx", "цена", "price", "qancha")):
        return start_flow(u, chat, "price")
    say(chat, "Quyidagi menyudan tanlang 👇", MENU)


def on_callback(q):
    u = q["from"]
    data = q.get("data", "")
    chat = (q.get("message") or {}).get("chat", {}).get("id", u["id"])
    call("answerCallbackQuery", callback_query_id=q["id"])
    if data.startswith(("ok:", "no:")):
        return admin_decide(u, data)
    if data.startswith(("rg:", "vd:", "vt:", "k:")) and handle_flow(u, chat, cb=data):
        return
    route(u, chat, data)


# ---------------------------------------------------------------- persistence
def load(path, default):
    try:
        with open(path, encoding="utf8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def git_sync():
    try:
        subprocess.run(["git", "add", "data"], cwd=ROOT, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
            return
        subprocess.run(["git", "commit", "-qm", "bot: data"], cwd=ROOT, check=True)
        for _ in range(3):
            subprocess.run(["git", "pull", "-q", "--rebase", "-X", "theirs"], cwd=ROOT)
            if subprocess.run(["git", "push", "-q"], cwd=ROOT).returncode == 0:
                return
    except Exception as e:
        print("[git]", e)


def setup():
    call("deleteWebhook")
    call("setMyCommands", commands=[
        {"command": "menu", "description": "Bosh menyu"}, {"command": "katalog", "description": "Katalog"},
        {"command": "buyurtma", "description": "Buyurtma berish"}, {"command": "narx", "description": "Narxni bilish"},
        {"command": "kalkulyator", "description": "Daromad kalkulyatori"}, {"command": "servis", "description": "Servis va taʼmirlash"},
        {"command": "top", "description": "Haftaning TOP-5 zarbasi"}, {"command": "aloqa", "description": "Aloqa"},
        {"command": "manzil", "description": "Manzillar"}])


def main():
    setup()
    start, offset, last_sync = time.time(), None, time.time()
    print("bot started")
    while time.time() - start < RUN_SECONDS:
        ups = call("getUpdates", offset=offset, timeout=50, allowed_updates=["message", "callback_query"]) or []
        for up in ups:
            offset = up["update_id"] + 1
            try:
                if "message" in up:
                    on_message(up["message"])
                elif "callback_query" in up:
                    on_callback(up["callback_query"])
            except Exception as e:
                print("[handler]", repr(e))
        if time.time() - last_sync > 600:
            git_sync()
            last_sync = time.time()
    if offset:
        call("getUpdates", offset=offset, timeout=0)
    git_sync()
    print("shift finished")


if __name__ == "__main__":
    main()

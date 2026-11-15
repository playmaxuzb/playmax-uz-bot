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
    [("🛠 Servis va taʼmirlash", "service"), ("📅 Tashrif buyurish", "visit")],
    [("🚚 Yetkazish narxi", "deliv"), ("🤝 Hamkorlik", "partner")],
    [("🏆 Eng kuchli zarba", "chal"), ("♻️ PLAYMAX avtomatimni sotaman", "resell")],
    [("🎥 Jonli video", "live"), ("📸 Avtomatim — joyimda", "show")],
    [("📍 Manzillar", "loc"), ("📞 Aloqa", "contact")],
    [("🌍 Xalqaro kanal", "global"), ("🌐 Sayt", SITE)],
]
BACK = [("⬅️ Bosh menyu", "menu")]
LINKS = [[("📸 Instagram", IG), ("🌐 Sayt", SITE)], [("📢 Kanal", CH_URL), ("🌍 Xalqaro kanal", GLOBAL_CH)]]
CANCEL = [("❌ Bekor qilish", "cancel")]
CFG_F = os.path.join(ROOT, "data", "config.json")


def cfg():
    return load(CFG_F, {})


def home(chat, name=""):
    hi = f"Assalomu alaykum, {esc(name)}! 👋\n\n" if name else ""
    return call("sendPhoto", chat_id=chat, photo=RAW + "showcase-product-lineup.jpg", parse_mode="HTML",
                caption=hi + "<b>PLAYMAX</b> — oʻyin avtomatlari Oʻzbekistonda 🇺🇿\n\n"
                "Katalog, buyurtma, narx, servis va boshqa xizmatlar — hammasi shu yerda. Tanlang 👇",
                reply_markup=ikb(MENU))


def contact(chat):
    say(chat, "📞 <b>Biz bilan bogʻlaning</b>\n\n"
        f"📞 {P1}\n📞 {P2}\n✉️ {EMAIL}\n🌐 playmaxuz.com\n📸 Instagram: {IG}\n\n📍 Koʻrgazma: {SHOWROOM}",
        LINKS + [BACK])


def global_ch(chat):
    say(chat, "🌍 <b>PLAYMAX — xalqaro kanal</b>\n\n"
        "Bu ham PLAYMAX — xuddi shu avtomatlar va xizmatlar, lekin boshqa davlatlar va tillar uchun: "
        "oʻzbek, rus, dari, ingliz va arab tillarida.\n\n"
        "Qarindosh yoki hamkoringiz boshqa davlatda boʻlsa — ularga ulashing. Hamma oʻz tilida, qulay xizmat oladi 🤝",
        [[("🌍 Xalqaro kanalga qoʻshilish", GLOBAL_CH)], BACK])


def locations(chat):
    call("sendVenue", chat_id=chat, latitude=OFFICE[0], longitude=OFFICE[1], title="🏢 PLAYMAX ofisi",
         address="Toshkent", reply_markup=ikb([[("🚗 Ofisga yoʻl (Yandex)", ROUTE_OFFICE)]]))
    call("sendVenue", chat_id=chat, latitude=FACTORY[0], longitude=FACTORY[1], title="🏭 PLAYMAX zavodi",
         address="Toshkent", reply_markup=ikb([[("🚗 Zavodga yoʻl (Yandex)", ROUTE_FACTORY)]]))
    say(chat, f"📍 Koʻrgazma: {SHOWROOM}\n\nKelishdan oldin vaqtni band qiling 👇" + FOOT,
        [[("📅 Tashrif buyurish", "visit")], BACK])


def catalog(chat):
    say(chat, "📋 <b>Katalog</b> — turini tanlang 👇", [[(t, f"c:{k}")] for k, (t, _) in CATALOG.items()] + [BACK])


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


# ---------------------------------------------------------------- admin cards (private only)
def user_line(u):
    name = esc(" ".join(x for x in (u.get("first_name"), u.get("last_name")) if x))
    uname = f" @{u['username']}" if u.get("username") else ""
    return f'👤 <a href="tg://user?id={u["id"]}">{name or "Mijoz"}</a>{esc(uname)} · ID <code>{u["id"]}</code>'


def targets():
    t = cfg().get("notify")
    return [t] if t else ADMINS


def notify(kind, u, fields, media=None, approve=None, extra_media=None):
    now = dt.datetime.now(TZ).strftime("%d.%m %H:%M")
    text = f"🔔 <b>{kind}</b> · {now}\n{user_line(u)}\n\n" + "\n".join(f"<b>{esc(k)}:</b> {esc(v)}" for k, v in fields if v)
    rows = [[("💬 Mijozga yozish", f"tg://user?id={u['id']}")]]
    if approve:
        rows = [[("✅ Tasdiqlash", f"ok:{approve}"), ("❌ Rad etish", f"no:{approve}")]] + rows
    for a in targets():
        for typ, fid in (extra_media or []):
            m = {"photo": "sendPhoto", "video": "sendVideo", "document": "sendDocument"}[typ]
            call(m, chat_id=a, **{typ: fid})
        if media:
            typ, fid = media
            m = {"photo": "sendPhoto", "video": "sendVideo", "document": "sendDocument"}[typ]
            call(m, chat_id=a, **{typ: fid}, caption=text[:1024], parse_mode="HTML", reply_markup=ikb(rows))
        else:
            say(a, text, rows)


# ---------------------------------------------------------------- flows
def region_kb(prefix="rg"):
    rows, row = [], []
    for i, r in enumerate(REGION_NAMES):
        row.append((r, f"{prefix}:{i}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return rows + [CANCEL]


def district_kb(ri):
    rows, row = [], []
    for j, dname in enumerate(REGIONS[REGION_NAMES[ri]]):
        row.append((dname, f"ds:{ri}:{j}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return rows + [[("✍️ Boshqa joy — yozaman", f"ds:{ri}:x")], CANCEL]


def ask(chat, text, rows=None):
    return say(chat, text, (rows or []) + [CANCEL])


def start_flow(u, chat, flow, **d):
    STATE[u["id"]] = {"flow": flow, "step": "", "d": d}
    st = STATE[u["id"]]
    if flow == "order":
        if d.get("machine"):
            st["step"] = "region"
            return say(chat, f"🛒 <b>{esc(MACHINES[d['machine']][0])}</b>\n\nQaysi viloyatga kerak? 👇", region_kb())
        st["step"] = "what"
        return ask(chat, "🛒 <b>Buyurtma</b>\n\nQaysi avtomat kerak? Katalogdan tanlang, yoki yozing / rasm yuboring 👇", [[("📋 Katalogdan tanlash", "cat")]])
    if flow == "price":
        st["step"] = "phone"
        what = f" — <b>{esc(MACHINES[d['machine']][0])}</b>" if d.get("machine") else ""
        return ask_phone(chat, f"💰 Narxni bilish{what}\n\nRaqamingizni yuboring — menejer narx va shartlarni aytadi 👇")
    if flow == "service":
        st["step"] = "problem"
        return ask(chat, "🛠 <b>Servis va taʼmirlash</b>\n\nMuammoni yozing. Rasm yoki video ham yuborishingiz mumkin 👇")
    if flow == "visit":
        st["step"] = "place"
        return ask(chat, "📅 <b>Tashrif buyurish</b>\n\nQayerga kelmoqchisiz? 👇",
                   [[("🏢 Ofis va koʻrgazma", "vp:ofis")], [("🏭 Zavod", "vp:zavod")]])
    if flow == "deliv":
        st["step"] = "region"
        return say(chat, "🚚 <b>Yetkazish narxi</b>\n\nViloyatingizni tanlang 👇", region_kb())
    if flow == "partner":
        st["step"] = "type"
        return ask(chat, "🤝 <b>PLAYMAX bilan hamkorlik</b>\n\nQanday hamkorlik sizni qiziqtiradi? 👇",
                   [[(t, f"pt:{k}")] for k, t in PARTNER_TYPES.items()])
    if flow == "live":
        if d.get("machine"):
            st["step"] = "phone"
            return ask_phone(chat, f"🎥 <b>{esc(MACHINES[d['machine']][0])}</b> — jonli video\n\nRaqamingizni yuboring, ishlayotgan videoni yuboramiz 👇")
        st["step"] = "what"
        return ask(chat, "🎥 <b>Jonli video</b>\n\nQaysi avtomatni koʻrmoqchisiz?", [[("📋 Katalogdan tanlash", "cat")]])
    if flow == "chal":
        st["step"] = "logo"
        return ask(chat, "🏆 <b>Eng kuchli zarba</b>\n\nFaqat <b>PLAYMAX</b> boks avtomatlari qatnashadi.\n\n"
                   "1️⃣ Avval avtomatdagi <b>PLAYMAX logotipi</b> rasmini yuboring 👇", [[("🏅 Haftalik reyting", "top")]])
    if flow == "resell":
        st["step"] = "logo"
        d["photos"] = []
        return ask(chat, "♻️ <b>PLAYMAX avtomatingizni sotish</b>\n\nFaqat <b>PLAYMAX</b> avtomatlari qabul qilinadi.\n\n"
                   "1️⃣ Avtomatdagi <b>PLAYMAX logotipi</b> aniq koʻrinadigan rasmni yuboring 👇")
    if flow == "show":
        st["step"] = "photo"
        return ask(chat, "📸 <b>Avtomatim — joyimda</b>\n\nPLAYMAX avtomati sizning joyingizda turibdimi? Rasmini yuboring (logotip koʻrinsin) 👇")
    if flow == "calc":
        st["step"] = "m"
        return ask(chat, "🧮 <b>Daromad kalkulyatori</b>\n\nQaysi avtomat? 👇", [[(t, f"k:m:{k}")] for k, (t, _) in CALC_MACHINES.items()])


def finish(u, chat, text):
    STATE.pop(u["id"], None)
    drop_kb(chat, text)
    say(chat, f"📞 {P1}\n📞 {P2}\n✉️ {EMAIL}\n\nYana nima kerak? 👇", LINKS + [BACK])


def save_pending(kind, u, d):
    pid = f"{kind[0]}{int(time.time())}{u['id'] % 1000}"
    pend = load(PEND_F, {})
    pend[pid] = {"type": kind, "user": {k: u.get(k) for k in ("id", "first_name", "username")}, **d}
    save(PEND_F, pend)
    return pid


def handle_flow(u, chat, msg=None, cb=None):
    st = STATE.get(u["id"])
    if not st:
        return False
    f, step, d = st["flow"], st["step"], st["d"]
    text, media = "", None
    if msg:
        text = msg.get("text") or msg.get("caption") or ""
        if msg.get("photo"):
            media = ("photo", msg["photo"][-1]["file_id"])
        elif msg.get("video"):
            media = ("video", msg["video"]["file_id"])
        elif msg.get("document"):
            media = ("document", msg["document"]["file_id"])
    if text == "❌ Bekor qilish":
        STATE.pop(u["id"], None)
        drop_kb(chat, "Bekor qilindi.")
        home(chat)
        return True
    contact_ = (msg or {}).get("contact")
    phone = (contact_ or {}).get("phone_number") or (text if step == "phone" and sum(c.isdigit() for c in text) >= 7 else None)
    if step == "phone" and msg and not phone:
        ask_phone(chat, "📱 Iltimos, telefon raqamingizni yuboring (tugmani bosing yoki yozing) 👇")
        return True

    # shared: region -> district
    if cb and cb.startswith("rg:"):
        d["region"] = REGION_NAMES[int(cb[3:])]
        if f == "deliv":
            st["step"] = "district"
            say(chat, f"📍 {esc(d['region'])} — tuman yoki shaharni tanlang 👇", district_kb(int(cb[3:])))
            return True
        st["step"] = "phone"
        ask_phone(chat, "📱 Raqamingizni yuboring — menejer siz bilan bogʻlanadi 👇")
        return True
    if cb and cb.startswith("ds:"):
        _, ri, j = cb.split(":")
        if j == "x":
            st["step"] = "district_text"
            ask(chat, "Tuman / shahar nomini yozing 👇")
            return True
        d["district"] = REGIONS[REGION_NAMES[int(ri)]][int(j)]
        st["step"] = "phone"
        ask_phone(chat, f"🚚 {esc(d['region'])}, {esc(d['district'])}\n\nRaqamingizni yuboring — yetkazish narxini aytamiz 👇")
        return True
    if step == "district_text" and text:
        d["district"] = text
        st["step"] = "phone"
        ask_phone(chat, "📱 Raqamingizni yuboring 👇")
        return True

    if f == "order":
        if step == "what" and (text or media):
            d["what"], d["media"] = text, media
            st["step"] = "region"
            say(chat, "Qaysi viloyatga kerak? 👇", region_kb())
            return True
        if step == "phone" and phone:
            m = MACHINES.get(d.get("machine"), ("",))[0]
            notify("🛒 YANGI BUYURTMA", u, [("Avtomat", m or d.get("what")), ("Viloyat", d.get("region")), ("Telefon", phone)], d.get("media"))
            finish(u, chat, "✅ Buyurtmangiz qabul qilindi! Menejer tez orada bogʻlanadi.")
            return True
    if f == "price" and step == "phone" and phone:
        m = MACHINES.get(d.get("machine"), ("",))[0]
        notify("💰 NARX SOʻRALDI", u, [("Avtomat", m or "Umumiy"), ("Telefon", phone)])
        finish(u, chat, "✅ Rahmat! Menejer tez orada qoʻngʻiroq qilib, narxlarni aytadi.")
        return True
    if f == "service":
        if step == "problem" and (text or media):
            d["problem"], d["media"] = text, media
            st["step"] = "model"
            ask(chat, "Qaysi avtomat? (nomini yozing yoki «bilmayman»)")
            return True
        if step == "model" and text:
            d["model"] = text
            st["step"] = "phone"
            ask_phone(chat, "📱 Raqamingizni yuboring — usta siz bilan bogʻlanadi 👇")
            return True
        if step == "phone" and phone:
            notify("🛠 SERVIS SOʻROVI", u, [("Muammo", d.get("problem") or "(rasm/video)"), ("Avtomat", d.get("model")), ("Telefon", phone)], d.get("media"))
            finish(u, chat, "✅ Soʻrovingiz qabul qilindi! Usta tez orada bogʻlanadi.")
            return True
    if f == "visit":
        if cb and cb.startswith("vp:"):
            d["place"] = "🏢 Ofis va koʻrgazma" if cb[3:] == "ofis" else "🏭 Zavod"
            st["step"] = "day"
            today = dt.datetime.now(TZ).date()
            names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
            rows, row = [], []
            for i in range(1, 8):
                dd = today + dt.timedelta(days=i)
                row.append((f"{names[dd.weekday()]} {dd:%d.%m}", f"vd:{dd:%d.%m}"))
                if len(row) == 3:
                    rows.append(row); row = []
            if row:
                rows.append(row)
            ask(chat, f"{d['place']}\n\nQaysi kuni kelasiz? 👇", rows)
            return True
        if cb and cb.startswith("vd:"):
            d["day"] = cb[3:]
            st["step"] = "time"
            ask(chat, "Soat nechida? 👇", [[("10:00–12:00", "vt:10:00–12:00"), ("12:00–15:00", "vt:12:00–15:00")],
                                          [("15:00–18:00", "vt:15:00–18:00"), ("18:00 dan keyin", "vt:18:00+")]])
            return True
        if cb and cb.startswith("vt:"):
            d["time"] = cb[3:]
            st["step"] = "phone"
            ask_phone(chat, "📱 Raqamingizni yuboring — tashrifni tasdiqlaymiz 👇")
            return True
        if step == "phone" and phone:
            notify("📅 TASHRIF", u, [("Joy", d.get("place")), ("Kun", d.get("day")), ("Vaqt", d.get("time")), ("Telefon", phone)])
            finish(u, chat, f"✅ {d.get('place')} — {d.get('day')}, {d.get('time')}.\nMenejer tasdiqlash uchun qoʻngʻiroq qiladi.")
            return True
    if f == "deliv" and step == "phone" and phone:
        notify("🚚 YETKAZISH NARXI", u, [("Viloyat", d.get("region")), ("Tuman / shahar", d.get("district")), ("Telefon", phone)])
        finish(u, chat, "✅ Rahmat! Yetkazish narxini tez orada aytamiz.")
        return True
    if f == "partner":
        if cb and cb.startswith("pt:"):
            d["type"] = PARTNER_TYPES[cb[3:]]
            st["step"] = "details"
            ask(chat, f"{d['type']}\n\nQisqacha yozing: nima taklif qilasiz yoki nima kerak? 👇", [[("⏭ Oʻtkazib yuborish", "skip")]])
            return True
        if step == "details" and (text or cb == "skip"):
            d["details"] = text
            st["step"] = "region"
            say(chat, "Qaysi viloyatdasiz? 👇", region_kb())
            return True
        if step == "phone" and phone:
            notify("🤝 HAMKORLIK", u, [("Turi", d.get("type")), ("Tafsilot", d.get("details")), ("Viloyat", d.get("region")), ("Telefon", phone)])
            finish(u, chat, "✅ Taklifingiz qabul qilindi! Hamkorlik boʻyicha menejer bogʻlanadi.")
            return True
    if f == "live":
        if step == "what" and text:
            d["what"] = text
            st["step"] = "phone"
            ask_phone(chat, "📱 Raqamingizni yuboring 👇")
            return True
        if step == "phone" and phone:
            m = MACHINES.get(d.get("machine"), ("",))[0]
            notify("🎥 JONLI VIDEO", u, [("Avtomat", m or d.get("what")), ("Telefon", phone)])
            finish(u, chat, "✅ Qabul qilindi! Video tez orada yuboriladi.")
            return True
    if f == "chal":
        if step == "logo" and media and media[0] == "photo":
            d["logo"] = media
            st["step"] = "video"
            ask(chat, "2️⃣ Endi zarbangiz videosini yuboring — natija tabloda koʻrinsin 👇")
            return True
        if step == "logo" and msg:
            ask(chat, "Iltimos, PLAYMAX logotipi koʻrinadigan <b>rasm</b> yuboring 👇")
            return True
        if step == "video" and media and media[0] in ("video", "document"):
            d["media"] = media
            st["step"] = "score"
            ask(chat, "3️⃣ Natijangiz nechchi? Faqat raqam (masalan 987):")
            return True
        if step == "score" and text.strip().isdigit():
            d["score"] = int(text.strip())
            st["step"] = "where"
            ask(chat, "4️⃣ Qayerda urdingiz? (shahar va joy nomi):")
            return True
        if step == "where" and text:
            pid = save_pending("chal", u, {"media": d["media"], "score": d["score"], "where": text})
            notify("🏆 ENG KUCHLI ZARBA — tekshirish", u, [("Natija", d["score"]), ("Joy", text),
                   ("Tekshiring", "PLAYMAX avtomatimi? Logotip rasmi yuqorida")], d["media"], approve=pid, extra_media=[d["logo"]])
            finish(u, chat, "✅ Videongiz tekshiruvga yuborildi! PLAYMAX avtomati ekani tasdiqlansa, reytingga qoʻshiladi 🏆")
            return True
    if f == "resell":
        if step == "logo" and media and media[0] == "photo":
            d["logo"] = media
            st["step"] = "photos"
            ask(chat, "2️⃣ Avtomatning umumiy rasmlarini yuboring (1–5 ta). Tayyor boʻlgach tugmani bosing 👇", [[("✅ Tayyor", "rs:done")]])
            return True
        if step == "logo" and msg:
            ask(chat, "Iltimos, PLAYMAX logotipi koʻrinadigan <b>rasm</b> yuboring 👇")
            return True
        if step == "photos" and media:
            if len(d["photos"]) < 5:
                d["photos"].append(media)
            say(chat, f"📷 {len(d['photos'])} ta rasm qabul qilindi.", [[("✅ Tayyor", "rs:done")]])
            return True
        if step == "photos" and cb == "rs:done" and d["photos"]:
            st["step"] = "model"
            ask(chat, "3️⃣ Avtomat modeli? (masalan: MANGU, SPACE, KING OF THE HAMMER)")
            return True
        if step == "model" and text:
            d["model"] = text
            st["step"] = "cond"
            ask(chat, "4️⃣ Holati qanday? 👇", [[(t, f"cd:{k}")] for k, t in CONDITIONS.items()])
            return True
        if cb and cb.startswith("cd:"):
            d["cond"] = CONDITIONS[cb[3:]]
            st["step"] = "price"
            ask(chat, "5️⃣ Narxi (soʻm yoki $) va shahar? Masalan: «25 000 000 soʻm, Samarqand»")
            return True
        if step == "price" and text:
            d["price"] = text
            st["step"] = "phone"
            ask_phone(chat, "6️⃣ Xaridorlar bogʻlanishi uchun raqamingizni yuboring 👇")
            return True
        if step == "phone" and phone:
            pid = save_pending("resell", u, {"photos": d["photos"], "model": d["model"], "cond": d["cond"], "price": d["price"], "phone": phone})
            notify("♻️ AVTOMAT SOTUVI — tekshirish", u, [("Model", d["model"]), ("Holati", d["cond"]), ("Narx / shahar", d["price"]),
                   ("Telefon", phone), ("Tekshiring", "Logotip rasmi — PLAYMAX avtomatimi?")], d["logo"], approve=pid, extra_media=d["photos"])
            finish(u, chat, "✅ Eʼloningiz tekshiruvga yuborildi! PLAYMAX avtomati ekani tasdiqlansa, eʼlon chiqariladi.")
            return True
    if f == "show":
        if step == "photo" and media:
            d["media"] = media
            st["step"] = "place"
            ask(chat, "Joy nomi va shahar? (masalan: «Family Park, Samarqand»)")
            return True
        if step == "place" and text:
            pid = save_pending("show", u, {"media": d["media"], "place": text})
            notify("📸 MIJOZ JOYI — tekshirish", u, [("Joy", text)], d["media"], approve=pid)
            finish(u, chat, "✅ Rahmat! Rasmingiz tekshiruvga yuborildi 🙌")
            return True
    if f == "calc":
        if cb and cb.startswith("k:m:"):
            d["m"] = cb[4:]
            st["step"] = "p"
            ask(chat, "Avtomat qayerda turadi? 👇", [[(t, f"k:p:{k}")] for k, (t, _) in CALC_PLACES.items()])
            return True
        if cb and cb.startswith("k:p:"):
            d["p"] = cb[4:]
            st["step"] = "t"
            ask(chat, "Kuniga taxminan necha kishi oʻtadi? 👇", [[(t, f"k:t:{k}")] for k, t in CALC_TRAFFIC.items()])
            return True
        if cb and cb.startswith("k:t:"):
            d["t"] = int(cb[4:])
            st["step"] = "price"
            ask(chat, "Bitta oʻyin narxi necha soʻm? Faqat raqam (masalan 5000):")
            return True
        if step == "price" and text.replace(" ", "").isdigit():
            calc_result(u, chat, d, int(text.replace(" ", "")))
            return True
    if msg:
        say(chat, "Iltimos, koʻrsatilgan tugmalardan foydalaning yoki soʻralgan maʼlumotni yuboring 👇", [CANCEL])
        return True
    return False


def calc_result(u, chat, d, price):
    mname, conv = CALC_MACHINES[d["m"]]
    pname, k = CALC_PLACES[d["p"]]
    plays = max(5, round(d["t"] * conv * k))
    lo, hi = round(plays * 0.7), round(plays * 1.3)
    fmt = lambda x: f"{x:,}".replace(",", " ")
    tip = {"mall": "Kirish yoki oziq-ovqat zonasi yoniga qoʻying.", "cafe": "Kutish joyi yoniga — odamlar vaqt oʻtkazadi.",
           "park": "Yoʻlak boʻyida, yorugʻ joyda turgani yaxshi.", "zal": "Rekord tablosini kirishdan koʻrinadigan qiling.",
           "dokon": "Kassa yoki bolalar boʻlimi yoniga qoʻying.", "azs": "Doʻkon kirishida, yorugʻ joyda turgani yaxshi."}[d["p"]]
    STATE.pop(u["id"], None)
    say(chat, f"🧮 <b>Taxminiy hisob</b>\n\n{mname} · {pname}\n👥 Kuniga ~{d['t']} kishi · 🎟 {fmt(price)} soʻm\n\n"
        f"🎮 Kuniga taxminan <b>{lo}–{hi}</b> oʻyin\n💰 Kunlik: <b>{fmt(lo*price)} – {fmt(hi*price)} soʻm</b>\n"
        f"📅 Oylik (30 kun): <b>{fmt(lo*price*30)} – {fmt(hi*price*30)} soʻm</b>\n\n💡 {tip}\n\n"
        "⚠️ Bu taxminiy misol. Haqiqiy daromad joy, odamlar oqimi va oʻyin narxiga bogʻliq.",
        [[("📞 Aniq hisob uchun menejer", "price")], [("🔁 Qayta hisoblash", "calc")], BACK])
    notify("🧮 KALKULYATOR", u, [("Avtomat", mname), ("Joy", pname), ("Oqim", d["t"]), ("Oʻyin narxi", price),
                                ("Natija (oy)", f"{fmt(lo*price*30)} – {fmt(hi*price*30)}")])


# ---------------------------------------------------------------- challenge & community
def top5():
    board = load(CH_F, [])
    week_ago = time.time() - 7 * 86400
    return sorted([b for b in board if b["t"] > week_ago], key=lambda b: -b["score"])[:5]


def show_top(chat):
    rows = top5()
    if not rows:
        return say(chat, "🏅 Bu hafta hali natijalar yoʻq. Birinchi boʻling! 💪", [[("🏆 Qatnashish", "chal")], BACK])
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    say(chat, "🏅 <b>Haftaning TOP-5 zarbasi</b> (faqat PLAYMAX avtomatlari)\n\n" + "\n".join(
        f"{medals[i]} <b>{r['score']}</b> — {esc(r['name'])} ({esc(r['where'])})" for i, r in enumerate(rows)),
        [[("🏆 Qatnashish", "chal")], BACK])


def admin_decide(u, data):
    if u["id"] not in ADMINS:
        return
    ok, pid = data.startswith("ok:"), data[3:]
    pend = load(PEND_F, {})
    p = pend.pop(pid, None)
    save(PEND_F, pend)
    if not p:
        return say(u["id"], "Bu soʻrov allaqachon koʻrib chiqilgan.")
    seller = p["user"]["id"]
    if not ok:
        say(seller, "Afsuski, materialingiz tasdiqlanmadi. Faqat PLAYMAX avtomatlari qabul qilinadi 🙏")
        return say(u["id"], "❌ Rad etildi.")
    name = p["user"].get("first_name") or "Mijoz"
    if p["type"] == "chal":
        board = load(CH_F, [])
        board.append({"t": time.time(), "score": p["score"], "name": name, "where": p["where"]})
        save(CH_F, board)
    community = cfg().get("community")
    if community:
        btn = {"inline_keyboard": [[{"text": "🤖 PLAYMAX xizmatlari", "url": "https://t.me/playmax_uz_bot"}]]}
        if p["type"] == "chal":
            typ, fid = p["media"]
            m = {"photo": "sendPhoto", "video": "sendVideo", "document": "sendDocument"}[typ]
            call(m, chat_id=community, **{typ: fid}, parse_mode="HTML", reply_markup=btn,
                 caption=f"🏆 <b>Eng kuchli zarba</b>\n\n💥 Natija: <b>{p['score']}</b>\n👤 {esc(name)}\n📍 {esc(p['where'])}")
        elif p["type"] == "show":
            typ, fid = p["media"]
            call("sendPhoto" if typ == "photo" else "sendVideo", chat_id=community, **{typ: fid}, parse_mode="HTML",
                 reply_markup=btn, caption=f"📸 <b>PLAYMAX avtomati — mijozimiz joyida</b>\n📍 {esc(p['place'])}")
        elif p["type"] == "resell":
            group = [{"type": t, "media": f} for t, f in p["photos"] if t in ("photo", "video")][:5]
            if group:
                group[0]["caption"] = (f"♻️ <b>Sotiladi: {esc(p['model'])}</b> (PLAYMAX)\n\n{p['cond']}\n💰 {esc(p['price'])}\n"
                                       f"📞 Sotuvchi: {esc(p['phone'])}")
                group[0]["parse_mode"] = "HTML"
                call("sendMediaGroup", chat_id=community, media=group)
        say(u["id"], "✅ Tasdiqlandi va hamjamiyat kanaliga chiqarildi.")
    else:
        say(u["id"], "✅ Tasdiqlandi. (Hamjamiyat kanali hali ulanmagan — /setcommunity @kanal_nomi)")
    say(seller, "🎉 Materialingiz tasdiqlandi! Rahmat 🙌")


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
            return start_flow(u, chat, st["flow"], machine=key[2:])
        return machine(chat, key[2:])
    if key.startswith("om:"):
        return start_flow(u, chat, "order", machine=key[3:])
    if key.startswith("pm:"):
        return start_flow(u, chat, "price", machine=key[3:])
    if key.startswith("lm:"):
        return start_flow(u, chat, "live", machine=key[3:])
    if key in FLOWS:
        return start_flow(u, chat, key)
    if key == "top":
        STATE.pop(u["id"], None)
        return show_top(chat)
    if key == "contact":
        return contact(chat)
    if key == "loc":
        return locations(chat)
    if key == "global":
        return global_ch(chat)
    return home(chat)


FLOWS = ("order", "price", "service", "chal", "visit", "deliv", "live", "show", "partner", "calc", "resell")


def on_message(msg):
    u, chat = msg["from"], msg["chat"]["id"]
    text = msg.get("text", "") or ""
    if msg["chat"]["type"] != "private":
        # admin binds a private admin group for notifications
        if text.startswith("/setadmin") and u["id"] in ADMINS:
            c = cfg(); c["notify"] = chat; save(CFG_F, c)
            say(chat, "✅ Endi barcha soʻrovlar shu guruhga keladi.")
        return
    if u["id"] in ADMINS and text.startswith("/setcommunity"):
        arg = text.split(" ", 1)[1].strip() if " " in text else ""
        c = cfg(); c["community"] = arg or None; save(CFG_F, c)
        return say(chat, f"✅ Hamjamiyat kanali: {esc(arg) or 'oʻchirildi'}")
    if u["id"] in ADMINS and text.startswith("/setadmin"):
        c = cfg(); c.pop("notify", None); save(CFG_F, c)
        return say(chat, "✅ Soʻrovlar endi shaxsiy chatga keladi.")
    if text.startswith("/start"):
        arg = text.split(" ", 1)[1] if " " in text else ""
        STATE.pop(u["id"], None)
        if arg in FLOWS:
            return start_flow(u, chat, arg)
        if arg == "catalog":
            return catalog(chat)
        return home(chat, u.get("first_name", ""))
    cmds = {"/menu": "menu", "/katalog": "cat", "/buyurtma": "order", "/narx": "price", "/kalkulyator": "calc",
            "/servis": "service", "/aloqa": "contact", "/manzil": "loc", "/top": "top", "/hamkorlik": "partner"}
    c0 = text.split("@")[0].split(" ")[0]
    if c0 in cmds:
        STATE.pop(u["id"], None)
        return route(u, chat, cmds[c0])
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
    if data.startswith(("rg:", "ds:", "vp:", "vd:", "vt:", "k:", "pt:", "cd:", "rs:")) or data == "skip":
        if handle_flow(u, chat, cb=data):
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
        {"command": "top", "description": "Haftaning TOP-5 zarbasi"}, {"command": "hamkorlik", "description": "Hamkorlik"}, {"command": "aloqa", "description": "Aloqa"},
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

"""Post the weekly TOP-5 strongest punches to the channel (run Sunday evening)."""
import time
from bot import top5, call, esc, cfg, FOOT

rows = top5() if cfg().get("community") else []
if rows:
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    txt = "🏅 <b>Haftaning TOP-5 eng kuchli zarbasi</b>\n\n" + "\n".join(
        f"{medals[i]} <b>{r['score']}</b> — {esc(r['name'])} ({esc(r['where'])})" for i, r in enumerate(rows))
    txt += "\n\nKeyingi hafta siz ham roʻyxatda boʻling! Videongizni botga yuboring 👇" + FOOT
    call("sendMessage", chat_id=cfg().get("community"), text=txt, parse_mode="HTML", link_preview_options={"is_disabled": True},
         reply_markup={"inline_keyboard": [[{"text": "🏆 Ishtirok etish", "url": "https://t.me/playmax_uz_bot?start=chal"}]]})
    print("posted top", len(rows))
else:
    print("no entries this week")

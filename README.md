# Mini Stadion — Telegram bot + Mini App

Mini futbol maydoni uchun bron tizimi. Mini App **GitHub Pages** da ochiladi — maxsus domen sotib olish shart emas.

Manzil: [https://nadirkarimov.github.io/Mini_Stadion/](https://nadirkarimov.github.io/Mini_Stadion/)

Repo: [https://github.com/NadirKarimov/Mini_Stadion](https://github.com/NadirKarimov/Mini_Stadion)

---

## Qanday ishlaydi

- **Mini App** (HTML) — GitHub Pages, bepul HTTPS
- **Bot** — sizning kompyuterda `start.bat` (polling)
- **Bron** — Mini Appdan botga ketadi (Telegram `sendData`)
- **Ranglar** — bot `webapp/data/public.json` ni GitHubga yangilab turadi

Repozitoriy **public** bo‘lishi kerak.

---

## 1) GitHubga qo‘yish

1. Kodni [Mini_Stadion](https://github.com/NadirKarimov/Mini_Stadion) repositoriyasiga push qiling.
2. Repo → **Settings → Pages**
   - Source: **GitHub Actions**
3. **Actions** da `Mini App (GitHub Pages)` yashil bo‘lishi kerak.
4. Mini App manzili:

```
https://nadirkarimov.github.io/Mini_Stadion/
```

@BotFather → botingiz → **Bot Settings → Menu Button**  
URL: `https://nadirkarimov.github.io/Mini_Stadion/` (oxirida `/` bo‘lsin)

---

## 2) Botni sozlash

`.env` (`.env.example` dan nusxa):

```
BOT_TOKEN=123456:AA....
ADMIN_IDS=123456789
WEBAPP_URL=https://nadirkarimov.github.io/Mini_Stadion/
GITHUB_REPO=NadirKarimov/Mini_Stadion
GITHUB_BRANCH=main
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

**GITHUB_TOKEN** — GitHub → Settings → Developer settings → Personal access tokens  
Huquq: `repo` (yoki fine-grained: Contents = Read and write).  
Tokenni hech qachon GitHubga commit qilmang.

`install.bat` → `start.bat`. Kompyuter yoniq turganda bot ishlaydi.

Telegramda `/start` — lokatsiya keladi, **🏟️ Bron qilish** Mini Appni ochadi.

---

## 3) Admin

`⚙️ Admin panel`:

1. 💰 Narx — `60 000`
2. 💳 Kartalar — Click, Payme, Uzcard
3. 📍 Stadion manzili
4. 🕐 Ish vaqti — `06:00-24:00`

---

## Ranglar va bron

| Rang | Ma'nosi |
|------|---------|
| Kulrang | O'tib ketgan kun/soat — bron qilib bo'lmaydi |
| Yashil | Soat to'liq bo'sh |
| Ko'k | Qisman band (masalan 20:00–20:30 band, 20:30–21:00 bo'sh) |
| Qizil | To'liq band (admin tasdiqlagan) |
| To'q sariq | To'lov tasdig'i kutilmoqda |

Vaqt: 1 soat = `21:00/21:59`, 1.5 soat = `20:00/21:29`.

To‘lov: Mini App → bot karta raqamini yuboradi → skrinshot → admin tasdiqlaydi.

---

## Muhim

Bron qilishni **pastdagi klaviatura**dagi **🏟️ Bron qilish** tugmasidan oching. Shundagina bron botga yetadi.

Agar Mini App ochilib, vaqtlar yangilanmasa: repo publicmi, `GITHUB_TOKEN` to‘g‘rimi, bot ishlayaptimi — tekshiring.

# 🏠 EvTap — Bakı Daşınmaz Əmlak Axtarışı

Bakıda mənzil, ev, villa, ofis kirayə və satış elanlarını avtomatik toplayan veb-dəşbord.
**20 saytdan** elanları hər 5 dəqiqədən bir yığır və göstərir.

---

## 📡 Mənbələr (20 sayt)

| #   | Sayt                                     | Növ            | Parsinq        |
| --- | ---------------------------------------- | -------------- | -------------- |
| 1   | [Bina.az](https://bina.az)               | Kirayə + Satış | requests + BS4 |
| 2   | [Tap.az](https://tap.az)                 | Kirayə + Satış | requests + BS4 |
| 3   | [Lalafo.az](https://lalafo.az)           | Kirayə + Satış | requests + BS4 |
| 4   | [Arenda.az](https://arenda.az)           | Kirayə         | requests + BS4 |
| 5   | [Emlak.az](https://emlak.az)             | Kirayə + Satış | requests + BS4 |
| 6   | [Ev10.az](https://ev10.az)               | Kirayə + Satış | requests + BS4 |
| 7   | [Houses.az](https://houses.az)           | Kirayə + Satış | requests + BS4 |
| 8   | [EmlakBazarı.az](https://emlakbazari.az) | Kirayə + Satış | requests + BS4 |
| 9   | [Tikili.az](https://tikili.az)           | Kirayə + Satış | requests + BS4 |
| 10  | [Kub.az](https://kub.az)                 | Kirayə + Satış | requests + BS4 |
| 11  | [YeniEmlak.az](https://yeniemlak.az)     | Kirayə + Satış | requests + BS4 |
| 12  | [Binalar.az](https://binalar.az)         | Kirayə + Satış | requests + BS4 |
| 13  | [Villa.az](https://villa.az)             | Kirayə + Satış | requests + BS4 |
| 14  | [VipEmlak.az](https://vipemlak.az)       | Kirayə + Satış | requests + BS4 |
| 15  | [RahatEmlak.az](https://rahatemlak.az)   | Kirayə + Satış | requests + BS4 |
| 16  | [BinaTap.az](https://binatap.az)         | Kirayə + Satış | requests + BS4 |
| 17  | [YekEmlak.az](https://yekemlak.az)       | Kirayə + Satış | requests + BS4 |
| 18  | [RNS.az](https://rns.az)                 | Kirayə + Satış | requests + BS4 |
| 19  | [Etagi.com](https://baku.etagi.com)      | Kirayə + Satış | requests + BS4 |
| 20  | [Emlak.gov.az](https://emlak.gov.az)     | Kirayə + Satış | requests + BS4 |

---

## ✨ Xüsusiyyətlər

- 🔄 **Avtomatik yenilənmə** — Hər 5 dəqiqədən bir 20 mənbə yoxlanılır
- 🏠 **Əmlak növü filterləri** — Mənzil, Ev/Villa, Ofis, Torpaq, Kommersiya
- 💰 **Sövdələşmə tipi** — Kirayə / Satış
- 🛏 **Otaq filterləri** — 1, 2, 3, 4+
- 🕐 **Canlı saat** — Bakı vaxtı
- 🌤 **Hava widgeti** — OpenWeather API ilə Bakı havası
- 📻 **Radio widgeti** — AzerbaiJazz Radio
- 📱 **Responsiv dizayn** — Mobil və masaüstü

---

## 🚀 GitHub-a Yükləmə (Addım-addım)

### 1. Repo yaradın

[github.com/new](https://github.com/new) → **Public** → **Create**

### 2. Kodu yükləyin

```bash
cd baku-realty
git init
git add .
git commit -m "🏠 EvTap — 20 mənbə"
git branch -M main
git remote add origin https://github.com/SIZIN_USERNAME/baku-realty.git
git push -u origin main
```

### 3. GitHub Pages aktivləşdirin

**Settings** → **Pages** → **Source: GitHub Actions** → **Save**

### 4. Actions aktivləşdirin

**Actions** tab → Enable → **🔄 Elanları Parserləmək** → **Run workflow**

### 5. Saytı yoxlayın

`https://SIZIN_USERNAME.github.io/baku-realty/`

---

## 💻 Lokal Test

```bash
pip install -r requirements.txt
python server.py
# http://localhost:5000
```

Yalnız JSON yaratmaq:

```bash
python scrape.py
```

---

## 📁 Struktur

```
baku-realty/
├── .github/workflows/
│   ├── scrape.yml         ← Hər 5 dəq parserlər
│   └── pages.yml          ← GitHub Pages deploy
├── data/listings.json     ← Elanlar (avtomatik)
├── parsers/
│   ├── base.py            ← Ümumi utilitlər
│   ├── bina.py ... emlak_gov.py  ← 20 parser
│   └── __init__.py
├── static/index.html      ← Frontend (Azərbaycanca)
├── scrape.py              ← Pipeline
├── server.py              ← Lokal server
└── requirements.txt
```

---

## ⚠️ Qeydlər

- GitHub Actions pulsuz plan: ayda 2000 dəqiqə limit
- Bəzi saytlar vaxtaşırı HTML strukturunu dəyişə bilər
- `time.sleep()` gecikmələri ilə serverləri yükləmirik

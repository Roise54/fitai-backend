import base64
import json
from openai import OpenAI
from core.config import settings

client = OpenAI(api_key=settings.openai_api_key, timeout=30.0)

_GOAL_LABELS = {
    "lose_fat": "yağ yakmak",
    "build_muscle": "kas kazanmak",
    "recomp": "vücut dönüşümü sağlamak",
}


def _b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _img(image_bytes: bytes) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_b64(image_bytes)}"}}


def analyze_body(current_image: bytes, target_image: bytes, profile: dict) -> dict:
    name = profile.get("first_name", "")
    name_line = f"- İsim: {name}\n" if name else ""
    goal_text = _GOAL_LABELS.get(profile["goal"], profile["goal"])

    prompt = (
        f"Sen bir fitness koçusun. Kullanıcı profili:\n"
        f"{name_line}"
        f"- Yaş: {profile['age']}, Boy: {profile['height_cm']}cm, Kilo: {profile['weight_kg']}kg\n"
        f"- Hedef: {goal_text}\n\n"
        "İlk fotoğraf mevcut vücut, ikinci fotoğraf hedef vücut.\n\n"
        'Şu formatta yanıt ver (JSON):\n'
        '{"fat_percentage":"tahmini yağ oranı","muscle_level":"düşük/orta/yüksek",'
        '"fitness_level":"başlangıç/orta/ileri","kg_to_goal":8.5,"estimated_months":4,'
        '"first_actions":["aksiyon 1","aksiyon 2","aksiyon 3"]}\n\n'
        "Net ve kısa ol. Kalori sayma. Aksiyon odaklı."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                _img(current_image),
                _img(target_image),
            ],
        }],
        response_format={"type": "json_object"},
        max_tokens=500,
    )
    return json.loads(response.choices[0].message.content)


def analyze_food(food_image: bytes, goal: str, first_name: str = "") -> dict:
    name = first_name or "Arkadaşım"
    goal_text = _GOAL_LABELS.get(goal, goal)

    system_prompt = (
        "Sen sıcak, destekleyici bir beslenme koçusun. "
        "Sadece yemek ve beslenme konularında yardım edersin. "
        "Yanıtlarını JSON formatında ver."
    )
    user_prompt = (
        f"Kullanıcı adı: {name}, hedefi: {goal_text}.\n"
        "Bu yemek fotoğrafını analiz et ve aşağıdaki JSON formatında yanıt ver:\n"
        f'{{"analysis":"{name} diye hitap ederek yemeği tanıt ve hedefine etkisini açıkla",'
        '"decision":"ye/azalt/değiştir/kaçın",'
        '"impact":"düşük/orta/yüksek",'
        f'"alternative":"{name}\'a daha iyi bir alternatif öner"}}\n'
        "Ton: sıcak, anlayışlı, motive edici. Kalori sayma."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_prompt},
                _img(food_image),
            ]},
        ],
        response_format={"type": "json_object"},
        max_tokens=400,
    )
    return json.loads(response.choices[0].message.content)


def generate_daily_quote(goal: str, first_name: str = "") -> str:
    goal_text = _GOAL_LABELS.get(goal, goal)
    name_part = f"{first_name}," if first_name else ""

    system_prompt = "Sen motive edici bir fitness koçusun. Kısa ve güçlü Türkçe motivasyon cümleleri yazarsın."
    user_prompt = (
        f"{name_part} {goal_text} hedefine sahip biri için "
        "bugüne özel, kişisel ve güçlü bir motivasyon cümlesi yaz. "
        "Maksimum 2 cümle. Özgün ol, klişe sözlerden kaçın. "
        "Sadece cümleyi yaz, başka bir şey ekleme."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()


def estimate_meal(meal_name: str, goal: str, first_name: str = "") -> dict:
    name = first_name or "Arkadaşım"
    goal_text = _GOAL_LABELS.get(goal, goal)

    prompt = (
        f"Kullanıcı: {name}, hedef: {goal_text}.\n"
        f"Yemek/içecek: {meal_name}\n\n"
        "Bu yemeğin tahmini besin değerlerini JSON formatında ver:\n"
        '{"calories":320,"protein":12,"carbs":58,"fat":6,"note":"kısa değerlendirme"}\n\n'
        "Kalori ve makrolar için gerçekçi ortalama porsiyon değerlerini kullan. "
        "Not alanında hedefe göre 1 cümlelik yorum yap."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=150,
    )
    return json.loads(response.choices[0].message.content)


def comment_body_progress(image_bytes: bytes, goal: str, first_name: str = "", week_number: int = 1) -> str:
    name = first_name or "Arkadaşım"
    goal_text = _GOAL_LABELS.get(goal, goal)

    system_prompt = "Sen destekleyici ve sıcak bir fitness koçusun. Kullanıcının ilerleme fotoğraflarına kısa ve motive edici yorumlar yaparsın."
    user_prompt = (
        f"{name}'ın {week_number}. hafta ilerleme fotoğrafı. Hedef: {goal_text}.\n"
        f"Bu fotoğrafa bakarak {name}'a kısa, samimi ve motive edici bir yorum yap. "
        "Olumlu noktaları vurgula, nazikçe bir sonraki adımı hatırlat. "
        "Maksimum 3 cümle."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_prompt},
                _img(image_bytes),
            ]},
        ],
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


def food_chat_text(question: str, photo_bytes: bytes | None = None) -> str:
    # Kullanıcı sorusu system prompt'a değil user mesajına gidiyor (prompt injection önlemi)
    system_prompt = (
        "Sen bir beslenme uzmanısın. SADECE yemek, beslenme ve diyet konularındaki soruları yanıtla. "
        "Konu dışı sorulara 'Sadece beslenme konularında yardımcı olabilirim' de. "
        "Net, kısa ve aksiyon odaklı cevap ver. Türkçe yanıt ver."
    )

    content: list = [{"type": "text", "text": question}]
    if photo_bytes:
        content.append(_img(photo_bytes))

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        max_tokens=400,
    )
    return response.choices[0].message.content


def calculate_score(
    food_decisions: list,
    workout_done: bool,
    goal: str,
    first_name: str = "",
    diet_done: bool = False,
    water_glasses: int = 0,
) -> dict:
    goal_text = _GOAL_LABELS.get(goal, goal)
    name_part = f"{first_name}," if first_name else "kullanıcı,"

    # Deterministik skor hesabı
    workout_pts = 40 if workout_done else 0
    diet_pts = 35 if diet_done else 0
    water_pts = round(min(water_glasses / 8.0, 1.0) * 25)
    score = workout_pts + diet_pts + water_pts  # 0-100

    system_prompt = (
        "Sen bir fitness koçusun. Kullanıcının günlük verileri sana verilecek. "
        "JSON formatında kısa, motive edici geri bildirim yazarsın."
    )
    user_prompt = (
        f"Kullanıcı: {name_part} Hedef: {goal_text}\n"
        f"Günlük skor: {score}/100\n"
        f"  - Antrenman ({workout_pts}/40): {'✓' if workout_done else '✗'}\n"
        f"  - Diyet uyumu ({diet_pts}/35): {'✓' if diet_done else '✗'}\n"
        f"  - Su tüketimi ({water_pts}/25): {water_glasses} bardak\n"
        f"  - Yemek kararları: {food_decisions if food_decisions else 'yok'}\n\n"
        f"Bu skora ({score}/100) göre 2-3 cümle samimi ve motive edici feedback yaz, yarın için 1 net öneri ver.\n"
        "Şu formatta yanıt ver (JSON, score alanını değiştirme):\n"
        f'{{"score":{score},"feedback":"2-3 cümle","top_recommendation":"yarın için 1 öneri"}}'
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=220,
    )
    result = json.loads(response.choices[0].message.content)
    result["score"] = score  # AI'ın skoru değiştirmesini engelle
    return result


_LOCATION_RULES = {
    "home": (
        "Egzersiz yeri: EV (ekipman yok).\n"
        "KURAL: Yalnızca vücut ağırlığıyla yapılabilen egzersizler kullan "
        "(şınav, squat, plank, burpee, lunges, mountain climber, jumping jack, "
        "dip (sandalye), glute bridge, superman vb.). "
        "Hiçbir ağırlık aleti veya spor salonu ekipmanı ekleme."
    ),
    "gym": "Egzersiz yeri: Spor salonu (tüm ekipmanlar ve ağırlıklar mevcut).",
}


_LEVEL_RULES = {
    "başlangıç": (
        "SEVİYE: Başlangıç.\n"
        "- Temel compound hareketlere odaklan (squat, deadlift, bench press, row, overhead press).\n"
        "- Her kas grubu için 2 egzersiz yeterli. Teknik öğrenme öncelikli.\n"
        "- Set/rep: 3x10-12, dinlenme 60-90 sn.\n"
        "- Ağırlık seçimi: tekniği bozmadan tamamlanabilecek, son 2 tekrarda zorlanılan ağırlık.\n"
        "- Tempo orta, derin nefes tekniği vurgula.\n"
        "- 'Son sete kadar git' veya 'drop set' gibi ileri teknikler kullanma."
    ),
    "orta": (
        "SEVİYE: Orta (6+ ay deneyim).\n"
        "- Her kas grubu için 3 egzersiz uygula: 1 compound (ağır/düşük tekrar) + 1 compound (orta) + 1 izolasyon.\n"
        "- Set/rep: compound için 4x6-8, izolasyon için 3x12-15.\n"
        "- Son sette tükenişe git (RIR 0-1).\n"
        "- Progresif yük artışı vurgula: her haftada 2.5-5 kg artış hedefle.\n"
        "- Süperset ve piramit set tekniklerini kullanabilirsin.\n"
        "- Dinlenme: ağır compound 2-3 dk, izolasyon 60-90 sn."
    ),
    "ileri": (
        "SEVİYE: İleri (2+ yıl deneyim, kas-sinir koordinasyonu gelişmiş).\n"
        "- Her kas grubu için 3-4 egzersiz. Compound + compound + izolasyon + bitirici izolasyon.\n"
        "- Yoğun teknikler zorunlu: son set tükenişe git, drop set, süperset, negatif tekrar, rest-pause.\n"
        "- Set/rep: compound 5x4-6 (ağır), aksesuar 4x8-10, izolasyon 3x12-15 tükenişe.\n"
        "- Periodizasyon: bazı günler güç odaklı (5x5), bazı günler hipertrofi (4x8-12).\n"
        "- Dinlenme: compound 3-4 dk, aksesuar 90 sn-2 dk, izolasyon 45-60 sn.\n"
        "- RPE 8-10 hedef. Antrenman süresi 75-90 dk."
    ),
}

def generate_workout_plan(profile: dict) -> dict:
    goal_text = _GOAL_LABELS.get(profile["goal"], profile["goal"])
    name = profile.get("first_name", "")
    name_line = f"- İsim: {name}\n" if name else ""
    fitness_level = profile.get("fitness_level", "başlangıç")
    days_per_week = profile.get("days_per_week", 3)
    location = profile.get("workout_location", "gym")
    location_rule = _LOCATION_RULES.get(location, _LOCATION_RULES["gym"])
    level_rule = _LEVEL_RULES.get(fitness_level, _LEVEL_RULES["başlangıç"])

    system_prompt = (
        "Sen 10 yıllık deneyime sahip sertifikalı bir kişisel antrenörsün (NASM-CPT). "
        "Bilimsel temelli, gerçekten sonuç veren antrenman programları yazarsın. "
        "Jenerik programlar değil, kişiye özel, uygulanabilir ve zorlayıcı programlar üretirsin. "
        "PT jargonunu doğal kullanırsın: RPE, RIR, drop set, süperset, progressive overload. "
        "JSON formatında yanıt verirsin."
    )
    user_prompt = (
        f"Kullanıcı profili:\n{name_line}"
        f"- Yaş: {profile['age']}, Boy: {profile['height_cm']}cm, Kilo: {profile['weight_kg']}kg\n"
        f"- Cinsiyet: {profile['gender']}, Hedef: {goal_text}\n"
        f"- {level_rule}\n"
        f"- Haftada {days_per_week} antrenman günü (geri kalan günler dinlenme)\n"
        f"- {location_rule}\n\n"
        "Bu profile uygun 7 günlük antrenman programı oluştur. "
        "Antrenman günlerini haftaya dengeli yay. Aynı kas grubunu arka arkaya koyma.\n\n"
        "JSON formatında yanıt ver:\n"
        '{"days":['
        '{"day":"Pazartesi","is_rest":false,"focus":"Göğüs & Triceps",'
        '"duration":"60-75 dk","intensity":"yüksek",'
        '"warmup":"5 dk hafif ip atlama + 10 tekrar boş bar bench press",'
        '"exercises":['
        '{"name":"Bench Press","sets":"4","reps":"6-8 — son set tükenişe git","rest":"2-3 dk",'
        '"tip":"Kürek kemiklerini birbirine yaklaştır, sırtında kavis oluştur. Barı göğüs ortasına indir.",'
        '"how_to":"Bankta sırt üstü uzan, kürek kemiklerini sık ve hafif kavis oluştur. Barı omuz genişliğinden biraz geniş tut. Nefes alarak barı kontrollü göğüs ortasına indir (2 sn), nefes vererek patlayıcı şekilde it. Son sette ağırlığı düşürme — tükenişe git."}'
        '],'
        '"cooldown":"5 dk göğüs-triceps esneme + köpük rulo"},'
        '{"day":"Salı","is_rest":true,"focus":"Aktif Dinlenme","duration":"","intensity":"",'
        '"warmup":"","exercises":[],"cooldown":""}'
        ']}\n\n'
        "Kurallar:\n"
        f"- Seviye kurallarına SIKI uy: {fitness_level} için belirtilen egzersiz sayısı, set/rep ve teknikler zorunlu\n"
        "- Hedef: kas hipertrofisi için ağırlık+izolasyon dengesi, yağ yakma için süper set ve kısa dinlenme tercih et\n"
        "- 'sets' ve 'reps' alanlarında detaylı not ekle: '4x8-10 — son set drop set' gibi\n"
        "- 'tip' alanı kısa ama kritik teknik noktayı vurgulasın (1-2 cümle)\n"
        "- 'how_to' alanına tam teknik açıklama yaz: nefes, kas aktivasyonu, hata önleme (3-4 cümle)\n"
        "- Warmup ve cooldown spesifik ve antrenmanla ilgili olsun\n"
        "- Türkçe yaz, PT terminolojisini (drop set, süperset, RPE, progressive overload vb.) doğal kullan"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
        timeout=60.0,
    )
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Antrenman planı JSON parse hatası: {e}")


_DIET_GOAL_RULES = {
    "lose_fat": (
        "HEDEF: Yağ yakma. "
        "Yüksek protein (her öğünde), düşük rafine karbonhidrat, bol lif, az işlenmiş gıda. "
        "Kahvaltıda yumurta/peynir/yoğurt ağırlıklı. Akşam yemeklerinde karbonhidratı azalt, sebze ve protein öne çıkar. "
        "Ara öğünlerde meyve, kuruyemiş veya süt ürünleri."
    ),
    "build_muscle": (
        "HEDEF: Kas kazanma. "
        "Çok yüksek protein (her öğünde et/tavuk/balık/yumurta/kurubaklagil), kompleks karbonhidrat (bulgur/yulaf/tam tahıl ekmek/patates), sağlıklı yağlar. "
        "Antrenman sonrası öğün: hızlı protein + karbonhidrat (yoğurt+muz veya tavuk+pirinç). "
        "Hacimli, doyurucu porsiyonlar."
    ),
    "recomp": (
        "HEDEF: Yağ yakıp kas kazanma. "
        "Dengeli makro: yüksek protein, orta karbonhidrat (kompleks), orta yağ. "
        "Öğün zamanlaması önemli: antrenman öncesi karbonhidrat, sonrası protein. "
        "İşlenmiş gıdalardan kaçın, Türk mutfağının sağlıklı seçeneklerini tercih et."
    ),
}


def generate_diet_plan(profile: dict) -> dict:
    goal_text = _GOAL_LABELS.get(profile["goal"], profile["goal"])
    goal_rules = _DIET_GOAL_RULES.get(profile["goal"], "")
    name = profile.get("first_name", "")
    name_line = f"- İsim: {name}\n" if name else ""
    gender = profile.get("gender", "")
    age = profile.get("age", 25)
    weight = profile.get("weight_kg", 75)
    height = profile.get("height_cm", 175)

    system_prompt = (
        "Sen deneyimli bir diyetisyen ve beslenme uzmanısın. "
        "Bilimsel temelli, detaylı, kişiye özel 7 günlük diyet planları hazırlarsın. "
        "Öğünler gerçekçi, pişirmesi kolay ve Türk damak zevkine uygundur. "
        "JSON formatında yanıt verirsin."
    )
    user_prompt = (
        f"Kullanıcı profili:\n{name_line}"
        f"- Yaş: {age}, Boy: {height}cm, Kilo: {weight}kg, Cinsiyet: {gender}\n"
        f"- Hedef: {goal_text}\n"
        f"- {goal_rules}\n\n"
        "Yukarıdaki profile göre 7 günlük kişiselleştirilmiş diyet planı oluştur.\n\n"
        "Her öğün için şunları yaz:\n"
        "- Spesifik yiyecek adları ve miktarları (ör: '2 yumurta haşlama, 2 dilim tam tahıllı ekmek, 1 dilim beyaz peynir (40g), domates-salatalık')\n"
        "- Hazırlanması basit, Türkiye'de kolayca bulunabilen malzemeler\n"
        "- 7 gün boyunca çeşitlilik olsun, aynı öğünleri tekrar etme\n"
        "- Tip alanına o gün için beslenmeye özgü pratik bir öneri yaz\n\n"
        'JSON formatında yanıt ver:\n'
        '{"days":['
        '{"day":"Pazartesi",'
        '"breakfast":"2 haşlama yumurta, 2 dilim tam tahıllı ekmek, 40g beyaz peynir, söğüş domates-salatalık, yeşil çay",'
        '"lunch":"Izgara tavuk göğsü (150g), bulgur pilavı (1 kase), mevsim salatası (zeytinyağlı-limonlu), cacık",'
        '"dinner":"Fırın somon (150g), zeytinyağlı brokoli-havuç, 1 kase mercimek çorbası",'
        '"snack":"1 avuç badem (20g) + 1 elma",'
        '"tip":"Öğleden sonra acıkırsan önce 1 büyük bardak su iç, 10 dakika bekle."}'
        "]}\n\n"
        "Kurallar:\n"
        "- Kalori sayısı yazma, sadece yiyecek/miktar\n"
        "- Her gün farklı protein kaynağı kullan (tavuk, kırmızı et, balık, yumurta, baklagil dönüşümlü)\n"
        "- Türk mutfağının zenginliğini yansıt: çorba, zeytinyağlılar, ızgara, dolma, köfte vb.\n"
        "- Miktar bilgisi ekle (gram, adet, kase, dilim)\n"
        "- Türkçe yaz"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )
    return json.loads(response.choices[0].message.content)

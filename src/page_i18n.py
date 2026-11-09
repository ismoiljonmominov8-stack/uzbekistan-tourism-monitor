"""All texts of the web page in Uzbek, Russian and English: key -> (uz, ru, en).
{name} = value filled in by the page. Keys ending in _html may contain <b>, <ul>, <a>."""

STRINGS = {
    # ---------------------------------------------------------------- header, summary, how it works
    "tagline": ("Turistlarni raqamli kuzatish, prognoz va jalb etish tizimi",
                "Цифровая система мониторинга, прогноза и привлечения туристов",
                "A digital system to monitor, forecast and attract tourists"),
    "meta": ("Ma'lumot: {first} — {last} · {n} kun · yangilangan {upd}",
             "Данные: {first} — {last} · {n} дней · обновлено {upd}",
             "Data: {first} — {last} · {n} days · updated {upd}"),
    "hero_lead": ("Bu tizim har kuni ochiq manbalardan ma'lumot yig'ib, <b>O'zbekistonga qancha xorijiy turist kelishini</b>, "
                  "<b>ular nima maqsadda kelishini</b> va <b>qaysi davlatlardan ko'proq jalb qilish mumkinligini</b> ko'rsatadi. "
                  "Hammasi bepul ishlaydi va o'z-o'zidan yangilanadi.",
                  "Система ежедневно собирает данные из открытых источников и показывает, <b>сколько иностранных туристов приезжает в Узбекистан</b>, "
                  "<b>с какой целью они приезжают</b> и <b>из каких стран можно привлечь больше</b>. Всё работает бесплатно и обновляется автоматически.",
                  "Every day this system collects open data and shows <b>how many foreign visitors come to Uzbekistan</b>, "
                  "<b>why they come</b> and <b>which countries could send more</b>. It runs free of charge and updates itself."),
    "kpi_fc": ("{y} yil prognozi, xorijiy safarlar", "Прогноз на {y} год, иностранные поездки", "{y} forecast, foreign visits"),
    "kpi_fc_s": ("oraliq {lo} – {hi}", "диапазон {lo} – {hi}", "range {lo} – {hi}"),
    "kpi_ytd": ("{y}: yanvar–{m} (rasmiy)", "{y}: январь–{m} (официально)", "{y}: January–{m} (official)"),
    "kpi_ytd_s": ("Milliy statistika qo'mitasi", "Национальный комитет по статистике", "National Statistics Committee"),
    "kpi_leis": ("dam olish uchun kelganlar ulushi, {y}", "доля приехавших на отдых, {y}", "share who came for leisure, {y}"),
    "kpi_leis_s": ("{v} safar; qarindoshlarni ko'rish — {r}", "{v} поездок; к родственникам — {r}", "{v} visits; visiting relatives — {r}"),
    "kpi_acc": ("oylik prognozning o'rtacha xatosi", "средняя ошибка месячного прогноза", "average error of the monthly forecast"),
    "kpi_acc_s": ("1 oy oldin, o'tmish sinovi ({n} holat)", "на 1 месяц вперёд, проверка на истории ({n} случаев)", "1 month ahead, tested on past data ({n} cases)"),
    "mln": ("mln", "млн", "M"),
    "how_title": ("Tizim qanday ishlaydi", "Как работает система", "How the system works"),
    "step1_t": ("Yig'ish", "Сбор", "Collect"),
    "step1_p": ("Har kuni: Vikipediya ko'rishlari (15 til = 15 bozor). Har oy: rasmiy turistlar soni. Har hafta: Google qidiruvlari, yangiliklar.",
                "Ежедневно: просмотры Википедии (15 языков = 15 рынков). Ежемесячно: официальное число туристов. Еженедельно: поиск Google, новости.",
                "Daily: Wikipedia views (15 languages = 15 markets). Monthly: official visitor numbers. Weekly: Google searches, news."),
    "step2_t": ("Tahlil", "Анализ", "Analyse"),
    "step2_p": ("Keyingi 3 oy prognozi va uning xatosi, safar maqsadi bo'yicha ajratish, voqealar (viza, reys, tadbir) ta'sirini o'lchash.",
                "Прогноз на 3 месяца и его ошибка, разделение по цели поездки, измерение влияния событий (визы, рейсы, мероприятия).",
                "A 3-month forecast with its measured error, a split by purpose of visit, and the measured effect of events (visas, flights, festivals)."),
    "step3_t": ("Tavsiya", "Рекомендация", "Recommend"),
    "step3_p": ("Har bir bozor uchun: qancha imkoniyat bor, qanday xabar va qaysi kanal orqali yetkazish kerak.",
                "Для каждого рынка: каков потенциал, какое сообщение и через какой канал его донести.",
                "For each market: how much headroom there is, what message to send and through which channel."),
    "step4_t": ("Yetkazish", "Доставка", "Deliver"),
    "step4_p": ("Telegram kanal (har kuni), Word hisobot (har dushanba), shu sahifa. Yangiliklar e'lon qilinishidan oldin tasdiqlanadi.",
                "Telegram-канал (ежедневно), отчёт Word (каждый понедельник), эта страница. Новости публикуются после одобрения.",
                "A Telegram channel (daily), a Word report (every Monday) and this page. News is published only after approval."),
    "toc1": ("1 · Qancha keladi", "1 · Сколько приезжает", "1 · How many"),
    "toc2": ("2 · Nima uchun", "2 · Зачем", "2 · Why"),
    "toc3": ("3 · Qayerdan jalb qilish", "3 · Откуда привлекать", "3 · Where to attract"),
    "toc4": ("4 · Qiziqish", "4 · Интерес", "4 · Interest"),
    "toc5": ("5 · Voqealar", "5 · События", "5 · Events"),
    "toc6": ("6 · Usul va manbalar", "6 · Метод и источники", "6 · Methods"),
    # ---------------------------------------------------------------- chapters
    "ch1_t": ("Qancha turist keladi va qancha keladi", "Сколько туристов приезжает и сколько приедет", "How many visitors come — and how many will come"),
    "ch1_p": ("Rasmiy statistika va keyingi oylar prognozi. Prognoz xatosi taxmin qilinmaydi — o'lchanadi.",
              "Официальная статистика и прогноз на ближайшие месяцы. Ошибка прогноза не предполагается, а измеряется.",
              "Official statistics and a forecast for the next months. The forecast error is measured, not assumed."),
    "ch2_t": ("Ular nima uchun keladi", "Зачем они приезжают", "Why they come"),
    "ch2_p": ("Rasmiy «turist» — chegaradan o'tgan har bir xorijlik. Ko'pchiligi qarindoshlarini ko'rishga keladi; jalb etish siyosati esa asosan dam olish uchun keluvchilarga ta'sir qiladi.",
              "Официальный «турист» — любой иностранец, пересёкший границу. Большинство едет к родственникам, а политика привлечения влияет в основном на тех, кто едет отдыхать.",
              "An official “tourist” is any foreigner who crosses the border. Most come to visit relatives, while promotion mainly works on people who travel for leisure."),
    "ch3_t": ("Qaysi bozorlardan jalb qilish kerak", "С каких рынков привлекать", "Where to attract them from"),
    "ch3_p": ("Kim safarga qodir, kim kam keladi va O'zbekiston raqiblar orasida qanchalik tanilgan — shularga qarab har bir bozor uchun tavsiya.",
              "Кто может позволить себе поездку, кто приезжает мало и насколько Узбекистан известен среди конкурентов — на этом основана рекомендация для каждого рынка.",
              "Who can afford the trip, who visits too little and how well known Uzbekistan is against its rivals — combined into a recommendation per market."),
    "ch4_t": ("Kim hozir qiziqmoqda", "Кто интересуется сейчас", "Who is interested right now"),
    "ch4_p": ("Vikipediya ko'rishlari — har kuni yangilanadigan yagona signal. Bu qiziqish, sayohat emas: bashorat kuchi past, lekin voqealar ta'sirini ko'rsatadi.",
              "Просмотры Википедии — единственный ежедневный сигнал. Это интерес, а не поездки: прогнозная сила слабая, но он показывает реакцию на события.",
              "Wikipedia views are the only signal that updates daily. They show interest, not travel: weak as a predictor, but they reveal reactions to events."),
    "ch5_t": ("Oqimni nima o'zgartiradi: voqealar", "Что меняет поток: события", "What changes the flow: events"),
    "ch5_p": ("Viza, chegara, reys, yirik tadbir. Har bir voqeaning ta'siri o'tgach o'lchanadi va kelajakdagi o'xshash voqealarni baholashga xizmat qiladi.",
              "Визы, границы, рейсы, крупные мероприятия. Влияние каждого события измеряется после него и помогает оценивать похожие события в будущем.",
              "Visas, borders, flights, major events. Each event's effect is measured afterwards and used to estimate similar future events."),
    "ch6_t": ("Ma'lumot, usul va cheklovlar", "Данные, метод и ограничения", "Data, methods and limits"),
    "ch6_p": ("Har bir raqam qayerdan olingani va nimani bilmasligimiz.", "Откуда взята каждая цифра и чего мы не знаем.",
              "Where every number comes from — and what we do not know."),
    "howto": ("Qanday o'qish kerak", "Как читать", "How to read this"),
    # ---------------------------------------------------------------- chapter 1
    "overall_t": ("Jami xorijiy turistlar, 2018 – 2026", "Всего иностранных туристов, 2018 – 2026", "Total foreign visitors, 2018 – 2026"),
    "overall_what": ("Qora — rasmiy raqamlar, oltin rang — prognoz va uning oralig'i.", "Чёрное — официальные данные, золотое — прогноз и его диапазон.",
                     "Solid line — official figures; gold — the forecast and its range."),
    "g_day": ("Kun", "День", "Day"), "g_week": ("Hafta", "Неделя", "Week"), "g_month": ("Oy", "Месяц", "Month"), "g_year": ("Yil", "Год", "Year"),
    "overall_note": ("Rasmiy statistika faqat <b>oylik</b> (2022-yil avgustidan, ba'zi oylar yo'q) va <b>yillik</b> chiqadi; kunlik yoki haftalik rasmiy raqam yo'q. "
                     "«Kun» va «Hafta» — o'rtacha qiymat (oy ÷ kunlar, ×7). Kulrang uzuq chiziq — oylik ma'lumot yo'q davr. Ochiq nuqta — manbada yaxlitlangan yoki ikki oy birga e'lon qilingan raqam.",
                     "Официальная статистика выходит только <b>ежемесячно</b> (с августа 2022 г., некоторых месяцев нет) и <b>ежегодно</b>; дневных и недельных данных нет. "
                     "«День» и «Неделя» — средние значения (месяц ÷ дни, ×7). Серая пунктирная линия — период без месячных данных. Пустая точка — округлённая цифра или два месяца, опубликованные вместе.",
                     "Official statistics are published only <b>monthly</b> (from August 2022, some months missing) and <b>yearly</b>; there are no official daily or weekly figures. "
                     "“Day” and “Week” are averages (month ÷ days, ×7). The grey dashed line marks periods without monthly data. Open dots are figures rounded at the source or two months published together."),
    "og_day": ("turist / kun (o'rtacha)", "туристов / день (среднее)", "visitors / day (average)"),
    "og_week": ("turist / hafta (o'rtacha)", "туристов / неделю (среднее)", "visitors / week (average)"),
    "og_month": ("turist / oy", "туристов / месяц", "visitors / month"),
    "og_year": ("turist / yil", "туристов / год", "visitors / year"),
    "o_official_y": ("Rasmiy (yillik)", "Официально (год)", "Official (yearly)"),
    "o_actual_m": ("{y}: {m} oy haqiqiy", "{y}: {m} мес. факт", "{y}: {m} months actual"),
    "o_fc_rest": ("{y}: prognoz (qolgan oylar)", "{y}: прогноз (остальные месяцы)", "{y}: forecast (remaining months)"),
    "o_year12": ("Yillik jami ÷ 12 (oylik ma'lumot yo'q)", "Год ÷ 12 (нет месячных данных)", "Yearly total ÷ 12 (no monthly data)"),
    "o_avg_months": ("Bir necha oy o'rtachasi", "Среднее за несколько месяцев", "Average over several months"),
    "o_official_m": ("Rasmiy (oylik)", "Официально (месяц)", "Official (monthly)"),
    "o_span": ("ikki oy birga e'lon qilingan", "два месяца опубликованы вместе", "two months published together"),
    "o_exact": ("aniq", "точно", "exact"), "o_rounded": ("yaxlitlangan (≈)", "округлено (≈)", "rounded (≈)"),
    "o_range": ("Prognoz oralig'i", "Диапазон прогноза", "Forecast range"), "o_fc": ("Prognoz", "Прогноз", "Forecast"),
    "o_method": ("<b>{y} yil prognozi: ≈ {v} turist</b> (oraliq {lo} – {hi}); {m} oyda haqiqatda {ytd} kelgan. "
                 "<b>Usul:</b> qolgan har bir oy = o'tgan yilning shu oyi × g; g — oxirgi 3 oy o'sishi ({raw}) ning 75 foizi = {g}. Oraliq — usulning o'tgan xatolaridan.",
                 "<b>Прогноз на {y} год: ≈ {v} туристов</b> (диапазон {lo} – {hi}); за {m} мес. фактически {ytd}. "
                 "<b>Метод:</b> каждый оставшийся месяц = тот же месяц прошлого года × g; g — 75% роста последних 3 месяцев ({raw}) = {g}. Диапазон — по прошлым ошибкам метода.",
                 "<b>{y} forecast: ≈ {v} visitors</b> (range {lo} – {hi}); {ytd} actually arrived in the first {m} months. "
                 "<b>Method:</b> each remaining month = the same month last year × g, where g is 75% of the growth of the last 3 months ({raw}) = {g}. The range comes from the method's past errors."),
    "o_bt": ("<b>Usul tekshiruvi</b> (o'tgan yillar, {m} oylik ma'lumotdan): {list}.", "<b>Проверка метода</b> (прошлые годы, по данным за {m} мес.): {list}.",
             "<b>Test on past years</b> (from {m} months of data): {list}."),
    "o_bt_item": ("{y}: prognoz {f}, haqiqatda {a} ({e}%{o})", "{y}: прогноз {f}, факт {a} ({e}%{o})", "{y}: forecast {f}, actual {a} ({e}%{o})"),
    "o_outside": (", oraliqdan tashqarida", ", вне диапазона", ", outside the range"),
    "score_t": ("Prognoz aniqligi va keyingi 3 oy", "Точность прогноза и следующие 3 месяца", "Forecast accuracy and the next 3 months"),
    "score_what": ("Usul o'tmishdagi har bir oydan 1–3 oy oldinga sinab ko'rildi va haqiqat bilan solishtirildi.",
                   "Метод проверен от каждого прошлого месяца на 1–3 месяца вперёд и сравнён с фактом.",
                   "The method was run from every past month 1–3 months ahead and compared with what actually happened."),
    "acc_t": ("O'rtacha xato (o'tmish sinovi, 2023–2026)", "Средняя ошибка (проверка на истории, 2023–2026)", "Average error (tested on 2023–2026)"),
    "fc_t": ("Keyingi 3 oy prognozi", "Прогноз на 3 месяца", "Forecast for the next 3 months"),
    "score_note": ("Usul: kelasi oy = o'tgan yilning shu oyi × oxirgi 3 oy o'sishining 75 foizi. <b>O'tmish sinovi</b> — usul o'tgan har bir oydan ishlatilib, haqiqat bilan solishtirilgan. "
                   "<b>Jonli</b> prognozlar o'sha kuni saqlanadi va rasmiy raqam chiqqach baholanadi (2026 noyabrdan). Oraliq: haqiqiy raqam taxminan 10 tadan 8 holatda shu ichida bo'lishi kerak.",
                   "Метод: следующий месяц = тот же месяц прошлого года × 75% роста последних 3 месяцев. <b>Проверка на истории</b> — метод запускался от каждого прошлого месяца и сравнивался с фактом. "
                   "<b>Живые</b> прогнозы сохраняются в день создания и оцениваются после выхода официальных данных (с ноября 2026). Диапазон: фактическое значение должно попадать в него примерно в 8 случаях из 10.",
                   "Method: next month = the same month last year × 75% of the growth of the last 3 months. <b>Back-test</b>: the method was run from every past month and compared with the actual figure. "
                   "<b>Live</b> forecasts are saved on the day they are made and scored when the official figure comes out (from November 2026). Range: the actual value should fall inside it about 8 times in 10."),
    "c_market": ("Bozor", "Рынок", "Market"), "c_h1": ("1 oy oldin", "на 1 мес.", "1 month ahead"), "c_h2": ("2 oy", "2 мес.", "2 months"),
    "c_h3": ("3 oy", "3 мес.", "3 months"), "c_bias": ("Siljish", "Смещение", "Bias"), "c_last": ("Oxirgi rasmiy oy", "Последний офиц. месяц", "Latest official month"),
    "live_note": ("Qavsda — baholangan prognozlar soni (* — 8 tadan kam, ishonchsiz). Siljish: musbat = usul oshirib yuboradi. Jonli: {a} ta prognoz saqlangan, {b} tasi baholangan.",
                  "В скобках — число оценённых прогнозов (* — меньше 8, ненадёжно). Смещение: плюс = метод завышает. Живые: сохранено {a}, оценено {b}.",
                  "In brackets: number of scored forecasts (* = fewer than 8, unreliable). Bias: positive = the method over-forecasts. Live: {a} forecasts saved, {b} scored."),
    "not_enough": ("ma'lumot yetarli emas", "недостаточно данных", "not enough data"),
    "arr_t": ("Rasmiy statistika: oyma-oy kelganlar", "Официальная статистика по месяцам", "Official monthly arrivals"),
    "arr_what": ("Eng katta bozorlar va jami (o'ng o'q). Manba: Milliy statistika qo'mitasi.", "Крупнейшие рынки и итог (правая ось). Источник: Национальный комитет по статистике.",
                 "Largest markets and the total (right axis). Source: National Statistics Committee."),
    "arr_y1": ("turist / oy (davlatlar)", "туристов / месяц (страны)", "visitors / month (countries)"),
    "arr_y2": ("jami / oy", "всего / месяц", "total / month"),
    # ---------------------------------------------------------------- chapter 2
    "leis_t": ("Safar maqsadi va dam olish uchun kelganlar", "Цель поездки и приезжающие на отдых", "Purpose of visit and leisure visitors"),
    "leis_what": ("Chapda — rasmiy yillik maqsadlar; o'ngda — dam olish uchun kelganlar davlatlar bo'yicha (baho).",
                  "Слева — официальные цели по годам; справа — приезжающие на отдых по странам (оценка).",
                  "Left: official purposes by year. Right: leisure visitors by country (estimate)."),
    "purpose_years_t": ("Safar maqsadlari, yillar bo'yicha (rasmiy)", "Цели поездок по годам (официально)", "Purpose of visit by year (official)"),
    "leis_months_t": ("Dam olish uchun kelganlar, oyiga (baho)", "Приезжающие на отдых, в месяц (оценка)", "Leisure visitors per month (estimate)"),
    "p_leisure": ("Dam olish va sayohat", "Отдых и путешествия", "Leisure and travel"),
    "p_relatives": ("Qarindoshlarni ko'rish", "Посещение родственников", "Visiting relatives"),
    "p_business": ("Xizmat safari", "Деловые поездки", "Business"),
    "p_other": ("Davolanish, tijorat, o'qish", "Лечение, торговля, учёба", "Medical, trade, study"),
    "people_month": ("kishi / oy", "человек / месяц", "people / month"),
    "leis_table_t": ("Davlatlar bo'yicha: {y} yil {m} oy va keyingi 3 oy prognozi", "По странам: {y} год, {m} мес., и прогноз на 3 месяца",
                     "By country: {y}, {m} months, and a 3-month forecast"),
    "c_country": ("Davlat", "Страна", "Country"), "c_leis_share": ("Dam olish ulushi", "Доля отдыха", "Leisure share"),
    "c_arrivals": ("Kelganlar (jami)", "Приехало (всего)", "Arrivals (all)"), "c_of_leis": ("Shundan dam olish", "Из них на отдых", "Of which leisure"),
    "leis_note": ("Yillik maqsadlar — rasmiy (SIAT). Davlatlar bo'yicha oylik raqam e'lon qilinmaydi, shuning uchun <b>baholanadi</b>: davlatdan kelganlar × shu davlatning dam olish ulushi (stat.uz, 2025 yil yanvar–iyun).",
                  "Цели по годам — официальные (SIAT). Месячные данные по странам не публикуются, поэтому они <b>оцениваются</b>: приехавшие из страны × доля отдыха этой страны (stat.uz, январь–июнь 2025).",
                  "Yearly purposes are official (SIAT). Monthly figures by country are not published, so they are <b>estimated</b>: arrivals from a country × that country's leisure share (stat.uz, January–June 2025)."),
    "leis_check": ("Tekshiruv: 2025 ulushlari oldingi yillarga qo'llanib, rasmiy jami bilan solishtirildi — xato {v}. Demak baho taxminan ±10% aniq; ulushlar vaqt o'tishi bilan o'zgaradi. «Boshqa davlatlar» — qolgan ~190 davlat bir guruh sifatida.",
                   "Проверка: доли 2025 года применены к прошлым годам и сравнены с официальным итогом — ошибка {v}. Значит, оценка точна примерно ±10%; доли со временем меняются. «Другие страны» — остальные ~190 стран одной группой.",
                   "Check: the 2025 shares were applied to earlier years and compared with the official total — error {v}. So the estimate is accurate to about ±10%; shares change over time. “Other countries” = the remaining ~190 countries as one group."),
    # ---------------------------------------------------------------- chapter 3
    "attr_t": ("Jalb etish xaritasi: qayerga va qanday ma'lumot yuborish", "Карта привлечения: куда и какую информацию отправлять", "Attraction map: where to send what information"),
    "attr_what": ("Rang — bozor guruhi. Davlat ustiga olib boring: tavsiya, sabab va kanal chiqadi.",
                  "Цвет — группа рынка. Наведите на страну: появятся рекомендация, причина и канал.",
                  "Colour = market group. Hover over a country to see the recommendation, the reason and the channel."),
    "attr_note": ("To'rtta o'lchangan ko'rsatkich birlashtirilgan: <b>dam olish uchun kelganlar</b> (baho); <b>imkoniyat</b> — 5 kunlik safarga qodir har 1000 kishiga dam olish safarlari, uzoq bozorlarning odatiy darajasiga nisbatan; "
                  "<b>tanilganlik</b> — Google qidiruvlaridagi ulush (20% = teng); <b>o'sish</b>. Qoidalar qat'iy, sun'iy intellekt ishlatilmaydi.",
                  "Объединены четыре измеренных показателя: <b>приезжающие на отдых</b> (оценка); <b>потенциал</b> — поездки на отдых на 1000 человек, способных оплатить 5-дневную поездку, относительно типичного уровня дальних рынков; "
                  "<b>известность</b> — доля в поиске Google (20% = поровну); <b>рост</b>. Правила фиксированные, ИИ не используется.",
                  "Four measured indicators are combined: <b>leisure visitors</b> (estimate); <b>headroom</b> — leisure visits per 1,000 people who can afford a 5-day trip, against the typical level of distant markets; "
                  "<b>awareness</b> — share of Google searches (20% = equal share); and <b>growth</b>. Fixed rules, no AI."),
    "attr_typical": ("Odatiy daraja — har 1000 qodir kishidan {r} dam olish safari. Imkoniyat — bozor shu darajaga yetsa yiliga qo'shimcha safarlar (qo'shnilarda — dam olish ulushi eng yaxshi qo'shnidek bo'lsa). Qodir kishilar soni va dam olish ulushi — baho (±10–20%); kanallar — umumiy ma'lumot, o'lchanmagan.",
                     "Типичный уровень — {r} поездки на отдых на 1000 платёжеспособных. Потенциал — дополнительные поездки в год, если рынок достигнет этого уровня (для соседей — если доля отдыха станет как у лучшего соседа). Число платёжеспособных и доля отдыха — оценки (±10–20%); каналы — общие сведения, не измерены.",
                     "Typical level = {r} leisure visits per 1,000 people who can afford the trip. Headroom = extra visits per year if a market reached that level (for neighbours: if its leisure share matched the best neighbour). Affordability and leisure shares are estimates (±10–20%); channels are general knowledge, not measured."),
    "grp_A": ("Katta imkoniyat", "Большой потенциал", "Big opportunity"), "grp_B": ("Kuchli bozor", "Сильный рынок", "Strong market"),
    "grp_C": ("Konversiya (qo'shnilar)", "Конверсия (соседи)", "Conversion (neighbours)"), "grp_D": ("Kuzatish", "Наблюдение", "Watch"),
    "leis_trips_y": ("Dam olish safarlari, 2025", "Поездки на отдых, 2025", "Leisure visits, 2025"),
    "headroom": ("Imkoniyat", "Потенциал", "Headroom"), "channel": ("Kanal", "Канал", "Channel"),
    "c_group": ("Guruh", "Группа", "Group"), "c_per1000": ("1000 qodir kishiga", "на 1000 платёжеспособных", "per 1,000 who can afford it"),
    "c_headroom": ("Imkoniyat, +/yil", "Потенциал, +/год", "Headroom, +/year"), "c_google": ("Google ulushi", "Доля в Google", "Google share"),
    "c_message": ("Xabar turi va kanal", "Тип сообщения и канал", "Message and channel"), "share_lbl": ("ulush", "доля", "share"),
    "trends_t": ("Google qidiruvlari: O'zbekiston raqiblar orasida", "Поиск Google: Узбекистан среди конкурентов", "Google searches: Uzbekistan among its rivals"),
    "trends_what": ("5 ta yo'nalish qidiruvlari 100% bo'lsa, O'zbekistonga qanchasi to'g'ri keladi.", "Если поиски по 5 направлениям = 100%, какая доля приходится на Узбекистан.",
                    "If searches for 5 destinations add up to 100%, how much of it goes to Uzbekistan."),
    "trends_years_t": ("O'zbekiston ulushi yillar bo'yicha, %", "Доля Узбекистана по годам, %", "Uzbekistan's share by year, %"),
    "trends_latest": ("So'nggi 90 kun", "Последние 90 дней", "Last 90 days"),
    "trends_latest_d": ("So'nggi 90 kun ({d} gacha)", "Последние 90 дней (до {d})", "Last 90 days (to {d})"),
    "trends_note": ("Yo'nalishlar: O'zbekiston, Qozog'iston, Qirg'iziston, Gruziya, Tojikiston. Manba: Google Trends (mavzular, tildan qat'i nazar), har hafta. <b>Ehtiyot bo'ling:</b> bu barcha qidiruvlar — yangilik, sport, biznes, faqat sayohat emas. Xitoyda Google bloklangan.",
                    "Направления: Узбекистан, Казахстан, Кыргызстан, Грузия, Таджикистан. Источник: Google Trends (темы, независимо от языка), еженедельно. <b>Осторожно:</b> это все поиски — новости, спорт, бизнес, не только путешествия. В Китае Google заблокирован.",
                    "Destinations: Uzbekistan, Kazakhstan, Kyrgyzstan, Georgia, Tajikistan. Source: Google Trends (topics, any language), weekly. <b>Caution:</b> these are all searches — news, sport, business — not only travel. Google is blocked in China."),
    "world_cup": ("Jahon chempionati", "Чемпионат мира", "World Cup"),
    # ---------------------------------------------------------------- chapter 4
    "map_t": ("Dunyo xaritasi: kim keladi va kim qiziqadi", "Карта мира: кто приезжает и кто интересуется", "World map: who visits and who is interested"),
    "map_what": ("Davlatni bosing — yonida uning statistikasi, grafiklari va voqealari chiqadi. Xaritani surish va kattalashtirish mumkin.",
                 "Нажмите на страну — рядом появятся её статистика, графики и события. Карту можно двигать и увеличивать.",
                 "Click a country to see its statistics, charts and events. The map can be dragged and zoomed."),
    "m_arrivals": ("Turistlar soni", "Число туристов", "Visitors"), "m_growth": ("O'sish (oldingi yilga)", "Рост (к прошлому году)", "Growth (vs previous year)"),
    "m_share": ("Vikipediya qiziqishi", "Интерес в Википедии", "Wikipedia interest"), "m_change": ("Qiziqish o'zgarishi (yillik)", "Изменение интереса (за год)", "Change in interest (yearly)"),
    "year_lbl": ("Yil:", "Год:", "Year:"),
    "no_data": ("ma'lumot yo'q", "нет данных", "no data"), "tourists_w": ("turistlar", "туристы", "visitors"),
    "vs_prev_year": ("oldingi yilga", "к прошлому году", "vs previous year"), "vs_last_year": ("o'tgan yilga", "к прошлому году", "vs last year"),
    "vs_year": ("{y} ga nisbatan", "к {y}", "vs {y}"), "per_million_short": ("1 mln ko'rish", "1 млн просмотров", "1M views"),
    "lg_arrivals": ("Turistlar, {y}", "Туристы, {y}", "Visitors, {y}"), "lg_growth": ("O'sish, {y}", "Рост, {y}", "Growth, {y}"),
    "lg_share": ("Vikipediya: 1 mln ko'rishga (30 kunlik mediana)", "Википедия: на 1 млн просмотров (медиана за 30 дней)", "Wikipedia: per 1M views (30-day median)"),
    "lg_change": ("Qiziqish o'zgarishi", "Изменение интереса", "Change in interest"),
    "lg_only_tracked": ("Faqat kuzatilayotgan bozorlar", "Только отслеживаемые рынки", "Tracked markets only"),
    "total_foreign": ("Jami xorijiy turistlar", "Всего иностранных туристов", "Total foreign visitors"),
    "tourists_y": ("Turistlar {y}", "Туристы {y}", "Visitors {y}"), "share_total": ("Jami oqimdagi ulushi", "Доля в общем потоке", "Share of all visitors"),
    "in_months": ("{y}: {n} oyda", "{y}: за {n} мес.", "{y}: {n} months"), "wiki_30": ("Vikipediya, 30 kun", "Википедия, 30 дней", "Wikipedia, 30 days"),
    "per_million_med": ("1 mln ko'rishga (mediana)", "на 1 млн просмотров (медиана)", "per 1M views (median)"),
    "interest_yoy": ("Qiziqish, yillik", "Интерес, за год", "Interest, yearly"), "past_events": ("O'tgan voqealar", "Прошедшие события", "Past events"),
    "wiki_w": ("Vikipediya", "Википедия", "Wikipedia"), "pending": ("kutilmoqda", "ожидается", "pending"), "unreliable": ("ishonchsiz", "ненадёжно", "unreliable"),
    "upcoming_w": ("Kutilayotgan", "Ожидаемые", "Upcoming"), "interest_w": ("qiziqish", "интерес", "interest"),
    "not_tracked": ("Bu davlat uchun Vikipediya qiziqishi kuzatilmaydi.", "Интерес в Википедии для этой страны не отслеживается.", "Wikipedia interest is not tracked for this country."),
    "mini_arr": ("Turistlar, yillar bo'yicha", "Туристы по годам", "Visitors by year"),
    "mini_wiki": ("Vikipediya, 7 kunlik o'rtacha (2 yil)", "Википедия, среднее за 7 дней (2 года)", "Wikipedia, 7-day average (2 years)"),
    "views_t": ("Vikipediya ko'rishlari, bozorlar bo'yicha", "Просмотры Википедии по рынкам", "Wikipedia views by market"),
    "views_what": ("O'zbekiston, Samarqand, Buxoro, Xiva, Toshkent sahifalari; har bir til = bir bozor. ▼ — voqealar.",
                   "Страницы Узбекистан, Самарканд, Бухара, Хива, Ташкент; каждый язык = один рынок. ▼ — события.",
                   "Pages on Uzbekistan, Samarkand, Bukhara, Khiva and Tashkent; each language = one market. ▼ = events."),
    "scale_log": ("Log shkala", "Лог. шкала", "Log scale"), "scale_lin": ("Oddiy shkala", "Обычная шкала", "Linear scale"),
    "views_note": ("Hafta/oy/yil — shu davrdagi ko'rishlar yig'indisi (tugallanmagan oxirgi davr ko'rsatilmaydi). Qo'shni davlatlar yashirin — legendani bosib yoqing. Kamera belgisi grafikni PNG qilib yuklaydi. Bir kunlik keskin sakrash avtomatik trafik bo'lishi mumkin.",
                   "Неделя/месяц/год — сумма просмотров за период (незавершённый последний период не показан). Соседние страны скрыты — включите кликом по легенде. Значок камеры сохраняет график в PNG. Резкий скачок за один день может быть автоматическим трафиком.",
                   "Week/month/year = total views in the period (an unfinished last period is not shown). Neighbouring countries are hidden — click the legend to show them. The camera icon saves the chart as PNG. A sharp one-day spike may be automated traffic."),
    "views_per": ("ko'rishlar / {u}", "просмотров / {u}", "views / {u}"),
    "u_day": ("kun", "день", "day"), "u_week": ("hafta", "неделю", "week"), "u_month": ("oy", "месяц", "month"), "u_year": ("yil", "год", "year"),
    "events_lbl": ("Voqealar", "События", "Events"),
    "share_t": ("Qiziqish ulushi (Vikipediya trafigiga nisbatan)", "Доля интереса (относительно трафика Википедии)", "Share of interest (relative to Wikipedia traffic)"),
    "share_what": ("Har 1 million Vikipediya ko'rishidan nechtasi O'zbekiston sahifalariga to'g'ri keladi (7 kunlik o'rtacha). Vikipediya trafigi kamayayotgani uchun uzoq muddatga shu grafik to'g'riroq.",
                   "Сколько из каждого 1 млн просмотров Википедии приходится на страницы об Узбекистане (среднее за 7 дней). Поскольку трафик Википедии падает, для долгосрочного сравнения этот график точнее.",
                   "How many of every 1 million Wikipedia views go to Uzbekistan pages (7-day average). Because overall Wikipedia traffic is falling, this chart is better for long-term comparison."),
    "per_million": ("1 mln ko'rishga", "на 1 млн просмотров", "per 1M views"),
    # ---------------------------------------------------------------- chapter 5
    "up_t": ("Kutilayotgan voqealar va ularning kutilgan ta'siri", "Ожидаемые события и их ожидаемое влияние", "Upcoming events and their expected effect"),
    "up_what": ("Ehtimollar — o'tgan o'lchangan o'xshash voqealarga asoslangan ulush, bashorat emas.",
                "Вероятности — доля среди измеренных похожих прошлых событий, а не предсказание.",
                "Probabilities are shares of similar past events that were measured — not predictions."),
    "up_note": ("Voqea qo'shish: Telegram botga oddiy so'zlar bilan yozing yoki yangilikni ✅ bilan tasdiqlang. Faqat viza, chegara, reys yoki yirik tadbir, aniq davlat nomi bilan. Voqea o'tgach, haqiqiy ta'sir o'zi o'lchanadi.",
                "Добавить событие: напишите боту в Telegram обычными словами или одобрите новость ✅. Только визы, границы, рейсы или крупные мероприятия с указанием страны. После события реальное влияние измеряется автоматически.",
                "To add an event, write to the Telegram bot in plain words or approve a news item with ✅. Only visas, borders, flights or major events naming a country. After the event, its real effect is measured automatically."),
    "dir_next": ("Kelgusi", "Будущие", "Upcoming"), "dir_past": ("O'tgan", "Прошедшие", "Past"),
    "w_day": ("Kun", "День", "Day"), "w_week": ("Hafta", "Неделя", "Week"), "w_month": ("Oy", "Месяц", "Month"), "w_year": ("Yil", "Год", "Year"), "w_all": ("Hammasi", "Все", "All"),
    "win_1": ("bugun", "сегодня", "today"), "win_7": ("shu hafta", "эта неделя", "this week"), "win_31": ("shu oy", "этот месяц", "this month"),
    "win_366": ("shu yil", "этот год", "this year"), "win_99999": ("hammasi", "все", "all"),
    "none_next": ("Kelgusi davrda ({w}) tasdiqlangan voqea yo'q. Eng yaqini: {e}.", "В ближайший период ({w}) подтверждённых событий нет. Ближайшее: {e}.",
                  "No confirmed events in this period ({w}). Next one: {e}."),
    "none_past": ("O'tgan davrda ({w}) voqea yo'q.", "В прошедший период ({w}) событий нет.", "No events in the past period ({w})."),
    "exp_none": ("Turistlar soniga ta'sir: o'xshash voqealar yetarli emas ({n} ta).", "Влияние на число туристов: недостаточно похожих событий ({n}).",
                 "Effect on visitor numbers: not enough similar events ({n})."),
    "exp_t": ("Turistlar soniga kutilgan ta'sir, oyiga", "Ожидаемое влияние на число туристов, в месяц", "Expected effect on visitors per month"),
    "exp_n": ("{n} ta o'xshash voqea; o'rtacha natija va o'rtadagi yarmining oralig'i", "{n} похожих событий; средний результат и диапазон средней половины",
              "{n} similar events; median result and the range of the middle half"),
    "exp_rose": ("Shu turdagi voqealar odatda turistlar oqimini oshirgan.", "События этого типа обычно увеличивали поток туристов.", "Events of this type usually increased visitor numbers."),
    "exp_flat": ("Shu turdagi voqealar odatda turistlar sonini sezilarli o'zgartirmagan.", "События этого типа обычно заметно не меняли число туристов.",
                 "Events of this type usually did not change visitor numbers noticeably."),
    "c_now_month": ("Hozir/oy", "Сейчас/мес.", "Now/month"), "c_expected": ("Kutilgan", "Ожидается", "Expected"),
    "c_range": ("Oraliq", "Диапазон", "Range"), "c_basis": ("Asos", "Основа", "Basis"),
    "in_similar": ("{k}/{n} o'xshash holatda (ishonch: {c})", "в {k}/{n} похожих случаях (надёжность: {c})", "in {k}/{n} similar cases (confidence: {c})"),
    "conf_low": ("past", "низкая", "low"), "conf_medium": ("o'rta", "средняя", "medium"), "conf_high": ("yuqori", "высокая", "high"),
    "not_enough_n": ("ma'lumot yetarli emas ({n} ta o'xshash voqea)", "недостаточно данных ({n} похожих событий)", "not enough data ({n} similar events)"),
    "approx": ("taxminiy", "примерно", "approximate"), "prec_month": ("oy", "месяц", "month"), "prec_quarter": ("chorak", "квартал", "quarter"),
    "in_days": ("{n} kundan keyin", "через {n} дн.", "in {n} days"), "days_ago": ("{n} kun oldin", "{n} дн. назад", "{n} days ago"),
    "all_distant": ("barcha uzoq bozorlar", "все дальние рынки", "all distant markets"), "neighbours": ("qo'shni davlatlar", "соседние страны", "neighbouring countries"),
    "source": ("manba", "источник", "source"), "info_search": ("Ma'lumot qidirish", "Поиск информации", "Interest (searching)"),
    "arrivals_w": ("Turistlar kelishi", "Приезд туристов", "Visitor arrivals"), "mixed": ("aralash", "смешано", "mixed"),
    "wv_strong": ("kuchli", "сильная", "strong"), "wv_some": ("biroz", "слабая", "some"), "wv_none": ("yo'q", "нет", "none"),
    "c_wiki7": ("Vikipediya, 7 kun", "Википедия, 7 дней", "Wikipedia, 7 days"), "c_before_after": ("Turistlar, oldin → keyin", "Туристы, до → после", "Visitors, before → after"),
    "c_diff": ("Farq", "Разница", "Difference"),
    "ev_t": ("O'tgan voqealar ta'siri: tur bo'yicha xulosa", "Влияние прошедших событий: итог по типам", "Effect of past events: summary by type"),
    "ev_what": ("Kutilayotgan voqealarning ehtimollari shu jadvaldan hisoblanadi.", "Вероятности для ожидаемых событий рассчитываются по этой таблице.",
                "The probabilities for upcoming events are calculated from this table."),
    "ev_all": ("Barcha voqealar jadvali va usul", "Таблица всех событий и метод", "Table of all events and method"),
    "ev_note": ("Har bir voqea uchun: <b>Vikipediya</b> — keyingi 7 kunda qiziqish odatdagidan necha baravar; <b>turistlar</b> — o'sha davlatdan kelganlar o'zgarishi, umumiy oqimga nisbatan («farq» ×1,2 dan yuqori = ko'proq o'sdi). "
                "Bu bog'liqlik, isbot emas. Mavsum boshqa yillarning shu oylari bilan tozalanadi. Kulrang qatorlar — boshqa voqea bilan aralash yoki COVID davri; xulosaga qo'shilmaydi.",
                "Для каждого события: <b>Википедия</b> — во сколько раз интерес за 7 дней выше обычного; <b>туристы</b> — изменение числа приехавших из страны относительно общего потока («разница» выше ×1,2 = рост больше). "
                "Это связь, а не доказательство. Сезонность убирается сравнением с теми же месяцами других лет. Серые строки — смешаны с другим событием или период COVID; в итог не входят.",
                "For each event: <b>Wikipedia</b> — how many times interest in the next 7 days exceeded the usual level; <b>visitors</b> — the change in arrivals from that country relative to the overall flow (“difference” above ×1.2 = grew more). "
                "This is association, not proof. Seasonality is removed by comparing with the same months of other years. Grey rows overlap with another event or fall in the COVID period and are excluded."),
    "c_event": ("Voqea", "Событие", "Event"), "c_date": ("Sana", "Дата", "Date"), "c_type": ("Turi", "Тип", "Type"), "c_result": ("Natija", "Результат", "Result"),
    "c_events": ("Voqealar", "Событий", "Events"), "c_wiki_react": ("Vikipediya reaksiyasi", "Реакция Википедии", "Wikipedia reacted"),
    "c_arr_rose": ("Turistlar ko'proq o'sgan", "Туристов стало больше", "Visitors grew more"), "c_med_diff": ("O'rtacha farq", "Средняя разница", "Median difference"),
    "av_rose": ("ko'proq o'sdi", "рост больше", "grew more"), "av_fell": ("kamaydi", "снижение", "fell"), "av_none": ("aniq o'zgarish yo'q", "явных изменений нет", "no clear change"),
    "n_mixed": ("boshqa voqea bilan aralash", "смешано с другим событием", "overlaps another event"), "n_covid": ("COVID davri", "период COVID", "COVID period"),
    "n_season": ("mavsum hisobga olinmagan", "сезонность не учтена", "season not controlled"), "n_season_y": ("mavsum", "сезон", "season"),
    "type_visa": ("viza", "визы", "visa"), "type_border": ("chegara ochilishi", "открытие границы", "border opening"), "type_crossing": ("o'tish punkti", "пункт пропуска", "border crossing"),
    "type_flight": ("reys", "рейс", "flight"), "type_event": ("tadbir", "мероприятие", "event"), "type_sport": ("sport", "спорт", "sport"),
    "type_politics": ("siyosat", "политика", "politics"), "type_price": ("narx", "цены", "prices"), "type_infrastructure": ("infratuzilma", "инфраструктура", "infrastructure"),
    "type_marketing": ("marketing / media", "маркетинг / СМИ", "marketing / media"), "type_other": ("boshqa", "другое", "other"),
    # ---------------------------------------------------------------- chapter 6
    "src_t": ("Ma'lumot manbalari", "Источники данных", "Data sources"),
    "src_html": ("<ul><li><b>Vikipediya ko'rishlari</b> (Wikimedia, CC0) — har kuni, 2016 yildan, 15 til.</li>"
                 "<li><b>Xorijiy turistlar</b> — Milliy statistika qo'mitasi: oylik press-relizlar (2022 avgustdan) va SIAT yillik ma'lumotlari, 205 davlat (CC BY 4.0).</li>"
                 "<li><b>Safar maqsadlari</b> — SIAT (yillik, 2016–2025) va stat.uz davlatlar kesimidagi relizlar.</li>"
                 "<li><b>Google Trends</b> — 11 bozorda qidiruv ulushi, har hafta.</li>"
                 "<li><b>Daromad va iste'mol</b> — Jahon banki, World Inequality Database: kim 5 kunlik safarga qodir.</li>"
                 "<li><b>Yangiliklar</b> — kun.uz, gazeta.uz, UzDaily, Google News; AI saralaydi, odam tasdiqlaydi.</li></ul>",
                 "<ul><li><b>Просмотры Википедии</b> (Wikimedia, CC0) — ежедневно, с 2016 г., 15 языков.</li>"
                 "<li><b>Иностранные туристы</b> — Национальный комитет по статистике: ежемесячные пресс-релизы (с августа 2022) и годовые данные SIAT, 205 стран (CC BY 4.0).</li>"
                 "<li><b>Цели поездок</b> — SIAT (годовые, 2016–2025) и релизы stat.uz по странам.</li>"
                 "<li><b>Google Trends</b> — доля в поиске на 11 рынках, еженедельно.</li>"
                 "<li><b>Доходы и потребление</b> — Всемирный банк, World Inequality Database: кто может позволить себе 5-дневную поездку.</li>"
                 "<li><b>Новости</b> — kun.uz, gazeta.uz, UzDaily, Google News; ИИ отбирает, человек одобряет.</li></ul>",
                 "<ul><li><b>Wikipedia views</b> (Wikimedia, CC0) — daily since 2016, 15 languages.</li>"
                 "<li><b>Foreign visitors</b> — National Statistics Committee: monthly press releases (from August 2022) and SIAT yearly data for 205 countries (CC BY 4.0).</li>"
                 "<li><b>Purpose of visit</b> — SIAT (yearly, 2016–2025) and stat.uz releases by country.</li>"
                 "<li><b>Google Trends</b> — search share in 11 markets, weekly.</li>"
                 "<li><b>Income and consumption</b> — World Bank, World Inequality Database: who can afford a 5-day trip.</li>"
                 "<li><b>News</b> — kun.uz, gazeta.uz, UzDaily, Google News; AI shortlists, a person approves.</li></ul>"),
    "lim_t": ("Cheklovlar — nimani bilmaymiz", "Ограничения — чего мы не знаем", "Limitations — what we do not know"),
    "lim_html": ("<ul><li><b>Kunlik rasmiy raqam yo'q</b>: rasmiy ma'lumot oylik, taxminan 3 hafta kechikib chiqadi.</li>"
                 "<li><b>«Turist» — safar, odam emas</b>: bir kishi bir necha marta kelsa, har biri sanaladi.</li>"
                 "<li><b>Prognoz xatosi</b>: jami ~6%, kichik bozorlarda 20–40%. 75% so'ndirish o'tmish ma'lumotida tanlangan — jonli natijalar tasdiqlashi kerak.</li>"
                 "<li><b>Dam olish uchun kelganlar va «qodir kishilar» — baho</b> (±10–20%).</li>"
                 "<li><b>Jalb etish tavsiyalari hali sinalmagan</b>: bu gipoteza; kampaniya natijasi bilan tekshiriladi.</li>"
                 "<li><b>Qiziqish ≠ sayohat</b>; bog'liqlik ≠ sabab. Voqealar soni hali kam.</li></ul>",
                 "<ul><li><b>Нет ежедневных официальных данных</b>: официальные данные месячные и выходят примерно через 3 недели.</li>"
                 "<li><b>«Турист» — это поездка, а не человек</b>: если человек приезжает несколько раз, учитывается каждая поездка.</li>"
                 "<li><b>Ошибка прогноза</b>: в целом ~6%, на малых рынках 20–40%. Коэффициент 75% выбран на исторических данных — его должны подтвердить живые результаты.</li>"
                 "<li><b>Приезжающие на отдых и «платёжеспособные» — оценки</b> (±10–20%).</li>"
                 "<li><b>Рекомендации по привлечению ещё не проверены</b>: это гипотеза, её проверит результат кампании.</li>"
                 "<li><b>Интерес ≠ поездка</b>; связь ≠ причина. Событий пока мало.</li></ul>",
                 "<ul><li><b>No official daily figures</b>: official data are monthly and arrive about 3 weeks late.</li>"
                 "<li><b>A “tourist” is a visit, not a person</b>: someone who comes several times is counted each time.</li>"
                 "<li><b>Forecast error</b>: about 6% overall, 20–40% for small markets. The 75% damping was chosen on past data — live results must confirm it.</li>"
                 "<li><b>Leisure visitors and “who can afford it” are estimates</b> (±10–20%).</li>"
                 "<li><b>The attraction recommendations are not yet tested</b>: they are hypotheses to be checked with a campaign.</li>"
                 "<li><b>Interest ≠ travel</b>; association ≠ cause. There are still few events.</li></ul>"),
    "dl_t": ("Ma'lumotlarni yuklab olish", "Скачать данные", "Download the data"),
    "dl_report": ("Haftalik hisobot (Word, o'zbekcha)", "Еженедельный отчёт (Word, на узбекском)", "Weekly report (Word, in Uzbek)"),
    "dl_views_m": ("Kunlik ko'rishlar (bozorlar), CSV", "Ежедневные просмотры (рынки), CSV", "Daily views by market, CSV"),
    "dl_views_p": ("Kunlik ko'rishlar (sahifalar), CSV", "Ежедневные просмотры (страницы), CSV", "Daily views by page, CSV"),
    "dl_month": ("Rasmiy statistika (oylik), CSV", "Официальная статистика (месяц), CSV", "Official arrivals (monthly), CSV"),
    "dl_ytd": ("Rasmiy statistika (yil boshidan), CSV", "Официальная статистика (с начала года), CSV", "Official arrivals (year to date), CSV"),
    "dl_purpose": ("Safar maqsadlari (yillik), CSV", "Цели поездок (годовые), CSV", "Purpose of visit (yearly), CSV"),
    "dl_leisure": ("Dam olish uchun kelganlar (baho), CSV", "Приезжающие на отдых (оценка), CSV", "Leisure visitors (estimate), CSV"),
    "dl_attr": ("Jalb etish xaritasi, CSV", "Карта привлечения, CSV", "Attraction map, CSV"),
    "dl_events": ("Voqealar ta'siri, CSV", "Влияние событий, CSV", "Event effects, CSV"),
    "dl_offline": ("Sahifa — oflayn HTML (internetsiz ochiladi)", "Страница — офлайн HTML (открывается без интернета)", "This page offline (HTML, opens without internet)"),
    "dl_preparing": ("Tayyorlanmoqda…", "Готовится…", "Preparing…"),
    "dl_error": ("Xato: sahifani GitHub Pages orqali oching", "Ошибка: откройте страницу через GitHub Pages", "Error: open the page via GitHub Pages"),
    "footer": ("Mo'minov Ismoiljon · Toshkent davlat agrar universiteti, «Turizm va mehmondo'stlik» magistraturasi. "
               "Manbalar: Wikimedia (CC0), O'zbekiston Milliy statistika qo'mitasi (CC BY 4.0), Google Trends, Jahon banki, WID. Kod ochiq: GitHub.",
               "Муминов Исмоилжон · Ташкентский государственный аграрный университет, магистратура «Туризм и гостеприимство». "
               "Источники: Wikimedia (CC0), Национальный комитет по статистике Узбекистана (CC BY 4.0), Google Trends, Всемирный банк, WID. Открытый код: GitHub.",
               "Ismoiljon Mominov · Tashkent State Agrarian University, MSc Tourism and Hospitality. "
               "Sources: Wikimedia (CC0), National Statistics Committee of Uzbekistan (CC BY 4.0), Google Trends, World Bank, WID. Open source code on GitHub."),
    # ---------------------------------------------------------------- common
    "months": ("yanv,fev,mar,apr,may,iyun,iyul,avg,sent,okt,noy,dek", "янв,фев,мар,апр,май,июн,июл,авг,сен,окт,ноя,дек",
               "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec"),
    "total": ("Jami", "Всего", "Total"), "other_countries": ("Boshqa davlatlar", "Другие страны", "Other countries"),
    "series_en": ("Ingliz tili (global)", "Английский (глобально)", "English (global)"),
    "series_ru": ("Rus tili (MDH)", "Русский (СНГ)", "Russian (CIS)"),
    "rs_1m": ("1 oy", "1 мес", "1m"), "rs_6m": ("6 oy", "6 мес", "6m"), "rs_1y": ("1 yil", "1 год", "1y"), "rs_3y": ("3 yil", "3 года", "3y"), "rs_all": ("Hammasi", "Все", "All"),
    "no_plotly": ("Grafik kutubxonasi yuklanmadi. Sahifani brauzerda oching yoki oflayn faylni yuklab oling.",
                  "Библиотека графиков не загрузилась. Откройте страницу в браузере или скачайте офлайн-файл.",
                  "The chart library did not load. Open the page in a browser or download the offline file."),
}


def as_json_dict() -> dict:
    out = {"uz": {}, "ru": {}, "en": {}}
    for k, (uz, ru, en) in STRINGS.items():
        out["uz"][k], out["ru"][k], out["en"][k] = uz, ru, en
    return out

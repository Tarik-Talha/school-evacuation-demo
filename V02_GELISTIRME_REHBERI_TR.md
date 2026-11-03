# School Evacuation Pilot v0.2 — gelişen senaryo atölyesi

20 Ekim 2026 · 111 öğrenci · yerel çalışma.

[Ekranı aç](http://127.0.0.1:8532/). Ana ekranın görünümü v0.1'e benzer; sol menüde sürüm **v0.2**, ana bölümde sekiz sekme bulunur. Sunucu kapalıysa `start_school_pilot.vbs` çift tıklanır; görünür komut penceresi açmaz. TwinOps ve SchoolWatch ayrı projelerdir.

## Yeni özellikler nasıl kullanılır?

1. **Kat planı:** Katı ve başlangıç anını seç, grafiğin üstündeki **Oynat** düğmesine bas. Öğrenciler orijinal plan fotoğrafının üzerinde gösterilir. Fotoğraflar değiştirilmez. Oda eşleştirme formunda her şubenin odası seçilebilir ve okuldan doğrulandıysa işaretlenebilir. Başlangıçta **0/10 eşleşme doğrulanmış** durumdadır. Noktalı çizgiler yaklaşık görsel bağlantılardır; ölçülmüş kaçış yolları değildir.
2. **Öğrenci ve sınıf davranışı:** Sol menüde hız çeşitliliği, sınıf hazırlık farkı, sınıfça hareket ve başlangıç aralığını değiştir. Sınıfça mod aynı sınıfa ortak başlangıç, rota ve tempo verir. Kuyrukların birleşmesinde sınıflar birbirine karışabilir; kesintisiz sınıf bloğu garantisi yoktur. Varsayılan şube sırası tahliye önceliği değildir.
3. **Çoklu deneme:** 20/50/100/200 eşlenmiş deneme çalıştır. Referans ile seçili koşul aynı öğrenci hız ve hazırlık çekilişlerini kullanır. Tamamlanan koşu sayısı, ortanca ve %5–%95 eşikleri gösterilir. Ayar değiştirilince eski sonuç gizlenir; tekrar çalıştırmak gerekir.
4. **Deney atölyesi:** Bireysel kısa rota, bireysel dağıtılmış akış, sınıfça dağıtılmış akış ve 3 saniye başlangıç aralıklı sınıfça akış aynı tohumlarla karşılaştırılır. Bu bir model deneyi; uygulanacak tahliye sırası önerisi değildir. Yalnız bütün denemeleri tamamlayan düzenler süreye göre sıralanır.
5. **Tatbikat / Ölçüler:** Sarsıntı bitiminden itibaren ilk hareket, son dış çıkış ve son saha varışı gözlemleri girilebilir. Sınıf bazında veya tüm öğrenciler için karşılaştırma yapılır. Kaynak adı ve örnek/gerçek ayrımı saklanır. Boş, geçersiz ve çelişkili zamanlar reddedilir. Geçiş uzunluğu ve net genişliği kaynak notuyla yerel kaydedilebilir; bu değerler seçili yerleşimde hem referansa hem seçili koşula uygulanır.
6. **3B / USD:** Aynı koşunun seçilen anını ve kat kesitini incele. **3B aktarım dosyalarını hazırla** ile JSON ve USDA indirilebilir. Hazır Blender dosyası `exports/school_evacuation_v02.blend` içindedir. Blender'da zaman çizgisini oynatınca aynı anonim öğrenciler hareket eder. Omniverse testi RTX bilgisayara bırakıldı.

## Sonuçları doğru okumak

Üst kartlar tek koşunun son sonucudur. Animasyon saati deprem başlangıcından, varış süreleri sarsıntı bitişinden başlar. Öğretmen, personel, ziyaretçi ve yoklama süresi kullanıcının belirlediği ilk kapsam gereği dahil değildir. Ders, toplu yemek ve örnek laboratuvar yerleşimi çalışır; belirsiz teneffüs/merdiven başlangıç konumları uydurulmaz.

Çoklu koşu aralığı, modelde seçilmiş hız/hazırlık değişkenliğini gösterir. Gerçek deprem için güven aralığı değildir. “Eşlenmiş ortanca fark”, her koşuda referans süresinden seçili süre çıkarılıp bu farkların ortancası alınarak bulunur. İki grubun ortancalarını çıkarmak farklı bir istatistiktir. Tamamlanmayan koşular gizlenmez; tüm çiftler tamamlanmadığında iyileşme sonucu verilmez.

Geometri ve oda eşleştirmeleri henüz sahada doğrulanmadı. Fotoğraflar perspektiflidir; pikseller metreye çevrilmedi. 3B kat boyutları ve kat yüksekliği örnek ölçektir; kat fotoğrafları mimari olarak ortak koordinata oturtulmuş değildir. Animasyon gerçek okulun ölçülü dijital ikizi olarak sunulmamalı. Bahçedeki saha kullanıcının önerisidir; güvenli alan sınırı ve kapasitesi doğrulanmadı.

Tatbikat karşılaştırması hata miktarını gösterir; hız veya akış katsayısını otomatik öğrenmez. Gerçek tatbikat verisi girilmedi, model kalibre edilmedi. Önce şube–oda eşleştirmesi, kesintisiz merdiven/dış çıkış bağlantıları ve net ölçüler doğrulanmalı; sonra bir tatbikatla karşılaştırma yapılmalı. Şu an bina dayanımı, hasar, yaralanma ve can kaybı sonucu yoktur.

## Gerçekte çalıştırılan kontroller

- 47 girdi, motor ve arayüz testi geçti. Eski motor/girdi kontrolleri de bu sayıya dahildir. Plan görselinin veri koordinatlarına bağlanması ayrıca kontrol edilir.
- 100 eşlenmiş referans/seçili koşu çalıştırıldı. Örnek seçili koşulda yangın rotası kapalıydı. Her iki tarafta 100/100 tamamlandı; seçili koşul için ortanca fark **−4,62 saniye**, yani bu model deneyinde süre uzadı. Bu okul için ölçülmüş sonuç değildir. Rapor: `reports/paired_100_v02.json`.
- Dört akış düzeni için 30'ar koşu çalıştırıldı. Rapor: `reports/strategies_30_v02.json`.
- Blender 4.4.3 CPU ile sahne üretildi ve görsel alındı. Bağımsız USDA dosyası Blender'ın USD okuyucusuyla açıldı: **111 öğrenci noktası** korundu.
- Kaydedilmiş `.blend` ayrı Blender sürecinde yeniden açıldı: 111 öğrenci nesnesi ve başlangıç/bitiş konumları kontrol edildi. En yüksek uç konum farkı yaklaşık `0,000000232 m`; bu dosya aktarım kontrolüdür, gerçek dünya doğruluk ölçüsü değildir.
- **Omniverse çalıştırılmadı.** USDA taşınabilir çıktı olarak hazır; Omniverse içindeki görüntü/animasyon ayrıca denenmeli.

## Dosya adı + başlık + ne değişti + neden

**engine.py**

`# =========================================================`

**ÖĞRENCİ DAVRANIŞI VE ÖLÇÜLMÜŞ GEÇİŞLER:** Öğrenci hız farkı, sınıf hazırlığı, ortak tempo/rota ve sınıf başlangıç aralığı eklendi. Yerel ölçüler mevcut geçişlere uygulanır; bilinmeyen/etkin olmayan geçişler raporlanır. Neden: tek tip öğrenci kabulünü gevşetmek ve ileride ölçülmüş okul verisini aynı motorda kullanmak.

**experiments.py**

`# =========================================================`

**TEKRARLI DENEY VE TATBİKAT KARŞILAŞTIRMASI:** Eşlenmiş denemeler, dağılımlar, dört akış düzeni ve gözlem farkı hesabı eklendi. Neden: tek rastgele sonucu kesin kazanım gibi sunmamak; gerçek ölçüm geldiğinde model hatasını görünür kılmak.

**plan_layout.json / spatial.py / visuals.py**

`# =========================================================`

**PLAN GÖRSELİ VE DOĞRULANMAMIŞ ODA EŞLEŞTİRMESİ:** Kaynak fotoğrafları, oda/merdiven görsel işaretleri, oynatılabilir öğrenci noktaları ve aynı zamanın 3B konumları eklendi. Görsel arka planı öğrenci koordinatlarıyla aynı eksene bağlandı. Plan ve şematik animasyon, kareleri gerçekten yükleyen bağımsız yerel oynatıcıya alındı; harici betik indirmez. Neden: kullanıcı öğrencilerin nerede olduğunu anlayabilsin; Oynat düğmesi zaman adımlarını ilerletsin ve örnek işaretlerle gerçek ölçüler karıştırılmasın.

**advanced_ui.py / app.py**

`# =========================================================`

**SEKİZ SEKME VE AÇIKLAYICI KONTROLLER:** Kat planı, çoklu deneme, deney atölyesi, tatbikat/ölçüler, 3B/USD sekmeleri ve davranış ayarları eklendi. Sonuçlar ayarlara bağlı tutulur. Neden: modelin ne anlattığını ve hangi verinin eksik olduğunu ilk kullanıcıya açıklamak.

**scene_export.py / build_blender_scene.py / verify_blender_scene.py**

`# =========================================================`

**AYNI KOŞUDAN JSON, USDA VE BLENDER SAHNESİ:** 111 anonim kimlik ve zaman örnekleri korunarak sahne üretimi ve bağımsız dosya açma kontrolü eklendi. Neden: ekran, Blender ve sonraki Omniverse çalışması farklı hesap sonuçları göstermesin. 3B boyutlar hâlâ örnek ölçektir.

**test_advanced.py / reports/validation_v02.json**

`# =========================================================`

**GELİŞMİŞ DAVRANIŞ VE AKTARIM KONTROLLERİ:** Rastgele çekilişlerin tutarlılığı, nüfus korunumu, başarısız deneme raporları, girdi doğrulaması, arayüz düğmeleri ve dışa aktarım kontrolleri eklendi. Neden: sonraki gelişmelerde çalışan akışı korumak. Test geçmesi fiziksel tahliye doğrulaması değildir.

## Dokunmadığım çalışan dosyalar

TwinOps `app.py`, `engine.py`, `optimizer.py`, `usd_bridge.py`, `textile_pilot/app.py`; SchoolWatch `app.py`, `schoolwatch/live.py` dosyalarının SHA256 değerleri geliştirme öncesiyle karşılaştırıldı. Bu yedi dosya değişmedi. Kaynak 11 plan fotoğrafı da değişmedi. Ayrı projelere paket kurulmadı; onların sunucuları kapatılmadı.

Okulun `school_profile.json`, `scenarios.json`, `classes.csv`, kaynak manifesti ve ilk doğrulama kayıtları korundu. v0.2 geliştirmesi yalnız okul pilotunda ve bu çalışmanın yerel rapor/yedek alanındadır. Yerel oda eşleştirmeleri/ölçüler `runtime/` içinde saklanır; özel çalışma kayıtları paylaşım paketine dahil edilmez.

## Geri dönüş noktası

Geliştirmeden önceki v0.1 kopyası: `../SchoolEvacuationPilot_pre_v02_20261020.zip`. SHA256: `69898911bf34586e451133f4f6403cad3d0d06ac973c389addcde0d47ed13d5e`.

Tamamlanan v0.2 kopyası: `../SchoolEvacuationPilot_v02_snapshot.zip`. Çalışan klasörün üstüne açmak yerine ayrı bir klasöre çıkararak karşılaştırılabilir. Özel `runtime/`, önbellekler ve `.blend1` yedekleri paketlenmez. Ham plan fotoğrafları dışarıdaki yerel kaynak klasöründe kalır; başka bilgisayarda plan arka planları için bu kaynaklar ayrıca aynı göreli konuma taşınmalıdır. JSON/USDA/Blender sahneleri bu fotoğraflara bağımlı değildir.

Yalnız bu okul pilotunu geri almak gerekiyorsa 8532'deki okul süreci kapatılıp yedek ayrı klasörden başlatılır. TwinOps ve SchoolWatch'ta geri alınacak kod değişikliği yoktur. Kullanıcının gerçek ölçü/oda kayıtları varsa `runtime/` ayrıca korunmalı.

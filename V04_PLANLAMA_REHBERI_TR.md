# v0.4 — TwinOps tarzında koşula göre model planı

20 Ekim 2026 · [Uygulamayı aç](http://127.0.0.1:8532/)

Akış: **girdileri belirle → seçenekleri tara → mevcut düzenle karşılaştır → seçilen planı 3B izle**.

## Nasıl kullanılır?

1. Ana ekrandaki **1. Senaryo girdileri** bölümünü aç. Ders/yemek/laboratuvar yerleşimini, sarsıntı süresini, açık merdivenleri ve saha geçişini seç. Teneffüste gerçek başlangıç konumları bilinmediği için bu durum için otomatik yerleşim uydurulmaz.
2. **Planlamada öncelik** seç: süre, bekleme veya dengeli hedef. Arama sınırlarında Hızlı/Standart/Ayrıntılı kapsamını belirle. İlave başlangıç beklemesi varsayılan **0**; bu halde arama hiçbir şubeye yeni bekleme ekleyemez.
3. **Bu koşullar için plan öner** düğmesine bas. Sistem mevcut düzeni de aday olarak değerlendirir; yalnız farklı bir çıktı göstermek için düzen değiştirmez.
4. Sonuç gerekçesini ve şube dağılımını aç. **Mevcut düzen / Modelin seçtiği düzen** seçimi 3B sahneyi, sonuç kartlarını, kat planını ve dışa aktarılan koşuyu birlikte değiştirir. Önerilen plan ayrı bir kayıtta tutulur; başlangıç girdilerinin üstüne yazılmaz.
5. Girdileri değiştirdiğinde eski öneri gizlenir ve mevcut koşuya dönülür. Yeni koşul için yeniden arama gerekir. Plan ve deneme raporu JSON olarak indirilebilir.

Başlangıç rota kuralı ve fiziksel varsayımlar soldaki ayrıntılı model ayarlarında. **Mevcut düzen**, seçili başlangıç modelidir; okulun ölçülmüş/onaylı planı değildir. v0.4 arayüzünde sınıfça ortak başlangıç, rota ve tempo varsayılan açık; motorun önceki varsayılan API davranışı korunur. Sınıfça mod kuyruk birleşimlerinde sınıfların karışmasını bütünüyle engellemez.

## Arama neyi değiştirir?

- Şubeye atanan, modelde açık ve bağlı merdiven güzergâhını.
- Kullanıcı izin verdiyse, izin verilen sınır içinde şubeye ilave başlangıç beklemesini.

Öğrenci sayısı, başlangıç yerleşimi, sarsıntı, hızlar, hazırlık dağılımı, genişlik/uzunluklar, akış katsayıları, ölçüm kayıtları, kapalı rotalar ve saha durumu aynı kalır. Kapalı bir yolu açmak veya öğrenci silmek kazanım sayılmaz. Bodrumlara yangın merdiveni bağlantısı eklenmez. Daha önce açıkça sabitlenmiş sınıf rotaları ve beklemeler korunur.

Sarsıntı süresi hareket başlangıcını öteler. Tek başına süre değişikliği, aynı yerleşim ve rota koşullarında rota sıralamasını değiştirmek zorunda değildir. Bu girdiden otomatik bina hasarı veya merdiven güvenliği çıkarılmaz. Motor hareketi sarsıntı bittikten ve hazırlık tamamlandıktan sonra başlatır.

## “Uygun plan” nasıl seçiliyor?

Standart kapsam en fazla **48 seçenek × 4 ortak arama koşusu**; ardından aramada kullanılmayan **20 koşuyla** mevcut düzen ve arama adayı kontrol edilir. Hızlı kapsam 24×3 + 10 kontrol, ayrıntılı kapsam 96×6 + 30 kontroldür. Tek uygulanabilir rota gibi durumlarda benzersiz seçenek sayısı daha az olabilir.

Arama, farklı büyüklük/kat sıralarında yük dağıtımıyla başlar; rota ve izinli bekleme komşuluklarını sınırlı sayıda dener. Bütün olası planları taramaz. Sıralama puanı daha düşük olan seçenek daha iyidir:

| Hedef | Süre bileşeni | Ortalama bekleme | En yüksek bekleme talebinin koşular arası ortalaması |
|---|---:|---:|---:|
| Dengeli | %60 | %25 | %15 |
| Süre | %85 | %10 | %5 |
| Bekleme | %30 | %50 | %20 |

Süre bileşeni tamamlanan koşuların %95 süre eşiğidir. Bileşenler başlangıca göre ölçeklenir; sıfır beklemede de karşılaştırma tanımlı kalsın diye pay/paydaya 1 eklenir. Bu yüzden **hedef puanı yüzdesi, süre kazancı yüzdesi değildir**. Bekleme talebi fiziksel kalabalık basıncı veya güvenli yoğunluk sınırı değildir.

Bir adayın önerilmesi için bütün kontrol koşuları tamamlanmalı; mevcut düzen de tamamlanıyorsa hedef puanında en az %2 azalma ve kontrol koşularının en az %60'ında hedefte kazanım aranır. Bu eşikler bu prototipin tasarım tercihidir; bir mevzuat veya güvenlik standardı değildir. Mevcut düzen tamamlanmıyor, aday bütün kontrol koşularını tamamlıyorsa bu durum süre yüzdesi uydurulmadan ayrıca gösterilir.

Arama adayı kontrol aşamasında elenirse ikinci bir aday kontrol verisine bakılarak seçilmez. Mevcut düzen korunur veya tamamlanan plan bulunamadığı bildirilir. Böylece kontrol koşuları aramanın içine tekrar sokulmaz.

Süre farkı aynı koşu çiftlerinde hesaplanır; pozitif değer seçilen düzenin daha kısa sürdüğünü gösterir. Ortanca fark, iki ayrı ortancanın farkı değildir. %5–%95 eşikleri model değişkenliğidir; gerçek deprem için güven aralığı değildir.

## Gerçekten çalıştırılan denemeler

- **70 girdi, motor, 3B, optimizasyon ve arayüz testi geçti.** Kapalı yollar, sahaya erişim olmaması, bodrum yangın bağlantısı, aşırı arama isteği, zaman aşımı, eski önerinin gizlenmesi ve 3B'ye doğru planın aktarılması denetlendi.
- Yeni plan alanları boşken **7 tam motor çıktısı**, v0.3 motoruyla birebir eşleşti: ders/yemek/laboratuvar yerleşimlerinin bireysel/sınıfça halleri ve yangın rotası kapalı koşu.
- Örnek önerinin güncel JSON/USDA aktarımı `exports/school_evacuation_v04_optimized.*` içinde. USDA mevcut Blender 4.4.3 ile açıldı; 10 mimari kat ağı ve 111 öğrenci noktası korundu. Omniverse testi yapılmadı.
- Standart aramada ders, yemek ve yangın rotası kapalı başlangıç durumları değerlendirildi. Yeterli ve tutarlı kazanım çıkmayan durumlarda mevcut düzen korundu.
- Ayrı bir **örnek darboğaz** deneyinde başlangıç kuralı “En kısa model rotası” idi. 48 aday tarandı. 20 kontrol koşusunun tamamında seçilen taslak daha kısa sürdü; eşlenmiş ortanca fark yaklaşık **57,1 saniye**, ortanca süre kazancı **%24,8** oldu. Hedef puanı kazanımı yaklaşık %35'ti. Bunlar örnek model deneyidir; okulda ölçülmüş bir iyileşme değildir. Ayrıntı: `reports/optimizer_example_bottleneck_v04.json`.

## Dosya adı + başlık + ne değişti + neden

**planner.py**

`# =========================================================`

**SINIRLI PLAN ARAMASI VE AYRI KONTROL KOŞULARI:** Açık yollarda şube dağılımı, izinli ek bekleme, üç hedef, aday karşılaştırması ve kontrol aşaması eklendi. Neden: kullanıcı bütün düzenleri elle denemeden açıklanabilir bir model taslağı bulabilsin.

**engine.py**

`# =========================================================`

**İSTEĞE BAĞLI SINIF ROTASI VE EK BEKLEME:** Varsayılanı boş `class_routes` ve `class_delays` alanları eklendi. Kapalı/bağlantısız rotalar, bilinmeyen sınıflar, mükerrer atama ve geçersiz bekleme reddedilir. Neden: aramanın bulduğu şube planı aynı simülasyon motorunda çalışsın. Önceki boş plan davranışı birebir korundu.

**planning_ui.py / app.py / advanced_ui.py**

`# =========================================================`

**GİRDİ → ÖNERİ → GEREKÇE → 3B:** Ana ekranda koşullar, plan arama düğmesi, hedef seçimi, sınıf dağılımı, sonuç açıklaması ve mevcut/önerilen geçişi eklendi. Neden: TwinOps'taki gibi önce/sonra farkı anlaşılır olsun. Eski öneri yeni girdilerde uygulanmaz.

**test_planner.py / reports/validation_v04.json**

`# =========================================================`

**KISIT VE KAZANIM KONTROLÜ:** Kapalı rota, sabit fiziksel koşullar, ayrı kontrol tohumları, aşırı uyumda adayın reddi, sarsıntı zaman etkisi, sınıf bekleme sınırı ve arayüz aktarımı test edildi. Neden: tamamlanmayan veya koşulları değişmiş bir sonucu “daha iyi plan” diye sunmamak.

## Dokunmadığım çalışan dosyalar

TwinOps ve SchoolWatch'ın daha önce izlenen yedi dosyası korunur. Okulun `school_profile.json`, `scenarios.json`, `classes.csv`, `plan_layout.json`, bina geometrisi ve 11 kaynak plan fotoğrafı değiştirilmedi. Bu sürümde yalnız okul motoruna iki isteğe bağlı plan alanı ve ayrı arama/arayüz katmanı eklendi. Yeni paket kurulmadı.

## Geri dönüş noktası

Geliştirme öncesi sürüm: `../SchoolEvacuationPilot_pre_optimizer_20261020.zip`.

SHA256: `08a28f01e88fd6d22e86a54d26b2d8fa352028f692e8b17c92114cd89c35d793`.

Güncel sürüm: `../SchoolEvacuationPilot_v04_snapshot.zip`. Özel `runtime/` paylaşım paketine alınmaz. Varsa yerel oda/ölçüm kayıtlarının ayrı koruma kopyası `work/school_earthquake_20261019/pre_optimizer_user_inputs_backup/` içinde; bu kayıtlar otomatik öneriyle değiştirilmez.

## Kaynak ve uygulama sınırı

Çıktı okul yönetimi ve ilgili uzmanların inceleyeceği **simülasyon taslağıdır**. Oda eşleştirmeleri, fiziksel bağlantılar, ölçüler, toplanma alanı ve gerçek tatbikat doğrulaması hâlâ eksiktir. Bu sürüm canlı bir depremde otomatik yönlendirme sistemi değildir. Yoklama, yetişkinler, hasar, düşme ve kalabalık basıncı hesaplanmaz.

[NIST TN 1822](https://www.nist.gov/publications/process-verification-and-validation-building-fire-evacuation-models), tahliye modelinin hazırlık, hareket, çıkış kullanımı, rota kullanılabilirliği ve akış kısıtlarıyla birlikte doğrulanmasını ve davranış belirsizliğinin incelenmesini ele alır; bu çalışmanın okula ait doğrulaması değildir. [AFAD okul tatbikatı örneği](https://kirsehir.afad.gov.tr/deprem-ani-ve-tahliye-tatbikati-gerceklestirildi), sarsıntı sonrasında görevlilerle tahliye ve toplanma/yoklama ayrımını gösterir. Arama puanları ve kabul eşikleri bu kaynaklardan alınmış resmi kurallar değildir.

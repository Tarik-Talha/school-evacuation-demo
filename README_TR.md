# Şerifali okul deprem ve tahliye senaryoları

20 Ekim 2026 · Güncel sürüm **v0.7** · yalnızca 111 öğrenci.

**v0.7 dış ekip varış referansı:** [v0.7 rehberi](V07_DIS_MUDAHALE_TR.md). Her tahliye koşusunda ambulans ve itfaiye için İBB'nin İstanbul geneli 2024 ortalamalarına dayalı örnek varış zamanı gösterilir. Bunlar okul adresine özel rota tahmini değildir; bildirim gecikmesi kullanıcı girdisidir ve deprem sonrası trafik/yol kapanması henüz hesaba katılmaz.

**v0.6 teneffüs modeli:** [v0.6 rehberi](V06_TENEFUS_MODEL_REHBERI_TR.md). Öğrenciler 2–3 kişilik arkadaş gruplarıyla derslik, laboratuvar, yemekhane, kat ortak alanları ve bahçeye rastgele yerleşir. Aynı yerleşim numarası karşılaştırmalarda korunur. Oda ve kapı geometrileri plandan yorumdur; konumlar gözlem verisi değildir. v0.6 için tam test paketi çalıştırılmadı; elle yapılan model ve 3B kontrolünde 111 öğrenci hesaplandı.

**v0.4 plan araması:** [v0.4 planlama rehberi](V04_PLANLAMA_REHBERI_TR.md). v0.4 kapsamındaki 70 test geçti; bu sonuç yeni v0.6 oda yerleşimine ait test sonucu değildir. Çıktı okulda doğrulama/onay bekleyen simülasyon taslağıdır.

**3B ana ekran, odalarda ayrı öğrenci yerleşimi, oynat/duraklat ve sayfa kaydırma:** [v0.3 görsel rehberi](V03_GORSEL_REHBER_TR.md). Yeni oda geometrisi planlardan yorumlandı; fiziksel ölçü ve oda eşleştirmesi doğrulanmış değildir. 55 test geçti. Önceki rehberler aşağıda tarihsel kayıt olarak korunur.

**Güncel kullanım, değişiklikler ve geri dönüş:** [v0.2 geliştirme rehberi](V02_GELISTIRME_REHBERI_TR.md). Kat planı animasyonu, çoklu denemeler, akış düzenleri, tatbikat/ölçü girişi ve 3B/USD/Blender çıktısı hazır. **47 test geçti.** Gerçek okul ölçüleri ve tatbikatla kalibrasyon henüz tamamlanmadı. Aşağıdaki ilk veri incelemesi ve v0.1 açıklamaları tarihsel kayıt olarak korunur; güncel özellik kapsamı v0.2 rehberindedir.

Bu paket artık ayrı bir yerel simülasyon ekranı ve kapasite kısıtlı öğrenci akış motoru içerir. Ders, toplu öğle yemeği ve örnek laboratuvar yerleşimi çalışır. Geometri ve davranış katsayıları ölçülmemiş örneklerdir: hesaplanan süreler okulda doğrulanmış tahliye süreleri değildir. Bina hasarı ve can kaybı sonucu üretilmez.

Doğrulama: 25 girdi/motor/arayüz testi geçti. 11 senaryo tanımı korunur; başlangıç konumu bilinen üç yerleşim simüle edilir. Gerçek ölçülmüş tahliye hazırlığı hâlâ `false`; girdi doğrulama raporunun süre alanı `null` kalır. Örnek motor koşuları ve ayarları ayrı sonuçlar olarak tutulur.

[Simülasyonu aç](http://127.0.0.1:8532/) · [Kullanım ve model rehberi](SIMULASYON_REHBERI_TR.md). Yeniden başlatmak için `start_school_pilot.vbs` dosyasına çift tıklanabilir. Mevcut yerel Python ortamı kullanılır; yeni paket yüklenmedi.

## Doğrulanmış kullanıcı girdileri

| Kat | Şubeler | Öğrenci |
|---|---|---:|
| 1 | 6A: 12, 8A: 10 | 22 |
| 2 | 5A: 2, 7A: 8 | 10 |
| 3 | 9A: 13, 10A: 20, 11A: 11 | 44 |
| 4 | 11B: 13, 12A: 20, 12B: 2 | 35 |
| **Toplam** | **10 şube** | **111** |

Öğrencilerin 77'si (%69,4) 3–4. katlarda. Bu bir başlangıç nüfus dağılımıdır; kendiliğinden tahliye önceliği belirlemez. 5–6. katlara ayrıca öğrenci eklenmez; laboratuvar ziyareti mevcut öğrencilerin konumunu değiştirir.

Ders aralığı 09.00–16.10; yemek aralığı 12.00–13.00. Öğrenciler yemekhaneye birlikte gidiyor. Kütüphane ziyareti kullanıcının isteğiyle kapalı. 30 öğretmen kadro bilgisi olarak saklandı; öğretmen, diğer personel ve ziyaretçiler bu modelin nüfusuna dahil değil. Bu kapsam gerçek binanın ortak güzergâh yükünü olduğundan düşük gösterebilir.

Kullanıcı yangın merdivenlerinin açık olduğunu bildirdi. Bahçedeki sahayı önerdi; okulun belirlenmiş toplanma alanı olmadığını söyledi. Bu iki bilgi güncel kullanıcı beyanıdır; saha geometrisi ve güzergâh incelemesi yerine geçmez.

## Planlardan çıkan ayrıntılar

ZIP içindeki 11 görsel: bahçe, 2. bodrum, 1. bodrum, zemin, asma ve 1–6. normal katlar. Fotoğraflarda 21.08.2020 tarihi okunuyor. Bu tarih yapım tarihi veya deprem performansı belgesi kabul edilmedi. ZIP'te haftalık ders programı/zil çizelgesi bulunmuyor.

Yemek salonu 1. bodrumda (P03); çok amaçlı salon 2. bodrumda (P02). 5. katta laboratuvar ve kütüphane (P10), 6. katta derslikler (P11) var. Laboratuvar etiketi 2. bodrum planında da görünüyor: gerçek dersin hangi laboratuvarda olduğu doğrulanmalı. Kullanıcı sınıf adları plandaki derslik numaralarıyla henüz eşleştirilmedi.

Üst kat çizimlerinde iki iç merdiven konumu ve yangın merdiveni görülüyor. Üç ayrı, kesintisiz ve güvenli çıkış doğrulanmış sayılmadı; net genişlik, bağlantılar ve dışarıda sonlandıkları yer eksik. Asansörler tahliye ağına alınmayacak.

Bahçe planındaki 472,12 m² toplam bahçe etiketi ile ayrı 410,00 m² etiketi otomatik toplanmadı. Bunların sahayla ilişkisi, net güvenli alanı ve cephe mesafeleri bilinmiyor; kişi kapasitesi hesaplanmadı.

## Senaryo seti

| Kimlik | Durum | Karşılaştırılacak konu |
|---|---|---|
| S01 | Ders sırasında | Katların merdiven ve kapılarda birleşmesi |
| S02 | Toplu öğle yemeği | 111 öğrencinin 1. bodrumdan yukarı çıkışı |
| S03 | Teneffüs | 2–3 kişilik grupların derslik, laboratuvar, yemekhane, ortak alan ve bahçedeki örnek başlangıçları |
| S04 | Tek merdiven/çıkış kapalı | Alternatif rota, erişilemeyen öğrenciler |
| S05 | Elektrik/anons kesintisi | Yönelme gecikmesi ve acil aydınlatma |
| S06 | Hareket desteği | Mevcut öğrenci ve onaylı refakat düzeni |
| S07 | Bahçeye/sahaya erişim kapalı | Alternatif dış güzergâh ve alan |
| S08 | Laboratuvar dersi | Mevcut bir şubenin başka kata taşınması |
| S09 | Yemekhaneye geçiş | Öğrenciler henüz merdivenlerdeyken deprem |
| S10 | 16.10 çıkışı | Bina dışına çıkış ile yoklamanın ayrılması |
| S11 | Tahliye sırasında artçı | Onaylı prosedüre göre kesinti/yeniden kontrol |

S08'deki 10A→5. kat yalnızca açıkça etiketlenmiş örnektir; gerçek ders ataması değildir. 20 kişi 3. kattan çıkarılır, 5. kata konur; toplam yine 111'dir. v0.6 teneffüs konumlarını rastgele senaryo girdisi olarak üretir; bu, okulda gözlenmiş dağılım değildir. Öğle yemeği başlangıç anıyla yemekhaneye varılmış an farklıdır.

Ortak akış: sarsıntı sırasında korunma → sarsıntı sonrasında onaylı prosedürle yönelme → kapı/koridor/merdiven → dış çıkış → uygunluğu doğrulanmış saha → sınıf bazında yoklama. Bu ayrım [AFAD'ın deprem önlemleri](https://afad.gov.tr/deprem-oncesi-ani-ve-sonrasi-alabileceginiz-onlemleri-biliyor-musunuz) ve [AFAD okul tatbikatı](https://www.youtube.com/watch?v=PfWAs10H9o0) ile uyumludur. Sarsıntı sürerken merdivene koşma, asansör veya otomatik “önce üst katlar” kuralı eklenmez. Kullanılabilir rotası olmayan kişi tahliye edilmiş sayılmaz.

## Konum nasıl kullanılacak?

Adres: Şerifali, Kızkalesi Sk. No:19, Ümraniye/İstanbul. Kullanıcının Google Maps bağlantısı okunamadı. [Adres eşleşmesindeki](https://yandex.com.tr/maps/115705/umraniye/house/kizkalesi_sok_no_19/ZkAYdwNiQUYOQFpqfXV4d3VlZQ%3D%3D/inside/) 40.996961, 29.142839 koordinatı yalnız geçici konum referansıdır; bina girişi/parsel doğrulanmadı, mesafe veya ivme hesaplarında kullanılmadı.

Konum; bahçe kapısı, sokağa çıkış, komşu cepheler, araçlar ve alternatif saha rotası incelenirken kullanılacak. [İBB ilçe çalışması](https://depremzemin.ibb.istanbul/tr/olasi-deprem-kayip-tahminleri-ilce-kitapciklari) bölgesel Mw 7,5 senaryosu sunar ve tekil bina performansı vermediğini belirtir. Bu büyüklük deprem tarihi/tahmini veya okula ait ivme değildir. Ümraniye PDF bağlantısı belirlendi ancak dosya büyüklüğü nedeniyle içeriği bu çalışmada okunamadı.

[AFAD harita açıklaması](https://tdth.afad.gov.tr/TDTH/loginControl.xhtml) yerel zemin etkilerini ayrıca ayırır. Okul için zemin sınıfı, yer hareketi, taşıyıcı sistem performansı veya hasar olasılığı atanmadı. Bahçedeki saha okul önerisidir; ayrıca [resmi toplanma alanı sorgusu](https://www.turkiye.gov.tr/afet-ve-acil-durum-yonetimi-acil-toplanma-alani-sorgulama) kullanılabilir, fakat okulun dış rotası yine sahada kontrol edilmelidir.

## Sonraki uygulama adımı ve başarı ölçütü

Önce 10 şube plan odalarıyla eşleştirilecek; merdiven, koridor ve kapıların net ölçüleri alınacak; çıkıştan sahaya kesintisiz rota çizilecek. `saha_olcum_listesi.csv` bu iş için hazır. Daha net plan/PDF veya sahada ölçümle yapılmalı; eğik fotoğraf piksellerinden metre türetilmedi.

İlk motor her öğrenciyi aynı anda tek konumda tutar; kapasite kısıtlı bağlantılarda kuyruk ve kat birleşimlerini örnek ağda hesaplar. S01, S02 ve örnek S08 başlangıç konumları çalışır. Merdiven/saha geçişi kapanması ekrandan denenebilir. Üç bağımsız güzergâh ve ortak saha geçişi henüz doğrulanmış bina ağı değildir. Ölçümler geldikçe bu örnek bağlantılar gerçek ağ ile değiştirilecek. Okulun onaylayacağı düzenler ayrıca aynı başlangıç koşullarıyla karşılaştırılacak.

v0.1 çıktıları: örnek ağda sarsıntı sonundan son dış çıkışa ve önerilen sahaya varışa süre, geçiş beklemeleri, sahaya ulaşamayan öğrenciler ve aynı yerleşimde referansa göre fark. Yoklama bitişi ve fiziksel yoğunluk ısı haritası hesaplanmaz. Gerçek tatbikat süreleriyle kalibrasyon ve birden fazla koşudan belirsizlik aralığı sonraki aşamadır. Örnek süre değişimleri doğrulanmış güvenlik kazanımı değildir.

## Dosya rehberi

`# =========================================================`

**school_profile.json — OKUL GİRDİLERİ VE KAPSAM:** 111 öğrenci, katlar, saatler, güncel kullanıcı yanıtları ve eksik alanlar. Neden: doğrulanmış bilgi ile varsayımları ayırmak.

`# =========================================================`

**scenarios.json — DURUMA GÖRE KONUMLAR:** 11 senaryo ve hareket tanımı. Neden: yemek/laboratuvar geçişinde aynı öğrenciyi ikinci kez saymamak.

`# =========================================================`

**source_manifest.json — PLAN KAYNAKLARI:** 11 görselin adları, SHA256 özetleri ve görsel gözlemleri. Neden: her plan bulgusunu kaynağına izleyebilmek. Orijinaller yerel `work/` altında tutulur.

`# =========================================================`

**classes.csv / saha_olcum_listesi.csv:** Şube nüfusu ve doldurulacak ölçüm tablosu. Neden: veri girişi ve sahadaki eksikleri görünür kılmak.

`# =========================================================`

**validate.py / test_inputs.py / validation_report.json:** Nüfusun korunması, geçersiz şube/katın reddi, öğrenciler dışındaki kişilerin kapsam dışı kalması. Neden: tanımlanmamış konum ve süreleri sahte sonuçla doldurmamak. Bu testler fiziksel tahliye doğrulaması değildir.

## Dokunmadığım çalışan dosyalar

TwinOps ve SchoolWatch uygulama, motor, optimizer, Blender/USD ve kamera dosyalarına değişiklik yapılmadı; bu paket `outputs/SchoolEvacuationPilot/` altında bağımsızdır. Mevcut önizleme bir okul tahliye ekranına dönüştürülmedi.

## Geri dönüş noktası

Motor eklenmeden önceki 10 dosyanın kopyası `outputs/SchoolEvacuationPilot_pre_simulation_20261019.zip` içinde. Paketin sunucusu ayrı 8532 portundadır. Orijinal ZIP Downloads altında aynen durur; açılmış kopyası `work/school_earthquake_20261019/source_images/` içindedir. TwinOps ve SchoolWatch'ta geri alınacak kod değişikliği yoktur.

# School Evacuation Pilot v0.1

Bu dosya v0.1 davranışının tarihsel rehberidir. Güncel v0.2 özellikleri, 47 kontrol ve 3B/Blender çıktıları için [v0.2 geliştirme rehberini](V02_GELISTIRME_REHBERI_TR.md) kullanın.

19 Ekim 2026 · 111 öğrenci · yerel senaryo atölyesi.

## Kullanım

1. [Ekranı aç](http://127.0.0.1:8532/). Sunucu kapalıysa bu klasördeki `start_school_pilot.vbs` dosyasına çift tıkla. Görünür komut penceresi açmaz. 8532 doluysa başka uygulamayı kapatmaz; bu projeyi doğrulamadan kullanmaz.
2. Soldan ders, öğle yemeği veya örnek laboratuvar yerleşimini seç. Öğle yerleşiminde 111 öğrenci B1'deki tek yemek salonu kapısını paylaşır. Laboratuvarda seçilen şubenin mevcut öğrencileri taşınır.
3. Merdivenleri/saha geçişini kapatıp aç. Ölçülmemiş genişlik, uzunluk ve hızları ayrı bölümden değiştir. Ayarlar değişince hesap otomatik yenilenir.
4. **Öğrenci akışı** sekmesindeki **Oynat** düğmesine bas; zaman çizgisini de sürükleyebilirsin. Şema gerçek kat planının ölçülü çizimi değildir. Gri korunma/hazırlık, mavi ilerleme, sarı bekleme, yeşil sahaya varış, kırmızı rota yok, mor dışarıda ancak sahaya ulaşamamadır.
5. **Referans ile karşılaştır** sekmesinde aynı yerleşimin başlangıç ayarlarını seçili koşuyla kıyasla. Referans ölçülmüş okul performansı değildir. Koşu ve varsayımları JSON olarak indirebilirsin.
6. **Veriler ve varsayımlar** sekmesinden sayıları, model kabullerini ve kaynak plan fotoğrafını incele.

## Sonucu nasıl okumalı?

Üstteki varış süresi sarsıntının bitişinden son öğrencinin önerilen sahaya varışına kadardır; hazırlık ve yolculuk dahildir. Animasyon saati ise deprem başlangıcından başlar. Örneğin örnek sarsıntı 20 sn ve gösterilen varış 128 sn ise animasyon yaklaşık 148 sn'de biter. Bunlar örnek ayarların çıktılarıdır.

“Dışarı çıktı” ile “sahaya ulaştı” ayrı sayılır. Saha geçişini kapatınca öğrenciler bina dışına çıkabilir ama sahaya varmış sayılmaz; tüm öğrencilere ait varış süresi ve iyileşme yüzdesi verilmez. Tüm merdivenler kapalıysa erişilemeyen öğrenciler kaybolmaz. Süre sınırına takılanlar da başarı olarak sayılmaz.

Bekleme tablosu, her geçişin toplam kişi·saniye beklemesini ve eşzamanlı en yüksek bekleme talebini gösterir. Bu sayı metre cinsinden kuyruk uzunluğu veya güvenli kalabalık yoğunluğu değildir. Sonraki geçiş doluyken öğrenci önceki geçişin yerini tutar; bu durum geriye doğru akışı yavaşlatabilir.

Dağıtılmış akış, mevcut güzergâhlara nominal seyahat ve atanan kişi yüküne göre öğrenci paylaştırır. En kısa rota seçeneği nominal yol süresini kullanır. Bunlar gerçek öğrencilerin davranışı veya onaylı tahliye talimatı değildir; ileri seviye optimizer de değildir.

## Hangi bilgiler örnek?

Üç bağımsız güzergâh, ortak saha geçişi, oda–merdiven bağlantıları, bütün mesafeler/genişlikler ve hız/akış katsayıları örnektir. Varsayılan 1,1 m merdiven, 0,5 m/sn merdiven hızı gibi değerler okulda ölçülmedi ve standart zorunluluğu olarak sunulmaz. Asma kat ayrı bağlantıdır. Bodrumdan yangın merdivenine belgelenmemiş bağlantı eklenmez; bodrum için yalnız iki varsayımsal iç güzergâh vardır.

Geçişte yer sayısı = uzunluk × genişlik × örnek depolama katsayısının aşağı yuvarlanmış değeri, en az 1. Kabul aralığı = 1 / (genişlik × örnek akış katsayısı). Yolculuk süresi = yol uzunluğu / hız. Giriş sırası FIFO'dur. Bu, sonlu kapasiteli bir ağ modelidir; beden çarpışması, düşme, kalabalık basıncı veya hasar fiziği çözmez. Gerçek öğrenci hareketini tatbikatla doğrulamak gerekir. [NIST araştırması](https://www.nist.gov/publications/movement-stairs-during-building-evacuations) de merdiven hareketinin geometri, insan ve koşullara göre değiştiğini gösterir; buradaki örnek katsayılar o veriyle okula kalibre edilmedi.

Öğretmen ve personel, kütüphane ziyareti, yoklama süresi, gerçek teneffüs/öğle geçiş konumları ve artçı davranışı kapsam dışı. Mevcut 11 senaryo tanımından yalnız başlangıç konumu belli üç yerleşim çalışır. Saha, uygunluğu henüz doğrulanmamış kullanıcı önerisidir. Deprem dayanımı, hasar, yaralanma veya can kaybı hesaplanmaz.

## Dosya adı + kod başlığı + değişiklik + neden

`# =========================================================`

**engine.py — EDITABLE EXAMPLE ASSUMPTIONS, NEVER MEASURED GEOMETRY:** Ayarlar ve doğrulama. Neden: örnek değeri gerçek ölçüyle karıştırmadan değiştirebilmek.

`# =========================================================`

**engine.py — SHARED STAIR SEGMENTS, INTERMEDIATE MEZZANINE AND FIELD GATE:** Paylaşılan kat bağlantıları ve saha geçişi. Neden: her sınıfa ayrı, sınırsız merdiven verip kuyruğu yok etmemek.

`# =========================================================`

**engine.py — FIFO ADMISSION, FINITE STORAGE AND UPSTREAM BACKPRESSURE:** Öğrenci süreçleri, kapasite ve bekleme. Neden: dolu geçişin arkasındaki akışı tutması ve erişilemeyenlerin korunması.

`# =========================================================`

**app.py — SCENARIO CONTROLS AND EXPLICIT UNMEASURED ASSUMPTIONS / EXPLAINABLE RESULTS AND PAIRED MODEL COMPARISON:** Türkçe ayarlar, anlaşılır sonuç ve eşlenmiş karşılaştırma. Neden: kullanıcı neyi değiştirdiğini ve sonucun hangi kabullere dayandığını görsün.

`# =========================================================`

**visuals.py — SCHEMATIC STUDENT PLAYBACK, NOT A MEASURED FLOOR PLAN:** Oynat/duraklat ve zaman çizgisi. Neden: akışı yalnız bir süre rakamı olarak sunmamak.

`# =========================================================`

**launch.py — PROJECT IDENTITY AND HIDDEN LOCAL SERVER:** Ayrı port ve kimlik kontrolü; **start_school_pilot.vbs** görünmez başlatma. Neden: önceki uygulamaları kapatmadan yeniden açabilmek.

**test_engine.py:** Analitik tek öğrenci hesabı, kapalı rotalar, ortak kapı, nüfus, kapasite, tekrar üretilebilirlik ve iki arayüz testi. **.streamlit/config.toml:** Okunaklı yerel tema; **.gitignore:** çalışma günlükleri dışarıda.

Çalışma alanı kökündeki **.gitignore — LOCAL SCHOOL SIMULATION RECOVERY SNAPSHOTS** başlığına iki yedek ZIP kalıbı eklendi. Neden: yerel geri dönüş kopyaları yanlışlıkla Git'e alınmasın. Önceki kök dosyanın kopyası `work/school_earthquake_20261019/pre_simulation_root.gitignore` içinde.

## Dokunmadığım çalışan dosyalar

TwinOps'un app/engine/optimizer/USD ve tekstil ekranı ile SchoolWatch'un app/kamera dosyaları. Yedi temsilci dosyanın başlangıç ve bitiş SHA256 özetleri karşılaştırılır. Yeni bağımlılık yüklenmedi; mevcut `work/ft06_runtime` yalnız çalıştırmak için kullanıldı.

## Geri dönüş noktası

Motor öncesi paket: `outputs/SchoolEvacuationPilot_pre_simulation_20261019.zip`. Sunucu ayrı 8532 portunda; eski TwinOps 8514 adresi değiştirilmedi. Bu klasörün yedeği eski projelerin dosyalarını içermez veya onların üzerine yazılmaz.

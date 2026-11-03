# Teneffüs senaryosu · v0.6

`# =========================================================`

**Amaç:** Deprem teneffüs ortasında olursa 111 öğrenciyi sınıflara bağlı kalmadan, okulun farklı öğrenci kullanım alanlarında modellemek. Bu bir varsayımsal dağılımdır; kamera, yoklama, okul gözlemi veya gerçek teneffüs verisi değildir.

## Nasıl kullanılır?

1. Uygulamada **Deprem hangi anda? → Teneffüs** seç.
2. **Teneffüs yerleşim numarası**nı değiştirerek farklı rastgele dağılımlar gör. “Yeni teneffüs dağılımı oluştur” numarayı bir artırır.
3. Aynı numara aynı öğrenci gruplarını ve başlangıç yerlerini üretir. Plan araması ve karşılaştırma senaryoları yerleşimi sabit tutar; böylece değişen şeyin yerleşim değil rota/akış ayarı olduğu görülebilir.
4. 3B okul görünümünde tüm katları ve bahçeyi birlikte izle. Oynatıcı her öğrenciyi bir nokta olarak gösterir. Kat görünümüne geçince yalnız seçilen kattakiler görünür.

## Model ne yapıyor?

Her şubenin mevcut öğrenci kimlikleri korunur ve aynı şubeden 2–3 kişilik arkadaş gruplarına ayrılır. Varsayılan 111 öğrenci için bu 46 gruptur. Gruplar 2. bodrumdan 6. kata kadar bütün modellenen katlara ve bahçeye dengeli biçimde dağıtılır; her katta uygun rastgele alan seçilir. Örnek 42 numaralı yerleşimde 18 grup derslik/lab/yemekhanede, 24 grup koridor ortak alanlarında, 4 grup bahçededir. Başka numara farklı yerler üretir.

Bir grup oda içindeyse, örnek ağda odadan kapısına, oradan kat koridoruna çıkar. Aynı odaya birden fazla grup düşerse kapı kapasitesini paylaşırlar. Ortak alanda başlayanlar koridora bağlanır. Bahçede başlayanlar merdiven kullanmadan saha geçişine yönelir. Öğrenciler 2–3 kişilik birim olarak aynı başlangıç, rota ve örnek tempoyu kullanır.

## Yerleşimin sınırları

- Oda şekilleri, kapılar ve ortak alan parçaları okul planı fotoğraflarından yorumlanmıştır; ölçülmüş mimari çizim değildir.
- Yerler rastgele oluşturulur; gerçek teneffüs dağılımı, ders programı veya sınıf bazında gözetim verisi olarak sunulmaz. Katlara dağılım dengeli tutulur; gerçek hayattaki kalabalık yoğunluğunu tahmin etmez.
- Sınıflar, lablar, yemekhane, seçili koridor/ortak alanlar ve önerilen bahçe alanı kapsanır. Kullanıcının önceki tercihine uygun olarak kütüphane kapalıdır; WC, merdiven boşluğu ve servis/teknik odalara yerleşim yapılmaz.
- Oda kapasitesi, masa/sıra kullanımı, odadaki grup aralıklarının gerçek hayatta uygulanabilirliği, personel/ziyaretçi, refakat ihtiyacı, yoklama, yaralanma ve bina hasarı hesaplanmaz.
- Saha ve güzergâhın uygunluğu okul tarafından doğrulanmış değildir. Ekrandaki süre veya öneriler acil durum talimatı ya da güvenlik onayı değildir.

## Dosya rehberi

`# =========================================================`

**app.py — TENEFFÜS KONTROLLERİ:** Yerleşim numarası, yeni dağılım düğmesi ve açık kapsam metni. Neden: varsayımı kullanıcıya görünür kılmak ve karşılaştırmaların aynı başlangıçla yapılmasını sağlamak.

`# =========================================================`

**recess.py — GRUPLAR VE RASTGELE YERLER:** 2–3 kişilik şube içi gruplar; oda, ortak alan ve bahçe koordinatları; sabit seed ve yerleşim özeti. Neden: teneffüs başlangıcını ayrı, tekrarlanabilir bir adaptörde tutmak.

`# =========================================================`

**engine.py — ODA KAPILARI VE AKIŞ:** Teneffüs grupları için odaya özgü bağlantı ve aynı odadaki gruplar için paylaşılan kapı kapasitesi. Neden: rastgele oda başlangıcını yalnız 3B görsele değil, tahliye hesabına da katmak.

`# =========================================================`

**building_geometry.py / spatial.py / school_scene.py / advanced_ui.py — PLAN VE 3B:** Öğrenci noktalarını odalara taşır, oda kapısından koridora animasyonla çıkarır ve teneffüs açıklamalarını gösterir. Neden: ekrandaki başlangıç konumuyla motorun kullandığı konum aynı kalsın.

`# =========================================================`

**planner.py / planning_ui.py / experiments.py — AYNI YERLEŞİMLE KARŞILAŞTIRMA:** Plan araması arkadaş gruplarını birim alır; başlangıç yerleşimini stratejiler ve kontrol koşuları boyunca sabitler. Neden: farklı rastgele dağılımların rota ayarlarına etkisini karıştırmamak.

## Dokunmadığım çalışan dosyalar

TwinOps uygulama ve simülasyon dosyalarına, Blender köprüsüne ve SchoolWatch kamera projesine dokunulmadı. Bu değişiklikler yalnız `outputs/SchoolEvacuationPilot/` içindeki okul pilotunda yapıldı. Önceki ders/yemek/lab davranışları için tam test paketi bu sürümde yeniden çalıştırılmadı.

## Geri dönüş noktası

Oda içi yerleşim eklenmeden önceki teneffüs sürümü `outputs/SchoolEvacuationPilot_pre_recess_rooms_20261020.zip` içinde; SHA256 özeti yanındaki `.sha256` dosyasında. Teneffüs eklenmeden önceki v0.4 sürümü `outputs/SchoolEvacuationPilot_pre_recess_20261020.zip` içinde. İki arşiv de yerel geri dönüş içindir, uygulamanın çalışma klasörü değildir.

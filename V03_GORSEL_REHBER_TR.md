# v0.3 — okul planlarına göre 3B ana ekran

20 Ekim 2026 · [Önizlemeyi aç](http://127.0.0.1:8532/)

Ana görünüm artık **3B okul**. Ders yerleşiminde ilk açılış 3. kattadır: 9A, 10A ve 11A'nın 44 öğrencisi kendi oda alanları içinde ayrı konumlarda görünür. Okulun tamamında toplam 111 öğrenci vardır. Model ilk açılışta **0 saniyede ve duraklatılmış** durumdadır. Sarsıntı boyunca öğrenci konumları değişmez; sonrasında mevcut motorun hazırlık ve hareket zamanları kullanılır.

## Kullanım

- **Katı incele:** Dersliği, sıraları, kapıları ve koridor bağlantılarını yakından gör. İncelenen katı değiştirmek öğrenci sayısını değiştirmez. Alttaki “bu görünümde” sayacı yalnız çizilen öğrencileri, durum sayaçları tüm 111 öğrenciyi kapsar.
- **Okulun tamamı:** Katları birlikte göster. **Katları ayır:** İç mekânları daha rahat görebilmek için katları görsel olarak arala. Bu aralık fiziksel kat yüksekliği değildir.
- **Oynat / Duraklat / Başa al:** 3B sahnede akışı çalıştır, dondur veya öğrencileri ilk odalarına döndür. Zaman çubuğuyla istenen ana git; 0,5× / 1× / 2× görsel oynatma hızını değiştir. Oynatma hızı hesaplanan tahliye süresini değiştirmez.
- **Çapraz / Üstten / Önden:** Hazır kamera açıları. **+ / −:** Sınırlı yakınlık değişimi; sahnede kaybolmayı azaltır. **Fareyle döndür:** İstenirse sol tuş sürüklemesini aç. Başlangıçta kapalıdır.
- **Fare tekerleği:** İmleç 3B sahnedeyken de sayfayı kaydırır. Kamera yakınlığı tekerleğe bağlanmaz; döndürme açıkken de sayfa kaydırılır.
- **Model güzergâhlarını göster:** Yollar varsayılan olarak gizlidir. Odalar daha rahat okunur; gerekirse model yolları açılır.
- Sonuç kartları ve eski şema **Akış ve sonuçlar** sekmesinde. Çoklu deneme, düzen karşılaştırması ve tatbikat girişleri korunmuştur.

Yemek yerleşimi seçilirse öğrenciler B1'deki yemekhanede; laboratuvar yerleşiminde ilgili şube seçilen laboratuvarda başlar. Öğle yemeğinde yeni öğrenci eklenmez; merdiven alanlarına masa/öğrenci yerleştirilmez.

## Planlara uygunluk ve sınırı

P02–P11 kaynak planları yeniden incelenerek kat çevresi, dersliklerin genel bölünmesi, ortak alanlar, iki iç merdiven ve üst kat yangın merdiveni kolu yorumlandı. Derslikler artık boş kat çerçevelerinin içinde üst üste noktalarla temsil edilmiyor; odalar, kapı açıklıkları, sıralar ve öğrenci konumları var. Fotoğrafların eğimi ve farklı kadrajları ortak görsel oranlarla sadeleştirildi.

Bu model **ölçülü mimari çizim değildir**. Duvar yüksekliği, oranlar, mobilyalar, bazı destek alanı bölmeleri ve dış yollar görsel yorumdur. Cephe fotoğrafı/verisi bulunmadığından gerçek cephe benzerliği iddia edilmez. Şube–oda atamaları ayrı formda hâlâ doğrulanmayı bekler. Motorun fiziksel uzunluk/genişlikleri fotoğraftan türetilmez; hesaplanan süreler yeni görsel ölçüye göre değiştirilmedi. Birebir mimari eşleşme için oda doğrulaması ve ölçülü plan gerekir.

Bahçe/saha ve dış çıkışlar önceki örnek ağın görsel karşılığıdır; okul tarafından onaylanmış güzergâh sayılmaz. Kamera/animasyon değişiklikleri güvenlik performansı doğrulaması değildir. Öğretmen/personel kapsam dışı kalır.

## Dosya adı + başlık + değişiklik + neden

**building_geometry.json / building_geometry.py**

`# =========================================================`

**PLAN YORUMU VE ODA İÇİ YERLEŞİM:** On kat için oda/kat çevreleri, merdiven alanları ve kapılar eklendi. Şubeye ait öğrenciler kendi oda poligonunun içinde ayrı konumlara yerleşir. Neden: okulun genel yerleşimini görünür kılmak ve başlangıçta üst üste duran öğrencileri ayırmak.

**school_scene.py**

`# =========================================================`

**3B OKUL VE SAYFA DOSTU OYNATICI:** Duvar, sınıf, sıra, merdiven, kat kesiti, kamera seçenekleri, canlı sayaçlar ve 3B oynatma eklendi. Tekerlek sayfa kaydırıcısına iletilir; yakınlık düğmelerle sınırlandırılır. Neden: sahneyi ana çalışma alanı yapmak ve sayfa kontrolünü korumak. İnternet üzerinden betik/veri indirilmez.

**spatial.py / scene_export.py**

`# =========================================================`

**AYNI KOŞUNUN ODA VE YOL KONUMU:** Oda içi başlangıçlar, kapı/koridor görsel yolları, kat geçişleri ve bina dışından geçen saha yolları işlendi. JSON/USDA aynı konumları ve yorumlanmış bina geometrisini taşır. Neden: 3B ekranda ve aktarılan koşuda öğrenci kimliklerini korumak. Kaynak motor olay zamanları değiştirilmez.

**app.py / advanced_ui.py**

`# =========================================================`

**3B ÖNCELİKLİ ARAYÜZ:** 3B okul ilk sekmeye alındı; sonuç kartları ayrı sekmeye taşındı. Başlık/panel daraltıldı, sahne küçük panele uyarlanır. Neden: kullanıcı önce okulu ve öğrencileri görsün, sayfayı daha rahat kullansın.

**test_scene.py / reports/validation_v03.json**

`# =========================================================`

**ODA, NÜFUS VE GÖRSEL YOL KONTROLÜ:** 55 testlik set; oda içinde ve ayrı başlangıç konumları, sarsıntıda sabitlik, yemek/laboratuvar yerleşimi, kat kesitinde nüfus, içbükey kat alanı, dış yol ve ana ekran kontrollerini içerir. Önceki girdi/motor/arayüz testleri korunur. Güncel USDA Blender 4.4.3 ile açıldı: 10 mimari kat ağı, 290 yüz ve 111 öğrenci noktası. Omniverse çalıştırılmadı.

## Dokunmadığım çalışan dosyalar

Okulun **engine.py** hesap motoru değiştirilmedi. `school_profile.json`, `scenarios.json`, `classes.csv`, orijinal `plan_layout.json` ve 11 kaynak fotoğrafı korundu. Yeni oda geometrisi ayrı dosyadadır. TwinOps ve SchoolWatch'ın daha önce izlenen yedi çalışan dosyası değişmedi. Yeni paket kurulmadı; başka sunucular kapatılmadı.

## Geri dönüş noktası

Geliştirme öncesi kopya: `../SchoolEvacuationPilot_pre_v03_20261020.zip`.

SHA256: `dd1a937192294bbc102dfdacd5d2c2f0f8475d6b2fc7c8aba7820f57946a9f34`.

Tamamlanan sürüm kopyası: `../SchoolEvacuationPilot_v03_snapshot.zip`. Özel `runtime/`, önbellekler ve `.blend1` dosyaları pakete alınmaz. Ham fotoğraflar yerel kaynak klasöründe korunur. Hazır v0.2 `.blend` eski sürümün arşividir; güncel görsel geometri `school_evacuation_v03.usda` ve `.json` içindedir. Omniverse ve ayrıntılı Blender sahne üretimi bu sürümün doğrulaması değildir.

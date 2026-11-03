# School Evacuation Pilot v0.7 · Dış ekip varış referansı

Her normal tahliye koşusunun sonuç ekranında ambulans ve itfaiye için örnek varış zamanı gösterilir. Hesaplayıcı öğrenci tahliye motorundan ayrıdır; güzergâh, öğrenci akışı veya optimizasyon sonuçlarını değiştirmez.

## Hesaplama

Her iki ekip için bildirim anı, sarsıntı bittikten sonra kullanıcı tarafından seçilir. Varsayılan gecikme 0 saniyedir. Yayınlanmış 2024 İstanbul geneli ortalama varış süresi bu gecikmenin üzerine eklenir:

```text
depremden varış = sarsıntı süresi + bildirim gecikmesi + yayımlanmış ortalama
```

| Hizmet | İBB 2024 gerçekleşme ortalaması |
|---|---:|
| Ambulans / acil sağlık vakaları | 5 dk 44 sn |
| İtfaiye olayları | 6 dk 44 sn |

Kaynak: [İBB 2026 Performans Programı](https://uploads.ibb.istanbul/uploads/2026_Performans_Programi_b33fca6500.pdf). Her iki süre de İstanbul geneli dönem ortalamasıdır; bu okulun sokağı, seçilecek istasyon, olay türü veya deprem sonrası trafik için ölçülmüş süre değildir. Uygulama, bu ortalamaların varsayımsal bildirimden sonraki süre olarak uygulanmasını kabul eder.

## Sonuçları yorumlama

- Ekran tahminleri hem deprem başlangıcından hem sarsıntı bitiminden itibaren gösterir.
- Bu koşuda her iki hizmetin de bilgilendirildiği varsayılır. Gerçek olayda ekip görevlendirilmesi çağrının niteliğine ve komuta kararına bağlıdır.
- İstanbul geneli referansına göre son öğrencinin saha varışıyla ilk dış ekip varışını kıyaslayan bir açıklama gösterilir. Bu bir güvenlik veya müdahale yeterliliği hükmü değildir.
- Adres/istasyon bazlı yol süresi, ekip müsaitliği, eşzamanlı olaylar, deprem hasarı, kapalı yollar ve kapı erişimi henüz modellenmez.
- Sonuçlar tatbikat veya gerçek olay süreleriyle kalibre edilmiş değildir. Okul için gerçek ETA kabul edilmemelidir.

## Değişen dosyalar

`# =========================================================`

**external_response.py — DIŞ EKİP ZAMAN HESABI:** İBB'nin 2024 şehir geneli ortalamalarını alır ve bildirim gecikmesi ile sarsıntı süresini ekleyerek her senaryoya varış zamanı üretir. Neden: dış ekip referanslarını tahliye motorundan bağımsız tutmak.

`# =========================================================`

**app.py — SENARYO GİRDİSİ VE SONUÇ KARTLARI:** Bildirim gecikmesi ayarı, ambulans/itfaiye varış kartları ve sonuç JSON'una dış ekip hesabı eklendi. Neden: her normal koşuda varsayımları görünen zaman çizelgesi sunmak.

`# =========================================================`

**test_external_response.py — HESAP DOĞRULAMASI:** Resmî referansların kullanımı, gecikme eklenmesi, süre gösterimi ve geçersiz girdiler sınanır. Neden: farklı senaryolarda hesaplamanın tekrarlanabilir olmasını sağlamak.

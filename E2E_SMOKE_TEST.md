# OptiPrice AI — End-to-End Smoke Test

> Temiz veritabanı ile sıfırdan başlanarak tüm kullanıcı akışı test edilir.

**Test Tarihi:** 2026-05-13
**Test Ortamı:** Yerel (localhost:8000 backend, localhost:3000 frontend)
**Başlangıç Durumu:** Temiz DB (kullanıcı kaydı yok)

---

## Adım 1: Kayıt Olma

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 1.1 | `/auth/register` sayfası açılıyor | ☐ | ☐ |
| 1.2 | Email + şifre + ad soyad ile kayıt başarılı | ☐ | ☐ |
| 1.3 | Kayıt sonrası `/products` sayfasına yönlendirme | ☐ | ☐ |
| 1.4 | Sidebar'da kullanıcı adı görünüyor | ☐ | ☐ |

---

## Adım 2: Platform Bağlantısı

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 2.1 | `/connections` sayfası açılıyor | ☐ | ☐ |
| 2.2 | 3 platform kartı görünüyor (Trendyol, Amazon, OwnSite) | ☐ | ☐ |
| 2.3 | "Hesap Bağla" butonu çalışıyor | ☐ | ☐ |
| 2.4 | Bağlantı sonrası yeşil "Bağlı" badge'i görünüyor | ☐ | ☐ |

---

## Adım 3: Demo Seed (Opsiyonel Hızlı Başlangıç)

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 3.1 | `/products` sayfasında "Demo verisini yükle" butonu görünüyor | ☐ | ☐ |
| 3.2 | Butona tıklayınca 5 ürün + bağlantı oluşturuluyor | ☐ | ☐ |
| 3.3 | Success mesajı: "X ürün eklendi, Y mevcut atlandı" | ☐ | ☐ |
| 3.4 | Sayfa refresh sonrası ürünler tabloda görünüyor | ☐ | ☐ |

---

## Adım 4: Manuel Ürün Ekleme

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 4.1 | `/products/new` sayfası açılıyor | ☐ | ☐ |
| 4.2 | Form validasyonu çalışıyor (SKU zorunlu, fiyat > 0) | ☐ | ☐ |
| 4.3 | Yeni ürün eklendikten sonra detay sayfasına yönlendirme | ☐ | ☐ |
| 4.4 | 3 platformda listeleme başarılı (yeşil "Listelendi" badge) | ☐ | ☐ |

---

## Adım 5: Platform Listeleme (Ürün Detay)

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 5.1 | `/products/[id]` sayfasında 3 platform kartı görünüyor | ☐ | ☐ |
| 5.2 | Her kartta: güncel fiyat, taban fiyat, rakip fiyatı, buybox durumu | ☐ | ☐ |
| 5.3 | AI başlık her platform için farklı (SEO/Teknik/Marka stili) | ☐ | ☐ |
| 5.4 | Fiyat geçmişi chart'ı görünüyor (eğer pricing log varsa) | ☐ | ☐ |

---

## Adım 6: Pricing Tetikleme

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 6.1 | Ürün detayda "Fiyatlandırmayı Tetikle" butonu görünüyor | ☐ | ☐ |
| 6.2 | Tetikleme sonrası karar dönüyor (price_updated / floor_hit / no_action) | ☐ | ☐ |
| 6.3 | Karar sonrası fiyat güncelleniyor (eğer price_updated ise) | ☐ | ☐ |
| 6.4 | Karar sonucu SSE canlı log panelinde görünüyor | ☐ | ☐ |

---

## Adım 7: Rakip Simülatörü

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 7.1 | `/simulator` sayfası açılıyor | ☐ | ☐ |
| 7.2 | Platform/ürün seçimi çalışıyor | ☐ | ☐ |
| 7.3 | Rakip ekleme/kaldırma çalışıyor | ☐ | ☐ |
| 7.4 | Simülasyon başlatınca pricing agent tetikleniyor | ☐ | ☐ |
| 7.5 | Sonuçlar ekranda görünüyor | ☐ | ☐ |

---

## Adım 8: Canlı Loglar (SSE)

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 8.1 | `/logs` sayfası açılıyor | ☐ | ☐ |
| 8.2 | Terminal görünümlü log paneli render ediliyor | ☐ | ☐ |
| 8.3 | SSE bağlantısı kuruluyor (auto-reconnect) | ☐ | ☐ |
| 8.4 | Yeni pricing kararları canlı akıyor | ☐ | ☐ |

---

## Adım 9: Dashboard & Profil

| # | Kontrol | PASS | FAIL |
|---|---------|------|------|
| 9.1 | `/dashboard` sayfası açılıyor | ☐ | ☐ |
| 9.2 | Stat kartları görünüyor (Toplam Ürün, Listelenen, Kar, Buybox %) | ☐ | ☐ |
| 9.3 | Platform kar bar chart'ı render ediliyor | ☐ | ☐ |
| 9.4 | Son ajan kararları tablosu görünüyor | ☐ | ☐ |
| 9.5 | `/profile` sayfası açılıyor, kullanıcı bilgileri görünüyor | ☐ | ☐ |
| 9.6 | Çıkış yapma çalışıyor | ☐ | ☐ |

---

## Özet

| Bölüm | Toplam | Geçti | Kaldı |
|-------|--------|-------|-------|
| 1. Kayıt | 4 | | |
| 2. Platform Bağlantısı | 4 | | |
| 3. Demo Seed | 4 | | |
| 4. Ürün Ekleme | 4 | | |
| 5. Platform Listeleme | 4 | | |
| 6. Pricing Tetikleme | 4 | | |
| 7. Rakip Simülatörü | 5 | | |
| 8. Canlı Loglar | 4 | | |
| 9. Dashboard & Profil | 6 | | |
| **Toplam** | **39** | | |

---

## Notlar

- Demo seed ile tüm akış ~2 dakikada test edilebilir
- Backend ve tüm mock servisler çalışır durumda olmalı
- Gemini API key `.env` dosyasında geçerli olmalı (ListingAgent + PricingAgent için)
- Test sırasında hata alınırsa backend loglarına ve tarayıcı console'una bakılmalı

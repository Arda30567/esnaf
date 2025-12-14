# Esnaf Defteri - Borç/Alacak ve Günlük Kasa Takip Programı

## Proje Özeti
Küçük esnaflar için internet gerektirmeyen, basit, hızlı ve kullanılabilir bir borç-alacak defteri ve günlük kasa takip programı.

## Teknik Özellikler
- **Dil**: Python 3.11
- **GUI**: Tkinter
- **Veritabanı**: SQLite (yerel, offline)
- **PDF**: reportlab
- **Tek dosya**: `esnaf_defter.py`

## Modüller

### 1. Borç-Alacak (Veresiye Defteri)
- Müşteri ekleme/silme (ad, telefon, not)
- Borç ve ödeme işlemleri kaydetme
- Bakiye hesaplama (renkli gösterim: kırmızı=borçlu, yeşil=alacaklı)
- İşlem geçmişi görüntüleme
- İşlem silme (onay ile)

### 2. Günlük Kasa Takip
- Ciro girişi
- Gider girişi
- Günlük net hesaplama (ciro - gider)
- İşlem listesi görüntüleme

### 3. Raporlama
- Borç-alacak raporu (metin ve PDF)
- Kasa raporu (metin ve PDF)
- Ay/yıl bazlı filtreleme
- Otomatik dosya adı oluşturma

## Veritabanı Yapısı
- `musteriler`: id, ad, telefon, not_alani, olusturma_tarihi
- `islemler`: id, musteri_id, tarih, aciklama, tutar, islem_turu (BORÇ/ÖDEME)
- `kasa`: id, tarih, aciklama, tutar, islem_turu (CİRO/GİDER)

## Özellikler
- Tarih doğrulama (YYYY-MM-DD formatı zorunlu)
- Büyük butonlar ve Türkçe etiketler
- Hata mesajları kullanıcı dostu
- Otomatik veritabanı oluşturma
- Offline çalışma (internet gerektirmez)

## Çalıştırma
```bash
python esnaf_defter.py
```

## Son Güncelleme
- Tarih: 14 Aralık 2025
- Durum: Tüm özellikler tamamlandı (PDF rapor dahil)

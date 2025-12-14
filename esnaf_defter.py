#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESNAF DEFTERİ - Borç/Alacak ve Günlük Kasa Takip Programı
=========================================================
Küçük esnaflar için basit, hızlı ve kullanılabilir muhasebe programı.
İnternet gerektirmez, veriler yerel olarak saklanır.

Geliştirici: Python ile geliştirilmiştir
Sürüm: 1.0
"""
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import sqlite3
import os

# PDF için reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Veritabanı dosyası
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

DB_FILE = resource_path("esnaf_defter.db")


# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def tarih_dogrula(tarih_str):
    """Tarihi YYYY-MM-DD formatında doğrular"""
    if not tarih_str or not tarih_str.strip():
        return False, "Tarih boş olamaz!"
    
    try:
        datetime.strptime(tarih_str.strip(), "%Y-%m-%d")
        return True, tarih_str.strip()
    except ValueError:
        return False, "Geçersiz tarih formatı! (YYYY-AA-GG olmalı, örn: 2025-12-14)"


# ============================================================================
# VERİTABANI FONKSİYONLARI
# ============================================================================

def veritabani_baglantisi():
    """Veritabanı bağlantısı oluşturur"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def tablolari_olustur():
    """Gerekli tabloları oluşturur (yoksa)"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    
    # Müşteriler tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS musteriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            telefon TEXT,
            not_alani TEXT,
            olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Borç-Alacak işlemleri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_id INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            aciklama TEXT,
            tutar REAL NOT NULL,
            islem_turu TEXT NOT NULL,
            olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (musteri_id) REFERENCES musteriler(id)
        )
    ''')
    
    # Günlük kasa tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kasa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            aciklama TEXT,
            tutar REAL NOT NULL,
            islem_turu TEXT NOT NULL,
            olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


# ============================================================================
# MÜŞTERİ FONKSİYONLARI
# ============================================================================

def musteri_ekle(ad, telefon="", not_alani=""):
    """Yeni müşteri ekler"""
    if not ad.strip():
        return False, "Müşteri adı boş olamaz!"
    
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO musteriler (ad, telefon, not_alani) VALUES (?, ?, ?)",
        (ad.strip(), telefon.strip(), not_alani.strip())
    )
    conn.commit()
    conn.close()
    return True, "Müşteri eklendi."


def musteri_listele():
    """Tüm müşterileri listeler"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM musteriler ORDER BY ad")
    musteriler = cursor.fetchall()
    conn.close()
    return musteriler


def musteri_sil(musteri_id):
    """Müşteriyi ve işlemlerini siler"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM islemler WHERE musteri_id = ?", (musteri_id,))
    cursor.execute("DELETE FROM musteriler WHERE id = ?", (musteri_id,))
    conn.commit()
    conn.close()


def musteri_bakiye_hesapla(musteri_id):
    """Müşterinin bakiyesini hesaplar (Borç - Ödeme)"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    
    # Borç toplamı
    cursor.execute(
        "SELECT COALESCE(SUM(tutar), 0) FROM islemler WHERE musteri_id = ? AND islem_turu = 'BORÇ'",
        (musteri_id,)
    )
    borc_toplam = cursor.fetchone()[0]
    
    # Ödeme toplamı
    cursor.execute(
        "SELECT COALESCE(SUM(tutar), 0) FROM islemler WHERE musteri_id = ? AND islem_turu = 'ÖDEME'",
        (musteri_id,)
    )
    odeme_toplam = cursor.fetchone()[0]
    
    conn.close()
    
    # Bakiye = Borç - Ödeme (pozitif = müşteri borçlu, negatif = biz borçluyuz)
    return borc_toplam - odeme_toplam


# ============================================================================
# İŞLEM FONKSİYONLARI
# ============================================================================

def islem_ekle(musteri_id, tarih, aciklama, tutar, islem_turu):
    """Yeni işlem ekler"""
    # Tarih doğrulama
    tarih_gecerli, tarih_sonuc = tarih_dogrula(tarih)
    if not tarih_gecerli:
        return False, tarih_sonuc
    
    try:
        tutar = float(tutar)
        if tutar <= 0:
            return False, "Tutar sıfırdan büyük olmalı!"
    except ValueError:
        return False, "Geçerli bir tutar girin!"
    
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO islemler (musteri_id, tarih, aciklama, tutar, islem_turu) VALUES (?, ?, ?, ?, ?)",
        (musteri_id, tarih_sonuc, aciklama.strip(), tutar, islem_turu)
    )
    conn.commit()
    conn.close()
    return True, "İşlem kaydedildi."


def islem_listele(musteri_id):
    """Müşterinin işlemlerini listeler"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM islemler WHERE musteri_id = ? ORDER BY tarih DESC, id DESC",
        (musteri_id,)
    )
    islemler = cursor.fetchall()
    conn.close()
    return islemler


def islem_sil(islem_id):
    """İşlemi siler"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM islemler WHERE id = ?", (islem_id,))
    conn.commit()
    conn.close()


def genel_borc_ozeti():
    """Tüm müşterilerin genel borç özetini döndürür"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    
    # Toplam borç
    cursor.execute("SELECT COALESCE(SUM(tutar), 0) FROM islemler WHERE islem_turu = 'BORÇ'")
    toplam_borc = cursor.fetchone()[0]
    
    # Toplam ödeme
    cursor.execute("SELECT COALESCE(SUM(tutar), 0) FROM islemler WHERE islem_turu = 'ÖDEME'")
    toplam_odeme = cursor.fetchone()[0]
    
    conn.close()
    
    return toplam_borc, toplam_odeme, toplam_borc - toplam_odeme


# ============================================================================
# KASA FONKSİYONLARI
# ============================================================================

def kasa_islem_ekle(tarih, aciklama, tutar, islem_turu):
    """Kasa işlemi ekler (CİRO veya GİDER)"""
    # Tarih doğrulama
    tarih_gecerli, tarih_sonuc = tarih_dogrula(tarih)
    if not tarih_gecerli:
        return False, tarih_sonuc
    
    try:
        tutar = float(tutar)
        if tutar <= 0:
            return False, "Tutar sıfırdan büyük olmalı!"
    except ValueError:
        return False, "Geçerli bir tutar girin!"
    
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO kasa (tarih, aciklama, tutar, islem_turu) VALUES (?, ?, ?, ?)",
        (tarih_sonuc, aciklama.strip(), tutar, islem_turu)
    )
    conn.commit()
    conn.close()
    return True, "Kasa işlemi kaydedildi."


def kasa_gunluk_ozet(tarih):
    """Belirli bir günün kasa özetini döndürür"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    
    # Günlük ciro
    cursor.execute(
        "SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE tarih = ? AND islem_turu = 'CİRO'",
        (tarih,)
    )
    ciro = cursor.fetchone()[0]
    
    # Günlük gider
    cursor.execute(
        "SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE tarih = ? AND islem_turu = 'GİDER'",
        (tarih,)
    )
    gider = cursor.fetchone()[0]
    
    conn.close()
    
    return ciro, gider, ciro - gider


def kasa_aylik_ozet(yil, ay):
    """Belirli bir ayın kasa özetini döndürür"""
    ay_baslangic = f"{yil}-{ay:02d}-01"
    if ay == 12:
        ay_bitis = f"{yil + 1}-01-01"
    else:
        ay_bitis = f"{yil}-{ay + 1:02d}-01"
    
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    
    # Aylık ciro
    cursor.execute(
        "SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE tarih >= ? AND tarih < ? AND islem_turu = 'CİRO'",
        (ay_baslangic, ay_bitis)
    )
    ciro = cursor.fetchone()[0]
    
    # Aylık gider
    cursor.execute(
        "SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE tarih >= ? AND tarih < ? AND islem_turu = 'GİDER'",
        (ay_baslangic, ay_bitis)
    )
    gider = cursor.fetchone()[0]
    
    conn.close()
    
    return ciro, gider, ciro - gider


def kasa_islem_listele(tarih=None):
    """Kasa işlemlerini listeler"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    
    if tarih:
        cursor.execute(
            "SELECT * FROM kasa WHERE tarih = ? ORDER BY id DESC",
            (tarih,)
        )
    else:
        cursor.execute("SELECT * FROM kasa ORDER BY tarih DESC, id DESC")
    
    islemler = cursor.fetchall()
    conn.close()
    return islemler


def kasa_islem_sil(islem_id):
    """Kasa işlemini siler"""
    conn = veritabani_baglantisi()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM kasa WHERE id = ?", (islem_id,))
    conn.commit()
    conn.close()


# ============================================================================
# RAPOR FONKSİYONLARI
# ============================================================================

def borc_raporu_olustur():
    """Borç-alacak raporunu metin olarak oluşturur"""
    rapor = []
    rapor.append("=" * 60)
    rapor.append("BORÇ - ALACAK RAPORU")
    rapor.append(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    rapor.append("=" * 60)
    rapor.append("")
    
    musteriler = musteri_listele()
    toplam_bakiye = 0
    
    for musteri in musteriler:
        bakiye = musteri_bakiye_hesapla(musteri['id'])
        toplam_bakiye += bakiye
        
        if bakiye != 0:
            durum = "BORÇLU" if bakiye > 0 else "ALACAKLI"
            rapor.append(f"Müşteri: {musteri['ad']}")
            if musteri['telefon']:
                rapor.append(f"Telefon: {musteri['telefon']}")
            rapor.append(f"Bakiye: {abs(bakiye):.2f} TL ({durum})")
            rapor.append("-" * 40)
            
            # İşlem detayları
            islemler = islem_listele(musteri['id'])
            for islem in islemler:
                rapor.append(f"  {islem['tarih']} - {islem['islem_turu']}: {islem['tutar']:.2f} TL")
                if islem['aciklama']:
                    rapor.append(f"    Açıklama: {islem['aciklama']}")
            rapor.append("")
    
    rapor.append("=" * 60)
    if toplam_bakiye > 0:
        rapor.append(f"GENEL TOPLAM: {toplam_bakiye:.2f} TL (Alacağınız var)")
    elif toplam_bakiye < 0:
        rapor.append(f"GENEL TOPLAM: {abs(toplam_bakiye):.2f} TL (Borcunuz var)")
    else:
        rapor.append("GENEL TOPLAM: 0.00 TL (Dengede)")
    rapor.append("=" * 60)
    
    return "\n".join(rapor)


def kasa_raporu_olustur(yil=None, ay=None):
    """Kasa raporunu metin olarak oluşturur"""
    rapor = []
    rapor.append("=" * 60)
    
    if yil and ay:
        rapor.append(f"KASA RAPORU - {ay:02d}/{yil}")
        ciro, gider, net = kasa_aylik_ozet(yil, ay)
    else:
        rapor.append("KASA RAPORU - TÜM ZAMANLAR")
        conn = veritabani_baglantisi()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE islem_turu = 'CİRO'")
        ciro = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE islem_turu = 'GİDER'")
        gider = cursor.fetchone()[0]
        net = ciro - gider
        conn.close()
    
    rapor.append(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    rapor.append("=" * 60)
    rapor.append("")
    
    rapor.append(f"Toplam Ciro:  {ciro:.2f} TL")
    rapor.append(f"Toplam Gider: {gider:.2f} TL")
    rapor.append("-" * 40)
    
    if net >= 0:
        rapor.append(f"NET KÂR:      {net:.2f} TL")
    else:
        rapor.append(f"NET ZARAR:    {abs(net):.2f} TL")
    
    rapor.append("")
    rapor.append("=" * 60)
    rapor.append("DETAYLI İŞLEMLER:")
    rapor.append("=" * 60)
    
    islemler = kasa_islem_listele()
    for islem in islemler:
        if yil and ay:
            islem_tarihi = islem['tarih']
            if not islem_tarihi.startswith(f"{yil}-{ay:02d}"):
                continue
        
        rapor.append(f"{islem['tarih']} - {islem['islem_turu']}: {islem['tutar']:.2f} TL")
        if islem['aciklama']:
            rapor.append(f"  Açıklama: {islem['aciklama']}")
    
    return "\n".join(rapor)


def borc_raporu_pdf_olustur(dosya_yolu=None):
    """Borç-alacak raporunu PDF olarak oluşturur"""
    if not dosya_yolu:
        dosya_yolu = f"borc_alacak_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    doc = SimpleDocTemplate(dosya_yolu, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    # Başlık stili
    baslik_stili = ParagraphStyle(
        'Baslik',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,
        spaceAfter=20
    )
    
    normal_stili = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=5
    )
    
    # Başlık
    elements.append(Paragraph("BORC - ALACAK RAPORU", baslik_stili))
    elements.append(Paragraph(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_stili))
    elements.append(Spacer(1, 20))
    
    # Müşteri verileri
    musteriler = musteri_listele()
    toplam_bakiye = 0
    
    for musteri in musteriler:
        bakiye = musteri_bakiye_hesapla(musteri['id'])
        toplam_bakiye += bakiye
        
        if bakiye != 0:
            durum = "BORCLU" if bakiye > 0 else "ALACAKLI"
            
            # Müşteri başlığı
            musteri_baslik = f"Musteri: {musteri['ad']}"
            if musteri['telefon']:
                musteri_baslik += f" - Tel: {musteri['telefon']}"
            elements.append(Paragraph(musteri_baslik, normal_stili))
            elements.append(Paragraph(f"Bakiye: {abs(bakiye):.2f} TL ({durum})", normal_stili))
            
            # İşlem tablosu
            islemler = islem_listele(musteri['id'])
            if islemler:
                tablo_verisi = [["Tarih", "Tur", "Tutar (TL)", "Aciklama"]]
                for islem in islemler:
                    tablo_verisi.append([
                        islem['tarih'],
                        islem['islem_turu'],
                        f"{islem['tutar']:.2f}",
                        islem['aciklama'] or "-"
                    ])
                
                tablo = Table(tablo_verisi, colWidths=[3*cm, 2.5*cm, 3*cm, 8*cm])
                tablo.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(tablo)
            
            elements.append(Spacer(1, 15))
    
    # Genel toplam
    elements.append(Spacer(1, 20))
    if toplam_bakiye > 0:
        toplam_metin = f"GENEL TOPLAM: {toplam_bakiye:.2f} TL (Alacaginiz var)"
    elif toplam_bakiye < 0:
        toplam_metin = f"GENEL TOPLAM: {abs(toplam_bakiye):.2f} TL (Borcunuz var)"
    else:
        toplam_metin = "GENEL TOPLAM: 0.00 TL (Dengede)"
    
    toplam_stili = ParagraphStyle(
        'Toplam',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=1
    )
    elements.append(Paragraph(toplam_metin, toplam_stili))
    
    doc.build(elements)
    return dosya_yolu


def kasa_raporu_pdf_olustur(yil=None, ay=None, dosya_yolu=None):
    """Kasa raporunu PDF olarak oluşturur"""
    if not dosya_yolu:
        if yil and ay:
            dosya_yolu = f"kasa_raporu_{yil}_{ay:02d}_{datetime.now().strftime('%H%M%S')}.pdf"
        else:
            dosya_yolu = f"kasa_raporu_tum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    doc = SimpleDocTemplate(dosya_yolu, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    styles = getSampleStyleSheet()
    
    baslik_stili = ParagraphStyle(
        'Baslik',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,
        spaceAfter=20
    )
    
    normal_stili = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=5
    )
    
    # Başlık
    if yil and ay:
        baslik = f"KASA RAPORU - {ay:02d}/{yil}"
        ciro, gider, net = kasa_aylik_ozet(yil, ay)
    else:
        baslik = "KASA RAPORU - TUM ZAMANLAR"
        conn = veritabani_baglantisi()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE islem_turu = 'CİRO'")
        ciro = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(tutar), 0) FROM kasa WHERE islem_turu = 'GİDER'")
        gider = cursor.fetchone()[0]
        net = ciro - gider
        conn.close()
    
    elements.append(Paragraph(baslik, baslik_stili))
    elements.append(Paragraph(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_stili))
    elements.append(Spacer(1, 20))
    
    # Özet tablosu
    ozet_verisi = [
        ["Toplam Ciro", f"{ciro:.2f} TL"],
        ["Toplam Gider", f"{gider:.2f} TL"],
        ["NET", f"{net:.2f} TL"]
    ]
    
    ozet_tablo = Table(ozet_verisi, colWidths=[6*cm, 6*cm])
    ozet_tablo.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 2), (-1, 2), colors.lightgreen if net >= 0 else colors.lightcoral),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(ozet_tablo)
    elements.append(Spacer(1, 30))
    
    # Detaylı işlemler
    elements.append(Paragraph("DETAYLI ISLEMLER", baslik_stili))
    
    islemler = kasa_islem_listele()
    tablo_verisi = [["Tarih", "Tur", "Tutar (TL)", "Aciklama"]]
    
    for islem in islemler:
        if yil and ay:
            islem_tarihi = islem['tarih']
            if not islem_tarihi.startswith(f"{yil}-{ay:02d}"):
                continue
        
        tablo_verisi.append([
            islem['tarih'],
            islem['islem_turu'],
            f"{islem['tutar']:.2f}",
            islem['aciklama'] or "-"
        ])
    
    if len(tablo_verisi) > 1:
        tablo = Table(tablo_verisi, colWidths=[3*cm, 2.5*cm, 3*cm, 8*cm])
        tablo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(tablo)
    else:
        elements.append(Paragraph("Bu donem icin islem bulunamadi.", normal_stili))
    
    doc.build(elements)
    return dosya_yolu


# ============================================================================
# ANA UYGULAMA SINIFI
# ============================================================================

class EsnafDefterUygulamasi:
    def __init__(self, root):
        self.root = root
        self.root.title("Esnaf Defteri - Borç/Alacak ve Kasa Takip")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Stil ayarları
        self.stil_ayarla()
        
        # Ana notebook (sekmeler)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Sekmeler
        self.borc_alacak_sekmesi = ttk.Frame(self.notebook)
        self.kasa_sekmesi = ttk.Frame(self.notebook)
        self.rapor_sekmesi = ttk.Frame(self.notebook)
        
        self.notebook.add(self.borc_alacak_sekmesi, text="  📒 Borç / Alacak  ")
        self.notebook.add(self.kasa_sekmesi, text="  💰 Günlük Kasa  ")
        self.notebook.add(self.rapor_sekmesi, text="  📊 Raporlar  ")
        
        # Seçili müşteri
        self.secili_musteri_id = None
        
        # Sekmeleri oluştur
        self.borc_alacak_olustur()
        self.kasa_olustur()
        self.rapor_olustur()
        
        # İlk yükleme
        self.musteri_listesini_guncelle()
        self.kasa_listesini_guncelle()
    
    def stil_ayarla(self):
        """Uygulama stilini ayarlar"""
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Arial", 12, "bold"), padding=[20, 10])
        style.configure("TButton", font=("Arial", 11), padding=10)
        style.configure("TLabel", font=("Arial", 11))
        style.configure("TEntry", font=("Arial", 11))
        style.configure("Treeview", font=("Arial", 10), rowheight=28)
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
    
    # ========================================================================
    # BORÇ-ALACAK SEKMESİ
    # ========================================================================
    
    def borc_alacak_olustur(self):
        """Borç-alacak sekmesini oluşturur"""
        # Ana çerçeve
        ana_frame = ttk.Frame(self.borc_alacak_sekmesi)
        ana_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Sol panel - Müşteri listesi
        sol_frame = ttk.LabelFrame(ana_frame, text="MÜŞTERİLER", padding=10)
        sol_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)
        
        # Müşteri listesi
        self.musteri_listbox = tk.Listbox(sol_frame, font=("Arial", 12), width=25, height=20)
        self.musteri_listbox.pack(fill=tk.BOTH, expand=True)
        self.musteri_listbox.bind('<<ListboxSelect>>', self.musteri_secildi)
        
        # Müşteri ekleme butonu
        btn_frame = ttk.Frame(sol_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="➕ Yeni Müşteri", command=self.musteri_ekle_dialog).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="🗑️ Müşteri Sil", command=self.musteri_sil_onay).pack(fill=tk.X, pady=2)
        
        # Sağ panel - İşlem detayları
        sag_frame = ttk.LabelFrame(ana_frame, text="İŞLEM GEÇMİŞİ", padding=10)
        sag_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Müşteri bilgi etiketi
        self.musteri_bilgi_label = ttk.Label(sag_frame, text="Müşteri seçin...", font=("Arial", 14, "bold"))
        self.musteri_bilgi_label.pack(anchor=tk.W, pady=5)
        
        # İşlem listesi
        islem_frame = ttk.Frame(sag_frame)
        islem_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview ile işlem listesi
        columns = ("Tarih", "Tür", "Tutar", "Açıklama")
        self.islem_tree = ttk.Treeview(islem_frame, columns=columns, show="headings", height=12)
        
        self.islem_tree.heading("Tarih", text="Tarih")
        self.islem_tree.heading("Tür", text="Tür")
        self.islem_tree.heading("Tutar", text="Tutar (TL)")
        self.islem_tree.heading("Açıklama", text="Açıklama")
        
        self.islem_tree.column("Tarih", width=100, anchor=tk.CENTER)
        self.islem_tree.column("Tür", width=80, anchor=tk.CENTER)
        self.islem_tree.column("Tutar", width=100, anchor=tk.E)
        self.islem_tree.column("Açıklama", width=200)
        
        scrollbar = ttk.Scrollbar(islem_frame, orient=tk.VERTICAL, command=self.islem_tree.yview)
        self.islem_tree.configure(yscrollcommand=scrollbar.set)
        
        self.islem_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bakiye gösterimi
        self.bakiye_frame = tk.Frame(sag_frame, bg="#f0f0f0", pady=10)
        self.bakiye_frame.pack(fill=tk.X, pady=10)
        
        self.bakiye_label = tk.Label(self.bakiye_frame, text="BAKİYE: 0.00 TL", 
                                     font=("Arial", 16, "bold"), bg="#f0f0f0")
        self.bakiye_label.pack()
        
        # İşlem butonları
        islem_btn_frame = ttk.Frame(sag_frame)
        islem_btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(islem_btn_frame, text="📝 Borç Ekle", 
                   command=lambda: self.islem_ekle_dialog("BORÇ")).pack(side=tk.LEFT, padx=5)
        ttk.Button(islem_btn_frame, text="💵 Ödeme Ekle", 
                   command=lambda: self.islem_ekle_dialog("ÖDEME")).pack(side=tk.LEFT, padx=5)
        ttk.Button(islem_btn_frame, text="🗑️ Seçili İşlemi Sil", 
                   command=self.islem_sil_onay).pack(side=tk.LEFT, padx=5)
        
        # Genel özet
        ozet_frame = ttk.LabelFrame(sag_frame, text="GENEL ÖZET", padding=10)
        ozet_frame.pack(fill=tk.X, pady=5)
        
        self.genel_ozet_label = ttk.Label(ozet_frame, text="", font=("Arial", 11))
        self.genel_ozet_label.pack()
    
    def musteri_listesini_guncelle(self):
        """Müşteri listesini günceller"""
        self.musteri_listbox.delete(0, tk.END)
        self.musteriler = musteri_listele()
        
        for musteri in self.musteriler:
            bakiye = musteri_bakiye_hesapla(musteri['id'])
            if bakiye > 0:
                durum = f" (+{bakiye:.0f})"
            elif bakiye < 0:
                durum = f" ({bakiye:.0f})"
            else:
                durum = ""
            self.musteri_listbox.insert(tk.END, f"{musteri['ad']}{durum}")
        
        self.genel_ozet_guncelle()
    
    def genel_ozet_guncelle(self):
        """Genel borç özetini günceller"""
        toplam_borc, toplam_odeme, net = genel_borc_ozeti()
        
        if net > 0:
            durum = f"Toplam Alacağınız: {net:.2f} TL"
        elif net < 0:
            durum = f"Toplam Borcunuz: {abs(net):.2f} TL"
        else:
            durum = "Borç/Alacak dengede"
        
        self.genel_ozet_label.config(
            text=f"Toplam Borç: {toplam_borc:.2f} TL | Toplam Ödeme: {toplam_odeme:.2f} TL | {durum}"
        )
    
    def musteri_secildi(self, event):
        """Müşteri seçildiğinde çağrılır"""
        selection = self.musteri_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        musteri = self.musteriler[index]
        self.secili_musteri_id = musteri['id']
        
        # Müşteri bilgilerini göster
        bilgi = f"{musteri['ad']}"
        if musteri['telefon']:
            bilgi += f" - Tel: {musteri['telefon']}"
        self.musteri_bilgi_label.config(text=bilgi)
        
        # İşlemleri listele
        self.islem_listesini_guncelle()
    
    def islem_listesini_guncelle(self):
        """İşlem listesini günceller"""
        # Listeyi temizle
        for item in self.islem_tree.get_children():
            self.islem_tree.delete(item)
        
        if not self.secili_musteri_id:
            return
        
        # İşlemleri getir
        islemler = islem_listele(self.secili_musteri_id)
        self.islemler = islemler
        
        for islem in islemler:
            self.islem_tree.insert("", tk.END, values=(
                islem['tarih'],
                islem['islem_turu'],
                f"{islem['tutar']:.2f}",
                islem['aciklama'] or ""
            ), iid=islem['id'])
        
        # Bakiyeyi güncelle
        bakiye = musteri_bakiye_hesapla(self.secili_musteri_id)
        if bakiye > 0:
            self.bakiye_label.config(text=f"BAKİYE: {bakiye:.2f} TL (BORÇLU)", fg="red")
            self.bakiye_frame.config(bg="#ffcccc")
            self.bakiye_label.config(bg="#ffcccc")
        elif bakiye < 0:
            self.bakiye_label.config(text=f"BAKİYE: {abs(bakiye):.2f} TL (ALACAKLI)", fg="green")
            self.bakiye_frame.config(bg="#ccffcc")
            self.bakiye_label.config(bg="#ccffcc")
        else:
            self.bakiye_label.config(text="BAKİYE: 0.00 TL (DENGELİ)", fg="black")
            self.bakiye_frame.config(bg="#f0f0f0")
            self.bakiye_label.config(bg="#f0f0f0")
    
    def musteri_ekle_dialog(self):
        """Müşteri ekleme penceresi"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Yeni Müşteri Ekle")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Ad / Ünvan:", font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, pady=5)
        ad_entry = ttk.Entry(frame, font=("Arial", 12), width=30)
        ad_entry.grid(row=0, column=1, pady=5)
        ad_entry.focus()
        
        ttk.Label(frame, text="Telefon:", font=("Arial", 12)).grid(row=1, column=0, sticky=tk.W, pady=5)
        tel_entry = ttk.Entry(frame, font=("Arial", 12), width=30)
        tel_entry.grid(row=1, column=1, pady=5)
        
        ttk.Label(frame, text="Not:", font=("Arial", 12)).grid(row=2, column=0, sticky=tk.W, pady=5)
        not_entry = ttk.Entry(frame, font=("Arial", 12), width=30)
        not_entry.grid(row=2, column=1, pady=5)
        
        def kaydet():
            basarili, mesaj = musteri_ekle(ad_entry.get(), tel_entry.get(), not_entry.get())
            if basarili:
                self.musteri_listesini_guncelle()
                dialog.destroy()
            else:
                messagebox.showerror("Hata", mesaj)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="💾 Kaydet", command=kaydet).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ İptal", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def musteri_sil_onay(self):
        """Müşteri silme onayı"""
        if not self.secili_musteri_id:
            messagebox.showwarning("Uyarı", "Lütfen bir müşteri seçin!")
            return
        
        onay = messagebox.askyesno("Onay", "Bu müşteriyi ve tüm işlemlerini silmek istediğinize emin misiniz?")
        if onay:
            musteri_sil(self.secili_musteri_id)
            self.secili_musteri_id = None
            self.musteri_bilgi_label.config(text="Müşteri seçin...")
            self.musteri_listesini_guncelle()
            self.islem_listesini_guncelle()
    
    def islem_ekle_dialog(self, islem_turu):
        """İşlem ekleme penceresi"""
        if not self.secili_musteri_id:
            messagebox.showwarning("Uyarı", "Lütfen önce bir müşteri seçin!")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{'Borç' if islem_turu == 'BORÇ' else 'Ödeme'} Ekle")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Tarih:", font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, pady=5)
        tarih_entry = ttk.Entry(frame, font=("Arial", 12), width=20)
        tarih_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        tarih_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="Tutar (TL):", font=("Arial", 12)).grid(row=1, column=0, sticky=tk.W, pady=5)
        tutar_entry = ttk.Entry(frame, font=("Arial", 12), width=20)
        tutar_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        tutar_entry.focus()
        
        ttk.Label(frame, text="Açıklama:", font=("Arial", 12)).grid(row=2, column=0, sticky=tk.W, pady=5)
        aciklama_entry = ttk.Entry(frame, font=("Arial", 12), width=30)
        aciklama_entry.grid(row=2, column=1, pady=5)
        
        def kaydet():
            basarili, mesaj = islem_ekle(
                self.secili_musteri_id,
                tarih_entry.get(),
                aciklama_entry.get(),
                tutar_entry.get(),
                islem_turu
            )
            if basarili:
                self.islem_listesini_guncelle()
                self.musteri_listesini_guncelle()
                dialog.destroy()
            else:
                messagebox.showerror("Hata", mesaj)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="💾 Kaydet", command=kaydet).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ İptal", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def islem_sil_onay(self):
        """İşlem silme onayı"""
        selection = self.islem_tree.selection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen bir işlem seçin!")
            return
        
        onay = messagebox.askyesno("Onay", "Bu işlemi silmek istediğinize emin misiniz?")
        if onay:
            islem_id = selection[0]
            islem_sil(islem_id)
            self.islem_listesini_guncelle()
            self.musteri_listesini_guncelle()
    
    # ========================================================================
    # KASA SEKMESİ
    # ========================================================================
    
    def kasa_olustur(self):
        """Kasa sekmesini oluşturur"""
        # Üst panel - Giriş alanları
        ust_frame = ttk.LabelFrame(self.kasa_sekmesi, text="YENİ KASA İŞLEMİ", padding=15)
        ust_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Tarih
        ttk.Label(ust_frame, text="Tarih:", font=("Arial", 12)).grid(row=0, column=0, padx=5, pady=5)
        self.kasa_tarih_entry = ttk.Entry(ust_frame, font=("Arial", 12), width=15)
        self.kasa_tarih_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        self.kasa_tarih_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Tutar
        ttk.Label(ust_frame, text="Tutar (TL):", font=("Arial", 12)).grid(row=0, column=2, padx=5, pady=5)
        self.kasa_tutar_entry = ttk.Entry(ust_frame, font=("Arial", 12), width=15)
        self.kasa_tutar_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Açıklama
        ttk.Label(ust_frame, text="Açıklama:", font=("Arial", 12)).grid(row=0, column=4, padx=5, pady=5)
        self.kasa_aciklama_entry = ttk.Entry(ust_frame, font=("Arial", 12), width=25)
        self.kasa_aciklama_entry.grid(row=0, column=5, padx=5, pady=5)
        
        # Butonlar
        btn_frame = ttk.Frame(ust_frame)
        btn_frame.grid(row=1, column=0, columnspan=6, pady=15)
        
        ttk.Button(btn_frame, text="💰 CİRO EKLE", 
                   command=lambda: self.kasa_islem_kaydet("CİRO")).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="📤 GİDER EKLE", 
                   command=lambda: self.kasa_islem_kaydet("GİDER")).pack(side=tk.LEFT, padx=10)
        
        # Orta panel - Günlük özet
        ozet_frame = ttk.LabelFrame(self.kasa_sekmesi, text="GÜNLÜK ÖZET", padding=15)
        ozet_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.gunluk_ozet_label = tk.Label(ozet_frame, text="", font=("Arial", 14, "bold"), pady=10)
        self.gunluk_ozet_label.pack()
        
        # Alt panel - İşlem listesi
        alt_frame = ttk.LabelFrame(self.kasa_sekmesi, text="KASA İŞLEMLERİ", padding=10)
        alt_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview
        columns = ("Tarih", "Tür", "Tutar", "Açıklama")
        self.kasa_tree = ttk.Treeview(alt_frame, columns=columns, show="headings", height=15)
        
        self.kasa_tree.heading("Tarih", text="Tarih")
        self.kasa_tree.heading("Tür", text="Tür")
        self.kasa_tree.heading("Tutar", text="Tutar (TL)")
        self.kasa_tree.heading("Açıklama", text="Açıklama")
        
        self.kasa_tree.column("Tarih", width=120, anchor=tk.CENTER)
        self.kasa_tree.column("Tür", width=100, anchor=tk.CENTER)
        self.kasa_tree.column("Tutar", width=120, anchor=tk.E)
        self.kasa_tree.column("Açıklama", width=300)
        
        scrollbar = ttk.Scrollbar(alt_frame, orient=tk.VERTICAL, command=self.kasa_tree.yview)
        self.kasa_tree.configure(yscrollcommand=scrollbar.set)
        
        self.kasa_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Silme butonu
        ttk.Button(alt_frame, text="🗑️ Seçili İşlemi Sil", 
                   command=self.kasa_islem_sil_onay).pack(pady=10)
    
    def kasa_listesini_guncelle(self):
        """Kasa listesini günceller"""
        # Listeyi temizle
        for item in self.kasa_tree.get_children():
            self.kasa_tree.delete(item)
        
        # İşlemleri getir
        islemler = kasa_islem_listele()
        
        for islem in islemler:
            self.kasa_tree.insert("", tk.END, values=(
                islem['tarih'],
                islem['islem_turu'],
                f"{islem['tutar']:.2f}",
                islem['aciklama'] or ""
            ), iid=islem['id'])
        
        # Günlük özeti güncelle
        bugun = date.today().strftime("%Y-%m-%d")
        ciro, gider, net = kasa_gunluk_ozet(bugun)
        
        if net >= 0:
            renk = "green"
            durum = "KÂR"
        else:
            renk = "red"
            durum = "ZARAR"
        
        self.gunluk_ozet_label.config(
            text=f"Bugün ({bugun}): Ciro: {ciro:.2f} TL | Gider: {gider:.2f} TL | Net: {net:.2f} TL ({durum})",
            fg=renk
        )
    
    def kasa_islem_kaydet(self, islem_turu):
        """Kasa işlemini kaydeder"""
        tarih = self.kasa_tarih_entry.get()
        tutar = self.kasa_tutar_entry.get()
        aciklama = self.kasa_aciklama_entry.get()
        
        basarili, mesaj = kasa_islem_ekle(tarih, aciklama, tutar, islem_turu)
        
        if basarili:
            self.kasa_tutar_entry.delete(0, tk.END)
            self.kasa_aciklama_entry.delete(0, tk.END)
            self.kasa_listesini_guncelle()
            messagebox.showinfo("Başarılı", mesaj)
        else:
            messagebox.showerror("Hata", mesaj)
    
    def kasa_islem_sil_onay(self):
        """Kasa işlemi silme onayı"""
        selection = self.kasa_tree.selection()
        if not selection:
            messagebox.showwarning("Uyarı", "Lütfen bir işlem seçin!")
            return
        
        onay = messagebox.askyesno("Onay", "Bu işlemi silmek istediğinize emin misiniz?")
        if onay:
            islem_id = selection[0]
            kasa_islem_sil(islem_id)
            self.kasa_listesini_guncelle()
    
    # ========================================================================
    # RAPOR SEKMESİ
    # ========================================================================
    
    def rapor_olustur(self):
        """Rapor sekmesini oluşturur"""
        frame = ttk.Frame(self.rapor_sekmesi, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Borç-Alacak Raporu
        borc_frame = ttk.LabelFrame(frame, text="BORÇ-ALACAK RAPORU", padding=20)
        borc_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(borc_frame, text="Tüm müşterilerin borç-alacak durumunu görüntüleyin.", 
                  font=("Arial", 11)).pack(pady=5)
        
        borc_btn_frame = ttk.Frame(borc_frame)
        borc_btn_frame.pack(pady=10)
        
        ttk.Button(borc_btn_frame, text="📋 Raporu Görüntüle", 
                   command=self.borc_raporu_goster).pack(side=tk.LEFT, padx=5)
        ttk.Button(borc_btn_frame, text="📄 PDF Olarak Kaydet", 
                   command=self.borc_raporu_pdf_kaydet).pack(side=tk.LEFT, padx=5)
        
        # Kasa Raporu
        kasa_frame = ttk.LabelFrame(frame, text="KASA RAPORU", padding=20)
        kasa_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(kasa_frame, text="Günlük kasa hareketlerinin özetini görüntüleyin.", 
                  font=("Arial", 11)).pack(pady=5)
        
        ay_frame = ttk.Frame(kasa_frame)
        ay_frame.pack(pady=5)
        
        ttk.Label(ay_frame, text="Ay:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.rapor_ay = ttk.Combobox(ay_frame, values=[str(i) for i in range(1, 13)], width=5, font=("Arial", 11))
        self.rapor_ay.set(str(datetime.now().month))
        self.rapor_ay.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(ay_frame, text="Yıl:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.rapor_yil = ttk.Combobox(ay_frame, values=[str(i) for i in range(2020, 2031)], width=7, font=("Arial", 11))
        self.rapor_yil.set(datetime.now().year)
        self.rapor_yil.pack(side=tk.LEFT, padx=5)
        
        kasa_btn_frame = ttk.Frame(kasa_frame)
        kasa_btn_frame.pack(pady=10)
        
        ttk.Button(kasa_btn_frame, text="📋 Raporu Görüntüle", 
                   command=self.kasa_raporu_goster).pack(side=tk.LEFT, padx=5)
        ttk.Button(kasa_btn_frame, text="📄 PDF Olarak Kaydet", 
                   command=self.kasa_raporu_pdf_kaydet).pack(side=tk.LEFT, padx=5)
        
        # Rapor görüntüleme alanı
        rapor_frame = ttk.LabelFrame(frame, text="RAPOR", padding=10)
        rapor_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.rapor_text = tk.Text(rapor_frame, font=("Courier", 10), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(rapor_frame, orient=tk.VERTICAL, command=self.rapor_text.yview)
        self.rapor_text.configure(yscrollcommand=scrollbar.set)
        
        self.rapor_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Kaydetme butonu
        ttk.Button(frame, text="💾 Raporu Dosyaya Kaydet", 
                   command=self.raporu_kaydet).pack(pady=10)
    
    def borc_raporu_goster(self):
        """Borç-alacak raporunu gösterir"""
        rapor = borc_raporu_olustur()
        self.rapor_text.delete(1.0, tk.END)
        self.rapor_text.insert(tk.END, rapor)
    
    def kasa_raporu_goster(self):
        """Kasa raporunu gösterir"""
        try:
            ay = int(self.rapor_ay.get())
            yil = int(self.rapor_yil.get())
            rapor = kasa_raporu_olustur(yil, ay)
        except ValueError:
            rapor = kasa_raporu_olustur()
        
        self.rapor_text.delete(1.0, tk.END)
        self.rapor_text.insert(tk.END, rapor)
    
    def raporu_kaydet(self):
        """Raporu dosyaya kaydeder"""
        rapor = self.rapor_text.get(1.0, tk.END).strip()
        if not rapor:
            messagebox.showwarning("Uyarı", "Önce bir rapor oluşturun!")
            return
        
        dosya_adi = f"rapor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        dosya = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=dosya_adi,
            filetypes=[("Metin Dosyası", "*.txt"), ("Tüm Dosyalar", "*.*")]
        )
        
        if dosya:
            with open(dosya, 'w', encoding='utf-8') as f:
                f.write(rapor)
            messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{dosya}")
    
    def borc_raporu_pdf_kaydet(self):
        """Borç-alacak raporunu PDF olarak kaydeder"""
        dosya_adi = f"borc_alacak_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        dosya = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=dosya_adi,
            filetypes=[("PDF Dosyası", "*.pdf"), ("Tüm Dosyalar", "*.*")]
        )
        
        if dosya:
            try:
                borc_raporu_pdf_olustur(dosya)
                messagebox.showinfo("Başarılı", f"PDF rapor kaydedildi:\n{dosya}")
            except Exception as e:
                messagebox.showerror("Hata", f"PDF oluşturulurken hata oluştu:\n{str(e)}")
    
    def kasa_raporu_pdf_kaydet(self):
        """Kasa raporunu PDF olarak kaydeder"""
        try:
            ay = int(self.rapor_ay.get())
            yil = int(self.rapor_yil.get())
            dosya_adi = f"kasa_raporu_{yil}_{ay:02d}.pdf"
        except ValueError:
            ay = None
            yil = None
            dosya_adi = f"kasa_raporu_tum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        dosya = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=dosya_adi,
            filetypes=[("PDF Dosyası", "*.pdf"), ("Tüm Dosyalar", "*.*")]
        )
        
        if dosya:
            try:
                kasa_raporu_pdf_olustur(yil, ay, dosya)
                messagebox.showinfo("Başarılı", f"PDF rapor kaydedildi:\n{dosya}")
            except Exception as e:
                messagebox.showerror("Hata", f"PDF oluşturulurken hata oluştu:\n{str(e)}")


# ============================================================================
# ANA PROGRAM
# ============================================================================

def main():
    """Ana program fonksiyonu"""
    # Veritabanı tablolarını oluştur
    tablolari_olustur()
    
    # Ana pencereyi oluştur
    root = tk.Tk()
    
    # Uygulama ikonunu ayarla (opsiyonel)
    try:
        root.iconbitmap("icon.ico")
    except:
        pass
    
    # Uygulamayı başlat
    app = EsnafDefterUygulamasi(root)
    
    # Ana döngüyü başlat
    root.mainloop()


if __name__ == "__main__":
    main()


# ============================================================================
# KULLANIM AÇIKLAMASI
# ============================================================================
"""
ESNAF DEFTERİ - KULLANIM KILAVUZU
=================================

1. BORÇ-ALACAK SEKMESİ:
   - Sol taraftan "Yeni Müşteri" butonu ile müşteri ekleyin
   - Müşteri listesinden bir müşteri seçin
   - "Borç Ekle" veya "Ödeme Ekle" butonları ile işlem kaydedin
   - Bakiye otomatik hesaplanır (kırmızı = borçlu, yeşil = alacaklı)

2. GÜNLÜK KASA SEKMESİ:
   - Tarih, tutar ve açıklama girin
   - "Ciro Ekle" ile günlük satışları kaydedin
   - "Gider Ekle" ile harcamaları kaydedin
   - Günlük özet otomatik güncellenir

3. RAPORLAR SEKMESİ:
   - Borç-Alacak veya Kasa raporu oluşturun
   - Raporları metin dosyası olarak kaydedin

VERİTABANI:
   - Tüm veriler "esnaf_defter.db" dosyasında saklanır
   - Bu dosyayı yedekleyerek verilerinizi koruyabilirsiniz

İPUÇLARI:
   - Program internet gerektirmez
   - Veriler otomatik kaydedilir
   - Silme işlemleri onay gerektirir
"""

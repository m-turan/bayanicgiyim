import xml.etree.ElementTree as ET
import requests
import ftplib
import os

# FTP Bilgileri
FTP_CONFIG = {
    "host": "ftp.eterella.com",
    "user": "windamdx", 
    "password": "c_bJ!-PGMwG57#Hx",
    "secure": False,
    "remoteDir": "/public_html/yasinxml"
}

# URL'ler
URLS = {
    "bayanerkek.xml": "https://www.bayanicgiyim.com/TicimaxCustomXml/F71B059327E34DD4BC45E37187ABB781/",
    "bayanbayandeneme.xml": "https://www.bayanicgiyim.com/TicimaxCustomXml/7848E6A17DF247CA82502A496F883C26/"
}

def convert_xml_format(source_url, output_filename):
    try:
        # URL'den XML'i indir
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        # Encoding'i manuel olarak belirt
        response.encoding = 'utf-8'
        xml_content = response.text
        
        # BOM karakterini temizle
        if xml_content.startswith('\ufeff'):
            xml_content = xml_content[1:]
        elif xml_content.startswith('ï»¿'):
            xml_content = xml_content[3:]
        
        # XML'i parse et
        root = ET.fromstring(xml_content)
        
        # Yeni format için root element oluştur
        new_root = ET.Element("products")
        
        # Script elementlerini kopyala
        for script in root.findall("script"):
            new_root.append(script)
        
        # Ürünleri dönüştür
        urunler = root.find("Urunler")
        if urunler is not None:
            for urun in urunler.findall("Urun"):
                product = convert_product(urun)
                new_root.append(product)
        
        # XML'i string olarak al
        tree = ET.ElementTree(new_root)
        xml_string = ET.tostring(new_root, encoding='utf-8', xml_declaration=True)
        
        print(f"{output_filename} dönüştürüldü!")
        return xml_string
        
    except Exception as e:
        print(f"Hata: {e}")
        return None

def convert_product(urun):
    product = ET.Element("product")
    
    # Temel bilgiler
    add_element(product, "id", urun.find("UrunKartiID").text if urun.find("UrunKartiID") is not None else "")
    
    # Stok kodu - ilk secenekten al
    urun_secenek = urun.find("UrunSecenek")
    stok_kodu = ""
    if urun_secenek is not None:
        ilk_secenek = urun_secenek.find("Secenek")
        if ilk_secenek is not None:
            stok_kodu = ilk_secenek.find("StokKodu").text if ilk_secenek.find("StokKodu") is not None else ""
    
    add_element(product, "productCode", stok_kodu)
    add_element(product, "barcode", "")
    
    # Kategori bilgileri
    kategori = urun.find("Kategori").text if urun.find("Kategori") is not None else ""
    add_element(product, "main_category", "İÇ GİYİM")
    add_element(product, "top_category", kategori)
    add_element(product, "sub_category", kategori)
    add_element(product, "sub_category_", "")
    add_element(product, "categoryID", "")
    add_element(product, "category", f"İÇ GİYİM >>> {kategori} >>> {kategori}")
    
    # Diğer bilgiler
    add_element(product, "active", "1")
    add_element(product, "brandID", "98")
    add_element(product, "brand", urun.find("Marka").text if urun.find("Marka") is not None else "")
    add_element(product, "name", urun.find("UrunAdi").text if urun.find("UrunAdi") is not None else "")
    add_element(product, "description",urun.find("OnYazi").text if urun.find("OnYazi") is not None else "")
    
    # Varyantlar
    variants = ET.SubElement(product, "variants")
    urun_adi = urun.find("UrunAdi").text if urun.find("UrunAdi") is not None else ""
    if urun_secenek is not None:
        for secenek in urun_secenek.findall("Secenek"):
            variant = convert_variant(secenek, urun_adi)
            variants.append(variant)
    
    # Resimler
    resimler = urun.find("Resimler")
    if resimler is not None:
        resim_list = resimler.findall("Resim")
        for i, resim in enumerate(resim_list[:3], 1):
            add_element(product, f"image{i}", resim.text)
    
    # Fiyat bilgileri
    if urun_secenek is not None and len(urun_secenek.findall("Secenek")) > 0:
        ilk_secenek = urun_secenek.find("Secenek")
        satis_fiyati = ilk_secenek.find("SatisFiyati").text if ilk_secenek.find("SatisFiyati") is not None else "0"
        alis_fiyati = ilk_secenek.find("AlisFiyati").text if ilk_secenek.find("AlisFiyati") is not None else "0"
        
        # Virgülü noktaya çevir
        satis_fiyati = satis_fiyati.replace(",", ".")
        alis_fiyati = alis_fiyati.replace(",", ".")
        
        add_element(product, "listPrice", satis_fiyati)
        add_element(product, "price", alis_fiyati)
        add_element(product, "tax", "0.1")
        add_element(product, "currency", "TRY")
        add_element(product, "desi", "1")
        
        # Toplam stok
        total_quantity = sum(int(secenek.find("StokAdedi").text) for secenek in urun_secenek.findall("Secenek") if secenek.find("StokAdedi") is not None)
        add_element(product, "quantity", str(total_quantity))
    
    return product

def convert_variant(secenek, urun_adi=""):
    variant = ET.Element("variant")
    
    # Renk ve beden bilgilerini al
    ek_secenek = secenek.find("EkSecenekOzellik")
    renk = ""
    beden = ""
    
    if ek_secenek is not None:
        ozellikler = ek_secenek.findall("Ozellik")
        for ozellik in ozellikler:
            tanim = ozellik.get("Tanim", "")
            deger = ozellik.get("Deger", "")
            if "renk" in tanim.lower() or "color" in tanim.lower():
                renk = deger
            elif "beden" in tanim.lower() or "size" in tanim.lower():
                beden = deger
    
   
    
    add_element(variant, "name1", "Renk")
    add_element(variant, "value1", renk)
    add_element(variant, "name2", "Beden")
    add_element(variant, "value2", beden)
    
    add_element(variant, "quantity", secenek.find("StokAdedi").text if secenek.find("StokAdedi") is not None else "0")
    add_element(variant, "barcode", "")
    
    return variant

def add_element(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = text

def upload_xml_to_ftp(xml_content, remote_file):
    try:
        # FTP bağlantısı kur
        ftp = ftplib.FTP(FTP_CONFIG["host"])
        ftp.login(FTP_CONFIG["user"], FTP_CONFIG["password"])
        
        # Remote dizine geç
        ftp.cwd(FTP_CONFIG["remoteDir"])
        
        # XML içeriğini doğrudan yükle
        from io import BytesIO
        xml_buffer = BytesIO(xml_content)
        ftp.storbinary(f'STOR {remote_file}', xml_buffer)
        
        ftp.quit()
        print(f"{remote_file} FTP'ye yüklendi!")
        return True
        
    except Exception as e:
        print(f"FTP hatası: {e}")
        return False

def main():
    # Her URL için dönüştürme ve yükleme
    for filename, url in URLS.items():
        print(f"{filename} işleniyor...")
        
        # XML dönüştür
        xml_content = convert_xml_format(url, filename)
        if xml_content:
            # FTP'ye yükle
            upload_xml_to_ftp(xml_content, filename)

if __name__ == "__main__":
    main()

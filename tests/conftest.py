import sys, os
# src'yi import yoluna ekle (uygulama src/ içinden flat import kullanıyor)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

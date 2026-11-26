# Kurulum ve kullanım

Yeni bir Linux sunucuda systemd, Python 3, Nginx ve Mosquitto kullanın. HTTPS ve MQTT uçları için DNS ve TLS sertifikalarını hazırlayın. Dosya yolları ve komutlar [İngilizce kurulum kılavuzunda](setup.md) yer alır.

1. Mosquitto'da `serverpulse_ingest` hesabını oluşturun. ACL ve broker örneklerini uygulayın. İç MQTT dinleyicisini loopback'te, ajanların kullandığı TLS dinleyicisini 8883'te çalıştırın.
2. Cihaz oluşturma ve iptal betiklerini kök sahipliğiyle kurun. API hesabına sudo üzerinden yalnızca bu iki komutu çalıştırma yetkisi verin.
3. `backend/` altında bir Python sanal ortamı oluşturun ve `requirements.txt` bağımlılıklarını kurun. `.env.example` dosyasından `.env` oluşturun. İçe alım parolasını, genel MQTT adını ve panelin HTTPS origin değerini girin.
4. API'yi `main_v2:app` ile loopback üzerinde çalıştırın. Nginx örneğini gerçek alan adınız ve sertifikalarınızla yapılandırın. `frontend/` dosyalarını web köküne yerleştirin. `maintenance.py` betiğini API hesabıyla düzenli çalışacak şekilde zamanlayın.
5. Windows'ta `agent/` altında Python sanal ortamı oluşturup ajan bağımlılıklarını kurun. `SERVERPULSE_API_URL` değerine panel adresini verin ve `main.py` dosyasını çalıştırın. Özel MQTT CA kullanıyorsanız `SERVERPULSE_MQTT_CA` değerini ilgili CA dosyasına ayarlayın.
6. Panele kayıt olun ve giriş yapın. Eşleştirme kodunu oluşturup on dakika içinde ajana girin. Panelde cihaz durumunu, son ölçümleri ve geçmişi kontrol edin. Erişimi kaldırmak için cihazı panelden iptal edin ve ajandaki yerel eşleştirmeyi temizleyin.

Kurulum paketi için PyInstaller ile `ServerPulse.spec`, ardından Inno Setup ile `setup.iss` dosyasını kullanın. Panelden indirme özelliği için hazırladığınız yükleyiciyi kendi web sunucunuzda `/downloads/ServerPulseSetup.exe` yoluna koyun.

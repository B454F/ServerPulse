# ServerPulse

ServerPulse, Windows cihazlarından işlemci, bellek ve disk ölçümlerini toplar. Web paneli cihaz durumunu, son ölçümleri ve geçmişi gösterir. Windows ajanı veriyi MQTT üzerinden gönderir. FastAPI servisi veriyi doğrular, SQLite'a yazar ve panel API'sinde sunar.

[English](README.md) · [Kurulum ve kullanım](docs/kurulum.tr.md) · [Mimari ve düzenlenebilir çizimler](docs/architecture.md)

| Dizin | İçerik |
| --- | --- |
| `backend/` | Kimlik doğrulama, cihaz yönetimi, MQTT ve SQLite |
| `frontend/` | HTML, CSS ve JavaScript web paneli |
| `agent/` | Windows masaüstü ajanı ve kurulum paketi tanımları |
| `deploy/` | Nginx ve Mosquitto örnekleri, broker cihaz yönetimi betikleri |
| `docs/` | Kurulum adımları ve düzenlenebilir diyagramlar |

Panelde oturum açın, tek kullanımlık kod üretin ve Windows ajanına HTTPS adresiyle birlikte girin. Cihazın durumunu ve telemetri geçmişini panelden izleyebilir, gerektiğinde cihaz erişimini iptal edebilirsiniz.

Telemetri cihaz adı, işletim sistemi ve yerel/genel IP adreslerini içerir. Ajan genel IP adresini bulmak için ipify'a sorgu gönderir. Zamanlanan bakım betiği yedi günden eski telemetriyi siler.

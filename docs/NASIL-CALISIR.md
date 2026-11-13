# Bearing Pulse nasıl çalışır? (Türkçe, baştan sona)

Bu doküman projeyi kod bilmeden okunacak şekilde anlatır: **ne yaptık, neden öyle yaptık,
hangi dosyada**. Mülakatta "şu satır ne yapıyor?" sorusuna cevap verebilmen için yazıldı.
Sırayla oku; her bölüm bir öncekinin üstüne kurulu. En sonda mülakat soruları ve cevapları var.

---

## 0. Büyük resim

```
 Rulman titreşir ──► ivmeölçer (ADXL345) ──► ESP32 ──MQTT──► Mosquitto ──► köprü ──► InfluxDB ──► Grafana
                       saniyede 3200 ölçüm      │                 (posta      (çevirmen)  (zaman serisi  (grafik +
                                                │                  ofisi)                  veritabanı)    alarm)
                                       özellik çıkar + model
                                       "normal / iç / bilye / dış"
```

- **Rulman:** mili döndüren bilyeli yatak. Arızalanınca makine durur; erken fark etmek para kazandırır.
  Werover'ın rüzgâr türbinlerinde yaptığı iş bunun büyüğü.
- **Fikir:** arızalı rulman farklı titreşir. Titreşimi ölç, bilgisayara "bu normal mi arızalı mı" öğret.
- **Donanım henüz yok.** O yüzden ESP32'nin yerine bir **simülatör** (`sim/node_sim.py`) koyduk:
  gerçek laboratuvar kayıtlarını (CWRU) ESP32 gönderiyormuş gibi gönderiyor. Donanım gelince
  simülatörü çıkarıp ESP32'yi takacağız, geri kalan her şey aynı kalacak.

Proje fazları:

| Faz | Ne | Durum |
|-----|----|-------|
| 1 | Hazır veriyle makine öğrenmesi | Bitti |
| 2 | Sensör → MQTT → veritabanı → Grafana | Yazılım bitti (simülatörle), donanım bekliyor |
| 3 | Özellikleri cihazın kendisinde hesaplamak | C kodu bitti ve test edildi, kendi verin donanım bekliyor |
| 4 | Modeli cihaza gömmek + alarm | C modeli ve Grafana alarmı bitti, cihazda çalıştırma donanım bekliyor |
| 5 | Sahaya hazır: güvenlik, bağlantı kopması, OTA, uyku | TLS + şifre bitti, gerisi donanım bekliyor |
| 6 | Kendi devre kartın (PCB) | Başlanmadı |

---

## 1. Faz 1: Hazır veriyle arıza tespiti

Dosyalar: `src/bearing.py` (bütün fonksiyonlar), `notebooks/01…06` (adım adım deneyler),
`docs/01-ml-on-cwru-data.md` (uzun anlatım).

### 1.1 Veri: CWRU

Case Western Reserve Üniversitesi bir motorun rulmanına bilerek küçük hasarlar açmış
(0.007", 0.014", 0.021" çapında; elektrikle aşındırarak) ve titreşimi kaydetmiş.
4 durum var: **normal, iç bilezik (inner), bilye (ball), dış bilezik (outer)**. Her durum 4 farklı
yükte (0, 1, 2, 3 beygir gücü) kaydedilmiş.

`bearing.py` içinde:
- `FILES = {97: ("normal", 0), ...}`: hangi dosya numarası hangi durum ve hangi yük. Bu bir sözlük.
  Sol taraf dosya numarası, sağ taraf (durum, yük).
- `load(num)`: bir `.mat` dosyasını açar, titreşim sinyalini ve mil hızını (rpm) döndürür.
  İçinde iki **veri tuzağı** düzeltiliyor. İkisi de mülakatta anlatılacak güzel hikâyeler:
  1. **Normal kayıtlar 48 kHz, arızalı kayıtlar 12 kHz.** Yani normal kayıt saniyede 4 kat fazla ölçüm
     içeriyor. Düzeltmezsek model "normal"i titreşimden değil örnekleme hızından tanır. Bu bir hile olur.
     `signal.resample_poly(x, 1, 4)` normal kayıtları 12 kHz'e indiriyor. Nasıl anladık? Spektrumdaki
     tepeler ancak 48 kHz kabul edilince arızalı kayıtlarla aynı yere oturuyor.
  2. **`99.mat` içinde 98'in verisi de var.** Bu yüzden anahtar dosya numarasıyla eşleşmeli:
     `m[f"X{num:03d}_DE_time"]`.

### 1.2 Fizik: arıza frekansları

Bir bilye iç bilezikteki çatlağın üstünden her geçtiğinde küçük bir "tık" olur. Saniyede kaç tık olacağı
**rulmanın geometrisinden ve mil hızından** hesaplanabilir. `fault_freqs(rpm)` bunu yapıyor:

- `BPFO`: dış bilezik arıza frekansı (Ball Pass Frequency Outer)
- `BPFI`: iç bilezik arıza frekansı
- `BSF`: bilyenin kendi etrafında dönme frekansı (bilye arızası için)
- `FTF`: kafes frekansı

1797 rpm'de BPFO ≈ 107 Hz, yani dış bilezikte arıza varsa saniyede ~107 tık duyulur.
Dosyanın en altındaki `assert`'ler bu formüllerin CWRU'nun yayınladığı değerleri verdiğini kontrol ediyor.
Kod kendini test ediyor.

### 1.3 Neden "zarf analizi"?

Sorun şu: tıklar çok kısa ve rulman yuvasını **binlerce Hz'de** çınlatıyor (çan gibi). Düz FFT'ye
(frekans analizine) bakınca 107 Hz'de bir şey görmezsin; enerji 2-5 kHz'deki çınlamada.
Çözüm üç adım (`envelope_spectrum`):

1. **Bant geçiren filtre (2-5 kHz):** sadece çınlamayı bırak, gerisini at. `signal.butter(4, ...)`
   4. dereceden Butterworth filtre; `sosfiltfilt` ileri-geri uygular, böylece sinyal zamanda kaymaz.
2. **Hilbert zarfı:** çınlamanın "zarfını" (dış hatlarını) çıkar. Her tıkta zarf yükselir.
   `np.abs(signal.hilbert(...))`.
3. **Zarfın FFT'si:** zarf saniyede kaç kez yükseliyor? Cevap tam olarak arıza frekansı.

Sonuç `images/01-envelope-spectrum.png`'de: tepeler tam hesaplanan BPFO/BPFI'nin üstünde.

### 1.4 Özellikler (features)

Makine öğrenmesi modeli ham sinyali değil, sinyali özetleyen sayıları alır. `features()` her
2048 ölçümlük **pencere** (≈0.17 s) için 17 sayı çıkarıyor:

| Özellik | Ne anlatır |
|---------|------------|
| `rms` | Ortalama titreşim gücü ("ne kadar sallanıyor") |
| `peak` | En büyük tek darbe |
| `crest` = peak / rms | Darbeli mi? Arızalı rulmanda sivri tepeler olduğu için yüksek |
| `kurtosis` | Sivrilik. Düz gürültüde 0, darbelerde yüksek |
| `skewness`, `std` | Asimetri, yayılma |
| `band0..band7` | Spektrumu 8 parçaya böl, her parçada enerjinin payı (log ölçekte) |
| `env_BPFO`, `env_BPFI`, `env_2BSF` | Zarf spektrumunda tam arıza frekanslarındaki yükseklik |

`env_2BSF` neden 2×BSF? Arızalı bilye her dönüşünde **iki** bileziğe de çarpar.

### 1.5 Model: Random Forest

**Random Forest** = çok sayıda **karar ağacı**. Her ağaç "rms 0.05'ten büyük mü? → evet → kurtosis 3'ten
büyük mü? → …" gibi sorular sorup bir cevaba varır; ağaçlar oy verir, çoğunluk kazanır. Neden bu?
Küçük veri ile iyi çalışır, açıklanabilir, ve en önemlisi (Faz 4) **if/else'e çevrilip ESP32'ye gömülebilir**.

**Veri sızıntısına dikkat:** her kaydın ilk %70'i eğitim, son %30'u test. Rastgele bölseydik
yan yana duran (neredeyse aynı) pencereler hem eğitimde hem testte olurdu, model ezberleyip yüksek
skor alırdı. Buna **data leakage** denir.

### 1.6 Sonuçlar ve asıl öğrenilen

| Test | 17 özellik | Sadece 3 zarf özelliği |
|------|-----------|------------------------|
| Aynı yük, zamanla bölünmüş | %100 | %100 |
| 0 HP'de eğit → 1/2/3 HP'de test | %100 | %100 |
| 0.007" hasarla eğit → 0.021" hasarla test | %59.3 | **%97.7** |

**Hikâye:** her şey %100 görünüyordu. Ama daha büyük bir hasarla test edince %59'a düştü. Neden?
Model spektrumun *şeklini* ezberlemişti ve o şekil hasar büyüklüğüne göre değişiyor. Zarf özellikleri ise
**fiziğe** bağlı (geometri + mil hızı), hasar büyüklüğüne bağlı değil. Sadece onları kullanınca %97.7.
Özellik seti test skoruna bakılarak değil, ayrı bir doğrulamayla seçildi (yoksa yine hile olurdu).

**Sınırlar (README → Limitations):** 0.014" hasarlar her yöntemle ~%37, çünkü bu kayıtlarda arıza izi
sinyalde yok. Model olmayanı öğrenemez. Ayrıca **güven skoru** (`predict_proba`) iyi bir uyarı:
model yanılmadan önce güveni düşüyor.

---

## 2. Faz 2-4: Gerçek sensöre uyarlamak

### 2.1 Büyük sorun: sensörümüz yavaş

ADXL345 saniyede **en fazla 3200** ölçüm alabiliyor. Bir sinyalde görebileceğin en yüksek frekans
örnekleme hızının yarısı (Nyquist): **1600 Hz**. Faz 1'in sihirli 2-5 kHz bandı **görünmüyor**.
Bu yüzden zarf özelliklerini kullanamıyoruz. Bunu bilmek ve söylemek mülakatta artı puan.

Çözüm: ucuz özellikler. Dosya: `src/edge.py`.

- `FS = 3200`, `WINDOW = 1024`: pencere 1024 ölçüm = 0.32 s ≈ milin 9.6 turu (yeterince tur görsün).
  1024 = 2¹⁰ çünkü FFT 2'nin kuvvetlerinde hızlı çalışır. 1024 float = 4 kB, ESP32'nin hafızasına sığar.
- `adxl345(x12k)`: CWRU kaydını **ADXL345 ölçseydi ne görürdük**e çevirir. Donanım olmadan
  gerçekçi veri üretmenin yolu bu:
  1. `resample_poly(x, 4, 15)`: 12000 × 4 / 15 = 3200 Hz. Önce filtreler, sonra seyreltir
     (filtresiz seyreltmek yüksek frekansları sahte alçak frekanslara çevirir: *aliasing*).
  2. `np.clip(x, -16, 16)`: sensör ±16 g'nin dışını ölçemez.
  3. `round(x / 0.0039) * 0.0039`: sensör 3.9 mg'lık basamaklarla ölçer (12 bitlik çözünürlük).
- `features(w)`: 12 özellik: `rms, peak, crest, kurtosis` + `band0..band7`.
  - `kurt = m4 / m2**2 - 3`: kurtosis'in tanımı (dördüncü moment / varyansın karesi). `-3` ile
    normal dağılımlı gürültü 0 olur ("excess kurtosis").
  - `np.hanning`: FFT'den önce pencerenin kenarlarını yumuşatır. Yoksa pencerenin keskin kesilmesi
    sahte frekanslar üretir (*spectral leakage*).
  - `spec[1:]`: 0 Hz (DC) atılıyor. Orada sadece yerçekimi ve sensör ofseti var, arıza bilgisi yok.
  - `reshape(8, -1).sum(1)`: 512 frekans kutusu → 8 bant × 64 kutu. Her kutu 3.125 Hz, her bant 200 Hz.
  - `log10(bands / bands.sum())`: enerjinin **payı**, logaritmik. Pay kullanıyoruz çünkü sensör biraz
    gevşek ya da sıkı takılsa toplam güç değişir ama dağılım değişmez.

### 2.2 Aynı kodu ESP32 için C'ye çevirmek

ESP32 Python çalıştıramaz; C/C++ çalıştırır. `firmware/lib/bearing_edge/`:

- `bearing_edge.h`: "sözleşme". İki fonksiyon ilan eder: `be_features` (1024 ölçüm → 12 sayı) ve
  `be_predict` (12 sayı → sınıf + olasılıklar). `extern "C"` satırı Arduino'nun C++ derleyicisinin de
  bunu kullanabilmesi için.
- `features.c`: `edge.features()`'ın satır satır C karşılığı. Önemli kararlar:
  - `static float re[N], im[N];`: 8 kB'lık çalışma alanı. `static` diyerek görevin yığınına (stack)
    değil kalıcı belleğe koyuyoruz; ESP32'de görev yığını küçük, taşarsa cihaz çöker.
  - Toplamlar `double` ile: 1024 sayının karesini `float` ile toplarken hassasiyet kaybolur.
  - `fft()`: kütüphane kullanmadan elle yazılmış klasik radix-2 FFT. Önce "bit ters çevirme"
    ile sıralar, sonra "kelebek" adımlarıyla birleştirir. Bağımlılık yok, bu yüzden hem
    ESP32'de hem bilgisayarda aynen derleniyor.
- `model.c`: **elle yazılmadı, üretildi** (aşağıda).

### 2.3 Modeli eğitip C'ye dökmek: `src/train_edge.py`

- `N_TREES, MAX_DEPTH = 10, 6`: küçük orman. 10 ağaç, her biri en fazla 6 soru derinliğinde →
  ~14.5 kB C kodu. ESP32'ye rahat sığar.
- `dataset(loads)`: CWRU kayıtlarını `adxl345()`'ten geçirip pencerelere bölüp özellik çıkarıyor.
- **Dürüst doğruluk ölçümü (leave-one-load-out):** bir yükü tamamen dışarıda bırak, diğer üçüyle eğit,
  dışarıdakiyle test et; dört kez tekrarla.

  | Dışarıda bırakılan yük | Doğruluk |
  |---|---|
  | 0 HP | %75.9 |
  | 1 HP | %75.8 |
  | 2 HP | %100 |
  | 3 HP | %81.6 |
  | **Ortalama** | **%83.3** |

  Faz 1'deki %100'den düşük, çünkü 3200 Hz'de arıza izi zayıf. Bu beklenen ve açıklanabilir bir sonuç.
- `tree_to_c()`: sklearn'ün her ağacını iç içe `if (feat[9] <= -1.03) { ... } else { ... }` kodlarına
  çeviriyor. Yaprakta o yaprağa düşen eğitim örneklerinin sınıf dağılımını `prob[]`'a ekliyor.
- `export()`: 10 ağacı + `be_predict` fonksiyonunu `model.c`'ye yazıyor. `be_predict` her ağacı çağırır,
  olasılıkları 10'a böler (ortalama), en yüksek olasılıklı sınıfı döndürür.
- Neden `micromlgen` gibi hazır araç değil de kendimiz? 40 satır, bağımlılık yok, ne ürettiğini satır satır
  biliyoruz ve test edebiliyoruz.

### 2.4 Üç kopya aynı mı? `tests/test_edge.py`

Aynı hesabın üç hali var: Python (eğitim için), C (cihaz için), bilgisayarda derlenmiş C (test için;
`edge.lib()` C kodunu `cc` ile derleyip `ctypes` ile Python'dan çağırıyor). Testler:

1. `test_features`: Python ve C özellikleri her sınıfta ve yükte aynı mı? En büyük fark 0.00002
   (kurtosis'te, float yuvarlamasından).
2. `test_model`: C modeli sklearn ile aynı olasılıkları veriyor mu? Fark < 0.0000001, etiketler %100 aynı.
3. `test_end_to_end`: ham sinyal → C özellik → C model, yani ESP32'nin yapacağı yol. Dış bilezik
   kaydında %100 "outer".

Çalıştırmak: `python tests/test_edge.py` → sonunda `ok`.

### 2.5 Veri yolu: MQTT → InfluxDB → Grafana

**MQTT** = cihazlar için hafif mesajlaşma. Cihaz bir "konu"ya (topic) mesaj atar, isteyen o konuya abone olur.
**Mosquitto** bu postaneyi işleten program (broker).

Konu yapısı: `bearingpulse/<düğüm>/<tür>`, örn. `bearingpulse/node1/model`. Üç tür mesaj:

| Tür | İçerik | Ne zaman |
|---|---|---|
| `raw` | Ham ölçümler (256'lık paketler) | Faz 2: her şeyi gönder |
| `features` | 12 özellik | Faz 3: cihaz özetler, çok daha az veri |
| `model` | 12 özellik + `label` + `confidence` | Faz 4: cihaz karar verir |

**`sim/node_sim.py`**: sahte düğüm. CWRU kaydını `adxl345()`'ten geçirip gerçek zamanlı hızda
(`time.sleep` ile) MQTT'ye gönderiyor. `--cycle` ile normal → iç → bilye → dış sırayla döner.
Mesaja `truth` (gerçek cevap) ekliyor; bu sadece simülatörde var, Grafana'da "model ne dedi / gerçek neydi"
yan yana görünsün diye.

**`bridge/mqtt_to_influx.py`** (köprü): MQTT'yi dinler, mesajları veritabanına yazar.
- `to_lines()`: JSON mesajı InfluxDB'nin "line protocol" formatına çevirir:
  `model,node=node1,truth=inner rms=0.12,...,label="inner",fault=1.0 1794577285000000000`
  (ölçüm adı, etiketler, alanlar, nanosaniye zaman damgası).
- `fault` alanı: model etiketi metin (`"inner"`); Grafana alarmı sayı ister. Arıza = 1, normal = 0.
- **Toplu yazma:** her mesajı ayrı yazmak yetişmiyor (her yazma ~0.5 s bekliyor), o yüzden mesajlar
  `pending` listesinde birikir, `flush_forever()` saniyede bir hepsini tek seferde yazar.
- `lock`: MQTT bir iş parçacığında (thread), yazma başka birinde; aynı listeye aynı anda dokunmasınlar.
- Hata yönetimi: bozuk mesaj köprüyü öldürmez (atlanır); veritabanı kapalıysa paket geri konur ve
  sonra tekrar denenir. Veri kaybolmaz.
- `on_connect` içinde abone olmak: bağlantı koparsa yeniden bağlanınca aboneliği kendiliğinden yeniler.

**InfluxDB 3**: zaman serisi veritabanı. "Şu anda şu değer" türü veriler için yapılmış.

**Grafana** (`grafana/`): panolar ve alarm. `provisioning/` klasörü sayesinde ayarlar elle tıklanmaz,
dosyadan yüklenir. Proje kopyalanınca pano da gelir. Panoda: cihaz ne diyor, güveni, tahmin-gerçek
karşılaştırması, ham titreşim, RMS/kurtosis, bant enerjileri.

**`scripts/stack.sh`**: hepsini tek komutla açar/kapatır (`start` / `stop`). Her programı arka planda
başlatır, işlem numarasını (PID) `.local/pids/`'e yazar (kapatırken lazım), InfluxDB hazır olana kadar
bekler (`/health`), sonra köprüyü başlatır. Tüm veri ve loglar `.local/`'de; git'e girmez.

---

## 3. Faz 5: Sahaya hazır (yazılım kısmı)

### 3.1 Güvenlik: TLS + şifre

Sahada sensör Wi-Fi üzerinden konuşacak. Önlem almazsak ağdaki herkes veriyi okur, sahte "her şey normal"
mesajı gönderebilir. İki kilit:

- **TLS** (HTTPS'teki kilit): bağlantı şifreli ve cihaz konuştuğu sunucunun gerçekten bizimki olduğunu
  doğrular.
- **Kullanıcı adı + şifre:** broker sadece tanıdığı cihazları kabul eder.

`scripts/make_certs.sh`:
- Kendi küçük **sertifika otoritemizi (CA)** kuruyor (`ca.crt`). Gerçek bir sitede bu işi
  Let's Encrypt gibi kurumlar yapar; kapalı bir sistem için kendi CA'n yeterli ve yaygın.
- Broker için bu CA'nın imzaladığı bir sertifika üretiyor. `SAN` satırı sertifikanın hangi adreslerde
  geçerli olduğunu söylüyor (localhost, 127.0.0.1, istersen dizüstünün ağ IP'si; ESP32 o IP'ye bağlanacak).
- `.env` yoksa rastgele bir şifre üretiyor (`openssl rand -hex 16`) ve `mosquitto_passwd` ile şifreyi
  **hash'leyerek** saklıyor (düz metin değil).
- Hepsi `.local/` ve `.env`'de, ikisi de `.gitignore`'da. **Şifre asla GitHub'a gitmez.**

`services/mosquitto.conf`: iki kapı.
- `1883`, sadece `127.0.0.1`: sadece bu bilgisayardaki programlar (köprü) girebilir, şifresiz.
- `8883`, tüm ağ: dışarıdan gelen cihazlar için. TLS + şifre zorunlu (`allow_anonymous false`).
- `per_listener_settings true`: her kapının kuralı ayrı olsun diye.

Simülatör `--tls` ile tam ESP32 gibi bağlanıyor (8883, CA ile doğrulama, `.env`'den şifre).
Test edildi: doğru şifre → veri geldi; yanlış şifre ve şifresiz → `not authorised`, reddedildi.

### 3.2 Alarm: `grafana/provisioning/alerting/rules.yml`

"Bir düğümün son 1 dakikadaki tahminlerinin yarıdan fazlası arıza ise ve bu 30 saniye sürerse alarm."

- **A:** her düğüm için son 60 saniyedeki `fault` ortalaması (0.8 = pencerelerin %80'i arıza dedi).
- **B:** son değeri al. **C:** 0.5'ten büyük mü?
- `for: 30s`: koşul 30 saniye sürmeli.
- Ortalama + bekleme sayesinde **tek bir yanlış tahmin alarm çaldırmaz**. Sahada yanlış alarm, alarmın
  ciddiye alınmamasına yol açar.
- `noDataState: OK`: veri hiç gelmiyorsa bunu "arıza" sayma; cihazın kapanması ayrı bir sorun.

Test edildi: iç bilezik verisi → alarm çaldı; normal veri → sustu.

### 3.3 Henüz yapılmayanlar (donanım bekliyor)

- **ESP32'nin ana programı:** Wi-Fi'ye bağlanmak, ADXL345'ten okumak, `be_features` + `be_predict`'i
  çağırmak, TLS'li MQTT ile göndermek. Kütüphane hazır; onu kullanan ana program donanımla birlikte yazılacak.
- **Bağlantı kopması (15):** Wi-Fi gidince sonuçları bellekte tutup gelince göndermek.
- **OTA (16):** cihazı kablosuz güncellemek. **Deep sleep:** ölçümler arasında uyuyup pil korumak.
- **Kendi verin (11), kendi modelin (12), güvenilirlik testi (14):** fanla.

---

## 4. Kendin çalıştır

```bash
cd ~/Desktop/projects/bearing-pulse
source .venv/bin/activate
python src/bearing.py                                   # Faz 1 kendi testi → ok
python tests/test_edge.py                               # C = Python testleri → ok
scripts/stack.sh start                                  # sistemi aç
python sim/node_sim.py --mode model --cycle --tls       # sahte sensör (Ctrl+C ile durdur)
```

Tarayıcıda http://localhost:3000 → "Bearing Pulse" panosu. İş bitince `scripts/stack.sh stop`.

---

## 5. Mülakatta sorulabilecekler

**"Neden zarf analizi?"**
Rulman arızası kısa darbeler üretir; darbeler yuvayı kHz'lerde çınlatır. Düz FFT'de arıza frekansı
görünmez. Bant geçirip zarfı çıkarınca darbe tekrar hızı, yani arıza frekansı ortaya çıkar.

**"%100 aldın, model iyi mi?"**
Hayır, %100 aynı koşulda. Daha büyük hasarla test edince %59'a düştü; model fiziği değil spektrum şeklini
ezberlemişti. Fizik tabanlı zarf özellikleriyle %97.7'ye çıkardım. Ayrıca CWRU yapay hasar, tek düzenek;
saha doğruluğu değil.

**"Veri sızıntısını nasıl önledin?"**
Pencereleri rastgele değil zamana göre böldüm (kaydın başı eğitim, sonu test). Özellik setini test skoruna
bakarak değil ayrı çapraz doğrulamayla seçtim.

**"ESP32'de neden zarf analizi yok?"**
ADXL345 en fazla 3200 Hz örnekliyor, Nyquist 1600 Hz; çınlama bandı 2-5 kHz. Fiziksel olarak görünmüyor.
Bu yüzden zaman istatistikleri + 1600 Hz'e kadar bant enerjileri kullandım; doğruluk %83 (yük değişimine karşı).
Daha iyi sonuç için daha hızlı bir sensör gerekir (ör. analog MEMS + ADC).

**"Modeli ESP32'ye nasıl koydun?"**
10 ağaçlı, 6 derinlikli küçük bir Random Forest eğittim, her ağacı if/else C koduna çeviren bir betik yazdım.
C kodunu bilgisayarda derleyip Python ile karşılaştıran testler yazdım: olasılık farkı < 10⁻⁷.

**"Neden ham veri yerine özellik ya da karar gönderiyorsun?"**
Ham veri saniyede ~3200 sayı; özellikler pencere başına 12 sayı. Bant genişliği ve pil için. Sahada
(rüzgâr türbini) bağlantı pahalı ve kesintili.

**"Güvenliği nasıl sağladın?"**
Dışarıya açık port sadece 8883: TLS (kendi CA'm ile sunucu doğrulama) + kullanıcı/şifre (hash'li saklanıyor).
Şifresiz port sadece localhost'ta. Sırlar git'e girmiyor.

**"Yanlış alarmı nasıl önlüyorsun?"**
Alarm tek pencereye değil 1 dakikalık ortalamaya bakıyor ve 30 saniye sürmesini bekliyor. Ayrıca model
güven skoru gönderiyor; düşük güven "emin değilim" demek.

**"Bir şeyi yeniden yapsan neyi farklı yapardın?"**
Daha hızlı örnekleyen sensör seçerdim (zarf analizi cihazda da çalışsın). Ve gerçek, yavaş ilerleyen aşınma
verisi toplardım; CWRU'daki hasarlar yapay ve sabit.

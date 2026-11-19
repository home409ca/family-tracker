# Family Tracker

Aplikacja Android 0.2.1 i integracja Home Assistant 0.2.2. Family Tracker przesyła lokalizację i stan baterii telefonu. Nazwę Wi-Fi (SSID) można udostępnić osobno.

## Aktualizacja integracji HA

Dodaj `https://github.com/home409ca/family-tracker` w HACS jako własne repozytorium typu **Integracja**. Pobierz Family Tracker **0.2.2** i zrestartuj Home Assistant Core. Przy instalacji ręcznej skopiuj katalog `custom_components/family_tracker` do konfiguracji HA. Przy aktualizacji zachowaj istniejący wpis integracji oraz ustawienia telefonu.

## Pobranie i parowanie

Zainstaluj [FamilyTracker.apk](FamilyTracker.apk) lub zeskanuj QR do pobrania APK w **Ustawienia → Urządzenia i usługi → Family Tracker → Konfiguruj**. Kod prowadzi do [pobrania APK z ostatniego wydania](https://github.com/home409ca/family-tracker/releases/latest/download/FamilyTracker.apk). W tym samym formularzu możesz wygenerować jednorazowy QR parowania, który skanujesz w aplikacji Family Tracker.

## Aktualizacje z aplikacji

Przycisk **Aktualizuj** jest dostępny również na ekranie parowania. Aplikacja pobiera nowsze wydanie i sprawdza identyfikator aplikacji oraz podpis. Instalację zatwierdzasz w Androidzie. Przy pierwszym użyciu Android może poprosić o zgodę na instalowanie aktualizacji z Family Tracker.

W każdym publicznym wydaniu GitHub w sekcji **Assets** umieść podpisany plik o dokładnej nazwie **`FamilyTracker.apk`**. Podnieś `versionCode` przy kolejnych wydaniach APK i zachowaj klucz podpisujący.

## Rozparowanie

**Rozparuj telefon** zatrzymuje udostępnianie. Integracja usuwa urządzenie i encje po zweryfikowaniu poświadczenia telefonu. Gdy połączenie przerwie się, otwórz Family Tracker i ponów rozparowanie. Wpis pozostawiony przez starszą wersję usuń z HA akcją `family_tracker.remove_device`, używając `device_id` zwróconego przez `family_tracker.list_devices`.

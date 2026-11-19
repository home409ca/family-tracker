# Family Tracker 0.2.0

Family Tracker przesyła lokalizację i stan baterii z telefonu z Androidem do Home Assistant. Nazwę sieci Wi-Fi (SSID) można udostępniać osobno.

## Instalacja integracji

W HACS dodaj `https://github.com/home409ca/family-tracker` jako własne repozytorium w kategorii **Integracja**. Pobierz **Family Tracker** i zrestartuj Home Assistant Core. Następnie wejdź w **Ustawienia → Urządzenia i usługi → Dodaj integrację** i wybierz Family Tracker.

Przy instalacji ręcznej skopiuj folder `custom_components/family_tracker` do katalogu `custom_components` w konfiguracji Home Assistant, a następnie zrestartuj Core. Integracja została przetestowana na Core 2026.10.4.

## Instalacja aplikacji

Zainstaluj [FamilyTracker-0.2.0.apk](FamilyTracker-0.2.0.apk) na telefonie z Androidem 10 lub nowszym. W integracji Family Tracker wybierz **Konfiguruj**, nadaj telefonowi nazwę i pobierz kod QR. Zeskanuj kod w aplikacji. Kod jest ważny przez pięć minut.

APK jest podpisany tym samym kluczem co wcześniejsza wersja pilotażowa. Aktualizacja z tego APK zachowuje parowanie.

## Aktualizacje

Aplikacja otwiera najnowsze [wydanie GitHub](https://github.com/home409ca/family-tracker/releases/latest). Przy publikacji nowej wersji dołącz podpisany APK jako plik wydania. HACS aktualizuje integrację Home Assistant osobno.

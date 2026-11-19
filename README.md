# Family Tracker

Integracja Home Assistant 0.2.1 i aplikacja Android 0.2.0. Aplikacja przesyła lokalizację i stan baterii. Nazwę sieci Wi-Fi (SSID) można udostępniać osobno.

## Instalacja w Home Assistant

W HACS dodaj `https://github.com/home409ca/family-tracker` jako własne repozytorium w kategorii **Integracja**. Pobierz integrację **Family Tracker** i zrestartuj Home Assistant Core. Następnie przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację** i wybierz Family Tracker.

Przy instalacji ręcznej skopiuj folder `custom_components/family_tracker` do katalogu `custom_components` w konfiguracji Home Assistant i zrestartuj Core. Integracja wymaga Core 2026.10.4 lub nowszego.

## Pobranie APK i parowanie

Podczas konfiguracji integracji lub po wybraniu **Family Tracker → Konfiguruj** zobaczysz kod QR do [najnowszego wydania GitHub](https://github.com/home409ca/family-tracker/releases/latest). Zeskanuj go zwykłym aparatem telefonu i wybierz APK z plików wydania. Gotowy [FamilyTracker-0.2.0.apk](FamilyTracker-0.2.0.apk) jest też dostępny w katalogu głównym repozytorium.

Po instalacji wróć do konfiguracji integracji, nadaj telefonowi nazwę i pobierz drugi kod QR. Zeskanuj ten drugi kod w aplikacji **Family Tracker**. Kod parowania jest jednorazowy i ważny przez pięć minut.

## Publikacja i aktualizacje

Utwórz na GitHubie wydanie z tagiem `v0.2.1` i dołącz APK w sekcji **Assets**. QR do pobrania będzie prowadził do aktualnego wydania. APK 0.2.0 ma podpis wcześniejszej wersji pilotażowej. HACS aktualizuje integrację osobno.

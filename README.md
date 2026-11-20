# Family Tracker

Aplikacja Android 0.2.6 i integracja Home Assistant 0.2.5.

Family Tracker przesyła pozycję telefonu z Androidem do Home Assistanta. Opcjonalnie udostępnia poziom baterii, stan ładowania i nazwę sieci Wi-Fi.

## Instalacja w Home Assistancie

1. W HACS otwórz **⋮ → Repozytoria niestandardowe**.
2. Dodaj `https://github.com/home409ca/family-tracker` w kategorii **Integracja**.
3. Pobierz Family Tracker i zrestartuj Home Assistant.
4. Przy pierwszej instalacji wejdź w **Ustawienia → Urządzenia i usługi → Dodaj integrację** i wybierz **Family Tracker**. Przy aktualizacji otwórz istniejący wpis.

Instalacja ręczna polega na skopiowaniu folderu `custom_components/family_tracker` do katalogu `custom_components` Home Assistanta i ponownym uruchomieniu HA. Integrację przetestowano na Core 2026.10.4.

## Instalacja i parowanie telefonu

1. Pobierz i zainstaluj [FamilyTracker.apk](https://github.com/home409ca/family-tracker/blob/main/FamilyTracker.apk). Jeśli masz już Family Tracker z tego repozytorium, zainstaluj APK jako aktualizację, żeby zachować parowanie.
2. W HA wpisz publiczny adres HTTPS w **Ustawienia → System → Sieć → Adres URL Home Assistanta → Internet**.
3. Wejdź w **Family Tracker → Konfiguruj**, wpisz nazwę telefonu i zatwierdź. W oknie pojawi się kod QR ważny przez pięć minut.
4. Otwórz Family Tracker na telefonie i wybierz **Zeskanuj kod QR**. Aplikacja odczyta adres serwera i kod, a następnie spróbuje sparować telefon.
5. W aplikacji włącz wybrane dane do udostępniania. Dla automatycznego wznowienia lokalizacji po restarcie telefonu ustaw **Dokładna lokalizacja** i **Zawsze zezwalaj** w uprawnieniach Androida.

## Lokalizacja na żądanie i Firebase

Na stronie telefonu w Home Assistancie wybierz **Poproś o aktualną lokalizację**. Bez Firebase telefon odbierze polecenie przy synchronizacji, jeśli jest ono nadal ważne. Z Firebase telefon może dostać sygnał również przy zablokowanym ekranie.

Dołączona APK zawiera konfigurację klienta FCM dla projektu właściciela repozytorium. Aby uruchomić FCM, umieść klucz JSON konta usługi tego projektu w `.storage/family_tracker_fcm.json` w katalogu konfiguracji HA. Następnie wpisz identyfikator tego samego projektu w **Family Tracker → ⋮ → Konfiguruj ponownie**. Prywatny klucz konta usługi przechowuj w Home Assistancie.

- **Firebase** w sekcji **Połączenie i raportowanie** w aplikacji pokazuje czas ostatniej udanej rejestracji telefonu w HA.
- **Ostatni sygnał Firebase** w tej samej sekcji pokazuje czas odebrania sygnału FCM.
- **Ostatnie potwierdzenie Firebase** w diagnostyce telefonu w HA pokazuje czas, kiedy HA otrzymał potwierdzenie z telefonu.
- **Ostatnia lokalizacja na żądanie** w tej samej sekcji pokazuje czas odbioru pomiaru GPS wykonanego na żądanie.

## Aktualizacje APK

Przycisk **Aktualizuj** w aplikacji sprawdza plik `FamilyTracker.apk` w głównym katalogu gałęzi `main`. Kolejne wydania APK zachowują tę nazwę i podpis. Instalację aktualizacji zatwierdzasz na telefonie.

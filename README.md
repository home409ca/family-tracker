# Family Tracker

Aplikacja Android 0.2.2 i integracja Home Assistant 0.2.3.

## Aktualizacja

Wgraj zawartość paczki do głównego katalogu publicznego repozytorium `https://github.com/home409ca/family-tracker`. W głównym katalogu gałęzi `main` umieść podpisany plik o nazwie **FamilyTracker.apk**. Zachowaj tę nazwę w kolejnych aktualizacjach. Przycisk **Aktualizuj** pobiera surowy plik z tej gałęzi, sprawdza certyfikat i wersję, a instalację zatwierdzasz w Androidzie. Przejście z APK 0.2.1 wymaga ręcznego zainstalowania APK 0.2.2. Do oznaczenia wersji integracji w HACS możesz opublikować wydanie z tagiem `v0.2.3`.

W HACS dodaj repozytorium w kategorii **Integracja** i pobierz wersję **0.2.3**. Po restarcie Core otwórz istniejący wpis Family Tracker. Przy instalacji ręcznej skopiuj katalog `custom_components/family_tracker` do konfiguracji HA i zrestartuj Core.

## Parowanie

W Home Assistant wpisz publiczny adres HTTPS w **Ustawienia → System → Sieć → Adres URL Home Assistanta → Internet**. Family Tracker odczytuje tę wartość przy tworzeniu nowego kodu parowania.

Otwórz **Ustawienia → Urządzenia i usługi → Family Tracker → Konfiguruj**. Podaj nazwę telefonu, zatwierdź formularz i pobierz jednorazowy QR. Na telefonie wybierz **Zeskanuj kod QR** w Family Tracker. Aplikacja odczyta adres HTTPS i kod, po czym od razu spróbuje sparować telefon. QR do instalacji APK jest osobny i wskazuje na [plik w gałęzi main](https://github.com/home409ca/family-tracker/blob/main/FamilyTracker.apk).

## Rozparowanie

Przycisk **Rozparuj telefon** zatrzymuje udostępnianie i usuwa z HA bieżące urządzenie oraz jego encje po potwierdzeniu przez serwer.

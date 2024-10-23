Køleboksprojekt med Raspberry Pi Pico og MicroPython

Dette projekt styrer en køleboks ved hjælp af en Raspberry Pi Pico W programmeret med MicroPython via wifi. Denne vejledning beskriver, hvordan du opsætter og kører projektet.


Trin 1: Installer MicroPython på Raspberry Pi Pico

  Tilslut din Raspberry Pi Pico til computeren med et micro-USB-kabel.
    Download MicroPython firmware til Pico fra MicroPython.org.
    Flash firmware til Pico ved hjælp af et værktøj som Thonny eller UF2-metoden:
        Hold BOOTSEL-knappen nede, mens du tilslutter Pico til computeren.
        Pico vises som en USB-lagringsenhed.
        Kopier .uf2-firmwarefilen til Pico.

Trin 2: Opsætning af MicroPython Udviklingsmiljø

  Installer Thonny eller en anden kompatibel editor til at programmere Pico:
        Thonny kan downloades fra thonny.org.

   Åbn Thonny og vælg:
        Værktøjer → Indstillinger → Interpreter
        Vælg MicroPython (Raspberry Pi Pico) som tolk.

Trin 3: Tilslutning af Hardware

  Forbind temperatur til Pico:
        Data-pin fra sensoren til en GPIO-pin på Pico (f.eks. GP2).
        VCC til 3.3V på Pico.
        GND til GND på Pico.

   Tilslut relæmodulet:
        IN-pin på relæet til en GPIO-pin (f.eks. GP15).
        VCC til 5V og GND til GND.

Trin 4: Kopier og Kør Koden

   Klon dette repository til din computer og kald det main.py

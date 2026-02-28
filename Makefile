ROGUE_DIR := rogue-collection

.PHONY: install build run clean distclean

install:
	sudo apt-get update
	sudo apt-get install -y \
		build-essential \
		qtbase5-dev \
		qtdeclarative5-dev \
		qtmultimedia5-dev \
		qt5-qmake \
		qml-module-qtquick2 \
		qml-module-qtquick-controls \
		qml-module-qtquick-controls2 \
		qml-module-qtquick-layouts \
		qml-module-qtquick-dialogs \
		qml-module-qtquick-window2 \
		qml-module-qtmultimedia

build:
	$(MAKE) -C $(ROGUE_DIR)

run:
	$(MAKE) -C $(ROGUE_DIR) run

clean:
	$(MAKE) -C $(ROGUE_DIR) clean

distclean:
	$(MAKE) -C $(ROGUE_DIR) distclean

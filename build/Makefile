
NAME=spoje
FILE1=$(NAME)-gui.py
FILE2=$(NAME).py
IconName=train.png

SrcDir=src
ImgDir=img
DataDir=data
SOURCE=$(FILE1)

FILES=$(SrcDir)/$(FILE1) $(SrcDir)/$(FILE2)
ICON=$(ImgDir)/$(IconName)
DesktopFile=$(DataDir)/$(NAME).desktop
SOURCEFORSTAT=$(FILES)

cilovyAdresar=/home/root/card/python/spoje

PERSONCOST=480000
OVERHEAD=2.4



IPK=spoje_*_all.ipk
LASTVERSION=0.4.2
IPKLAST=$(NAME)_$(LASTVERSION)_all.ipk
DEPENDS="python-core python-elementary python-sqlite3 python-netclient"


default: pk  



copy:
	ssh root@192.168.0.202 'mkdir -p $(cilovyAdresar)|| echo ""'
	scp $(FILES)     192.168.0.202:$(cilovyAdresar)/
	scp $(IPK)  192.168.0.202:$(cilovyAdresar)/



install:        
	scp $(IPKLAST)  192.168.0.202:$(cilovyAdresar)/
	ssh root@192.168.0.202 'opkg install $(cilovyAdresar)/$(IPKLAST)'

run:
	ssh root@192.168.0.202  "export DISPLAY=:0.0; python  $(cilovyAdresar)/$(FILE1)"

arch:	archiv
archiv:
	tar -cvzf  $(NAME).tar.gz *  --exclude=$(NAME).tar.gz

ipk:	package
pk:	package
package:
	mkdir -p package-ipkg/CONTROL package-ipkg/usr/bin package-ipkg/usr/share/applications package-ipkg/usr/share/pixmaps
	cp $(ICON) package-ipkg/usr/share/pixmaps/
	cp $(FILES) package-ipkg/usr/bin/
	echo -e Package: spoje\\n\
	Section: extras\\n\
	Priority: optional\\n\
	Version: $(LASTVERSION)\\n\
	Architecture: all\\n\
	Source: http://code.google.com/p/spoje/ \\n\
	"Maintainer: Josef Jebavy <josef.jebavy[at]gmail.com>" \\n\
	Depends: $(DEPENDS) \\n\
	"Description: GUI program which used  CLI program spoje.py (http://code.google.com/p/spoje/)." \\n\
	\\n > package-ipkg/CONTROL/control
	cp $(DesktopFile) package-ipkg/usr/share/applications/
	ipkg-build  -o root -g root ./package-ipkg/ ./
	rm -rf ./package-ipkg/
	


stat:
stat:
	echo -e "\e[0;34m $(FILE1) \e[0m "
	sloccount --personcost  $(PERSONCOST) --overhead $(OVERHEAD)  $(FILE1)
	echo -e "\e[0;34mecho celkovy pocet radku: \e[0m \
	"
	cat $(FILE1)| wc -l
	echo -e "\e[0;34m $(FILE2) \e[0m "
	sloccount --personcost  $(PERSONCOST) --overhead $(OVERHEAD)  $(FILE2)
	echo -e "\e[0;34mecho celkovy pocet radku: \e[0m \
	"
	cat $(FILE2)| wc -l
	echo -e "\e[0;34m $(SOURCEFORSTAT) \e[0m "
	sloccount --personcost  $(PERSONCOST) --overhead $(OVERHEAD)  $(SOURCEFORSTAT)
	echo -e "\e[0;34mecho celkovy pocet radku: \e[0m \
	"
	cat $(SOURCEFORSTAT)| wc -l




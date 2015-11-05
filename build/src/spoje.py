#!/usr/bin/env python
# -*- coding: utf-8 -*-


#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
#    Author: Karel Srot, karel.srot@seznam.cz
#    http://code.google.com/p/spoje/
#    Program slouzi k hledani dopravnich spojeni prostrednictvim serveru IDOS
#
#    Thanks to all contributors:
#       Petr Vorel
#
#
#    Revision history:
#        
#        0.7.3 - trying to make some order in version numbers
#
#        r27 - searching in reqular expressions is not case sensitive
#        r26 - fixed bug in detection when initial/final connection point does not exist
#        r25 - increased maximum time delay between individual buses/trains, added atributes MIN_CAS_PRESTUPU, MAX_CAS_PRESTUPU
#        r24 - date and time can be specified using relative values, such as "-c +2:00"
#
#
#

from __future__ import generators
import os
import sys
import httplib
import urllib
import re
import string
import getopt
import time
import codecs

VERSION = "0.7.3"

# nasledujici promenne jsou jen pro ladici ucely
DEBUG = 0
ZPRACOVAT_ARGUMENTY = 1

# konstanty pro navratove kody
KOD_SPOJ_NALEZEN = 0
KOD_NEZNAMY_PARAMETR_LINK = 1
KOD_NEJEDNOZNACNE_KONCOVE_BODY = 2
KOD_SPOJ_NENALEZEN = 3
KOD_OBJEKT_NENALEZEN = 4
KOD_DETAIL_ZISKAN = 5
KOD_DETAIL_NELZE_ZISKAT = 6

KODOVANI_IDOS = 'cp1250'   # kodovani pouzivane idosem
KODOVANI_SYSTEM = 'utf_8'  # kodovani v systemu - ma vyznam pro tiskove vystupy, pri pouziti tridy samotne neni dulezita

HTTP_PROXY = ''


class IDOS_Prestup:
    """ Trida reprezentuje jeden spoj (nastup ci prestup) v nalezenem dopravnim spojeni mezi zadanymi koncovymi body """

    def __init__(self):
        self.cislo_spoje = ""     # cislo spoje
        self.typ = ""             # typ spoje (bus, vlak, ...)
        self.poznamka = ""        # poznamka ke spoji
        self.zastavka = ""        # nazev zastavky
        self.cas_prijezdu = ""
        self.cas_odjezdu = ""
        self.kilometr = ""
    
  
    

class IDOS_Spojeni:
    """ Trida reprezentuje jednu polozku v seznamu nalezenych spojeni vyhovujicich dotazu """

    def __init__(self):
        self.datum = ""
        self.prestupy = []    # seznam jednotlivych dopravnich spoju, instanci tridy IDOS_Prestup
        self.poznamka = ""


        
    
    def tiskni(self, zpozdeni = {}):
        """ vytiskne udaje o spoji na vystup """
        
        print u"--------------------".encode(KODOVANI_SYSTEM)
        print (u"Datum: "+self.datum).encode(KODOVANI_SYSTEM)
        
        # projdu jednotlive nastupy/prestupy
        for prestup in self.prestupy:

            spoj_vypis = prestup.cas_prijezdu.rjust(5)+u'  '+prestup.cas_odjezdu.rjust(5)+u'  '+prestup.zastavka  # prijezd, odjezd, zastavka
            if prestup.poznamka:  # poznamka
                spoj_vypis += u", "+prestup.poznamka
            if prestup.typ:  # typ spoje
                spoj_vypis += u", "+prestup.typ
            if prestup.cislo_spoje:  # jmeno (cislo) spoje
                spoj_vypis += u" "+prestup.cislo_spoje
                # pokud byl predan slovnik se zpozdenimi spoju, vytisknu i zpozdeni tohoto konkretniho spoje
                if prestup.cislo_spoje in zpozdeni:
                    spoj_vypis += u", zpoždění "+zpozdeni[prestup.cislo_spoje]
            
            # vytisknu nalezeny spoj
            print spoj_vypis.encode(KODOVANI_SYSTEM)

        if self.poznamka:  # poznamka k nalezenemu spoji (celkova cena,...)
            print
            print (u'Pozn.: '+self.poznamka).encode(KODOVANI_SYSTEM)




class IDOS_Dotaz:
    """ Trida obsahuje parametry hledaneho spoje """

    def __init__(self):

        self.TYP_SPOJE=""    # urcuje jaky typ spoje se bude hledat
        self.ODKUD = ""     # pocatek cesty
        self.ODKUD2=""           # upresneny pocatek cesty pomoci kodu
        self.KAM = ""     # cil cesty
        self.KAM2=""             # upresneny cil cesty pomoci kodu
        self.KDY = ""  
        self.CAS = ""
        self.CAS_URCUJE_ODJEZD = 1  # 1 = cas urcuje odjezd, 0 = cas urcuje prijezd
        self.MAX_PRESTUPU = 3    # maximalni pocet prestupu (neni vzdy idosem respektovan)
        self.MAX_SPOJU = 5       # maximalni pocet nalezenych spoju
        self.ZISKAT_TRASU_SPOJE = 0  # povoluje/zakazuje  vypis zastavek na trase jednotlivych spoju, 0 = nic, 1 = zastavky na trase, 2 = vsechny zastavky
        self.ZISKAT_ZPOZDENI_VLAKU = 0  # povoluje/zakazuje dohledavani a vypis informace o zpozdeni vlaku
        self.MIN_CAS_PRESTUPU = 3  # minimalni cas na prestup
        self.MAX_CAS_PRESTUPU = 240  # maximalni cas na prestup



class IDOS_Odpoved:
    """ Trida obsahuje data o nalezenych spojich """

    def __init__(self):

        self.VYBER_ODKUD = []       # obsahuje seznam moznosti pri nepresne specifikovanem vyberu
        self.VYBER_KAM = []         # obsahuje seznam moznosti pri nepresne specifikovanem vyberu
        self.NALEZENA_SPOJENI = []  # obsahuje nalezena spojeni
                                    # kazde spojeni na nasledujici je instance tridy IDOS_spojeni
        self.DICT_URL_DETAILY_SPOJU = {}  # slovnik s URL adresami detailu nalezenych spojeni
                                          # jednotlive polozky jsou slovniky s klici
                                          # trasa (pro trasu spoje), poloha (pro zpozdeni vlaku), razeni (pro razeni vlaku)
        self.DICT_DETAILY_SPOJU = {}  # slovnik s detaily nalezenych spojeni
                                      # hodnotou je seznam, v nemz kazda polozka je instance tridy IDOS_prestup (preprezentuji jednotlive zastavky)
        self.DICT_ZPOZDENI_VLAKU = {}  # slovnik s informaceni o zpozdeni vlaku

        self.NAVRATOVY_KOD = None   # pro ulozeni navratoveho kodu identifikujiciho vysledek vyhledavani
        self.POPIS_CHYBY = ""       # textovy popis chyby




class IDOS_Prostrednik:
    """ Trida je prostrednikem pro komunikaci se servery typu IDOS"""

    def __init__(self):

        # vyhledavaci kody pro identifikaci typu spojeni pri hledani pres idos
        self.DICT_VYHLEDAVACI_KODY1 = {}
        self.DICT_VYHLEDAVACI_KODY2 = {}
   
        self.DATA = ""              # do teto promenne se ulozi data ziskana z idosu (html stranka)
        self.DATA2 = ""             # do teto promenne se ulozi data ziskana z idosu - detail spojeni (html stranka), ale pouze jen pro posledni dotazovane spojeni

        self.DOTAZ = ""             # parametry hledaneho spojeni, instance tridy IDOS_Dotaz
        self.ODPOVED = ""       # nalezena spojeni, instance tridy IDOS_Odpoved

        self.HEADERS = {}
        self.IDOS_URL = ""



    def vyhledej_spojeni(self, parametry_spoje):
        """ Procedura vyhleda dopravni spojeni odpovidajici pozadovanym parametrum (instance IDOS_Dotaz) a vraci instanci tridy IDOS_Odpoved"""

        pass


    #===================
    # pomocne procedury
    #===================


    def generator_dat(self, data = 1):
        """ generator posila obsah retezce self.DATA nabo self.DATA2 po jednotlivych radcich """

        if data == 1:
            radky = self.DATA.splitlines()
        else:
            radky = self.DATA2.splitlines()

        for i in range(len(radky)):
            yield radky[i]
       


    def odstran_tagy(self, s):  
        """ odstrani z retezce tagy """

        pom = s.replace(u'=">"', u'=""')
        r = 1
        while r:
            r = re.search('(.*)<(.+?)>(.*)', pom)
            if r:
                pom = r.group(1)+r.group(3)
        return pom



    def nahrad_nechtene_retezce(self, s):  
        """ odstrani ci upravi nektere nechtene retezce """

        s = s.replace(u' ',u' ')
        s = s.replace(u',,',u',')
        s = s.replace(u'&#160;',u'')
        s = s.replace(u'&nbsp;',u'')
        return s




class IDOS_Prostrednik_jizdnirady_cz(IDOS_Prostrednik):
    """ Trida je prostrednikem pro komunikaci se serverem blind.jizdnirady.cz """


    def __init__(self):

        # vyhledavaci kody pro identifikaci typu spojeni pri hledani pres idos
        self.DICT_VYHLEDAVACI_KODY1 = {
            "BRNO": "tt=f",
            "VLAK": "tt=a",#tt=a&p=CD",
            "BUS": "tt=b",
            "KOMB": "tt=X&cl=C",
            "PRAHA": "tt=e",
            "OSTRAVA": "tt=g",
            "LIBEREC": "tt=LI",
        }
   
        self.DICT_VYHLEDAVACI_KODY2 = {
            "BRNO": "tt=f",
            "VLAK": "tt=a",#tt=a&p=CD",
            "BUS": "tt=b",
            "KOMB": "tt=c",
            "PRAHA": "tt=e",
            "OSTRAVA": "tt=g",
            "LIBEREC": "tt=LI",
        }
   
        self.DATA = ""              # do teto promenne se ulozi data ziskana z idosu (html stranka)
        self.DATA2 = ""             # do teto promenne se ulozi data ziskana z idosu - detail spojeni (html stranka), ale pouze jen pro posledni dotazovane spojeni

        self.DOTAZ = ""             # parametry hledaneho spojeni
        self.ODPOVED = ""       # nalezena spojeni

        self.HEADERS = {
                "Host": "blind.jizdnirady.idnes.cz",
                "User-Agent": "User-Agent: Mozilla/5.0 (Windows; U; Windows NT 5.1; cs-CZ; rv:1.7.8) Gecko/20050511 Firefox/1.0.4",
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "cs,en-us;q=0.7,en;q=0.3",
                "Accept-Encoding": "text/plain",
                "Accept-Charset": "ISO-8859-2,utf-8;q=0.7,*;q=0.7",
                "Referer": "http://blind.jizdnirady.idnes.cz/ConnForm.asp",
                "Keep-Alive": "300",
                "Connection": "keep-alive",
              }
   
        self.IDOS_URL = "blind.jizdnirady.idnes.cz"



    def vyhledej_spojeni(self, parametry_spoje):
        """ Procedura vyhleda dopravni spojeni odpovidajici pozadovanym parametrum (instance IDOS_Dotaz) a vraci instanci tridy IDOS_Odpoved"""
    
        self.DOTAZ = parametry_spoje
        self.ODPOVED = IDOS_Odpoved()
        
        self.posli_dotaz_na_idos()
        self.zpracuj_ziskana_data()

        if self.DOTAZ.ZISKAT_TRASU_SPOJE:
            self.vyhledej_detaily_spoju()
        if self.DOTAZ.ZISKAT_ZPOZDENI_VLAKU:
            self.vyhledej_zpozdeni_vlaku()
        
        return self.ODPOVED


    #===================
    # pomocne procedury
    #===================

    def vyhledej_detaily_spoju(self):
        """ Vyhleda detaily (jednotlive zastavky na trase, casy,...) k nalezenych dopravnim spojenim """
       
        self.ODPOVED.DICT_DETAILY_SPOJU = {}
       
        # projdu nalezena spojeni a pro kazdy uvedeny spoj dohledam detaily
        for spojeni in self.ODPOVED.NALEZENA_SPOJENI:

            # projdu jednotlive prestupy
            for prestup in spojeni.prestupy:

                # pokud pro uvedene spojeni, neni-li jeste ve slovniku, dohledam detaily
                if prestup.cislo_spoje and (not prestup.cislo_spoje in self.ODPOVED.DICT_DETAILY_SPOJU):
                                 
                    # ziskam z idosu detail o spoji
                    kod = self.ziskej_z_idosu_detail_spoje(prestup.cislo_spoje, "trasa")
                    # detail o dopravnim spoji nalezen
                    if kod == KOD_DETAIL_ZISKAN:
                        self.ODPOVED.DICT_DETAILY_SPOJU[prestup.cislo_spoje] = self.parsuj_detail_spoje()
                    else:
                        pass



    def vyhledej_zpozdeni_vlaku(self):
        """ Vyhleda informace o zpozdeni vlaku """
       
        self.ODPOVED.DICT_ZPOZDENI_VLAKU = {}
       
        # projdu nalezena spojeni a pro kazdy uvedeny spoj dohledam detaily
        for spojeni in self.ODPOVED.NALEZENA_SPOJENI:

            # preskocim datum a poznamky
            for prestup in spojeni.prestupy:

                # pokud jeste neni cislo spoje ve slovniku a mam-li pro nej ulozene URL pro zpozdeni, pak dohledam detaily
                if prestup.cislo_spoje and (not prestup.cislo_spoje in self.ODPOVED.DICT_ZPOZDENI_VLAKU) and ("poloha" in self.ODPOVED.DICT_URL_DETAILY_SPOJU[prestup.cislo_spoje]):
                    # ziskam z idosu detail o spoji
                    kod = self.ziskej_z_idosu_detail_spoje(prestup.cislo_spoje, "poloha")
                    # detail o dopravnim spoji nalezen
                    if kod == KOD_DETAIL_ZISKAN:
                        zpozdeni = self.parsuj_zpozdeni_vlaku()
                        if zpozdeni:
                            self.ODPOVED.DICT_ZPOZDENI_VLAKU[prestup.cislo_spoje] = zpozdeni
                    else:
                        pass
           
           

    def zpracuj_ziskana_data(self):
        """ Zpracuje odpoved ziskanou z idosu """
       
        kod = self.ODPOVED.NAVRATOVY_KOD
       
        if kod == KOD_NEJEDNOZNACNE_KONCOVE_BODY:
            # nejednoznacne zadane koncove body    
            self.parsuj_koncove_body()
        elif kod == KOD_SPOJ_NALEZEN:
            # hledane spojeni bylo nalezeno
            self.parsuj_nalezena_spojeni()
        else:
            # behem k hledani doslo k chybe
            pass



    def posli_dotaz_na_idos(self):
        """ Posle dotaz na IDOS a ulozi ziskana data a status odpovedi """

        if self.DOTAZ.ODKUD2 == "":
            odkud2 = urllib.quote(self.DOTAZ.ODKUD.encode(KODOVANI_IDOS))
        else:
            odkud2 = self.DOTAZ.ODKUD2.encode(KODOVANI_IDOS)
        if self.DOTAZ.KAM2 == "":
            kam2 = urllib.quote(self.DOTAZ.KAM.encode(KODOVANI_IDOS))
        else:
            kam2 = self.DOTAZ.KAM2.encode(KODOVANI_IDOS)
       
        kdy = urllib.quote(self.DOTAZ.KDY.encode(KODOVANI_IDOS))
        cas = urllib.quote(self.DOTAZ.CAS.encode(KODOVANI_IDOS))
        #print odkud2, kam2, kdy, cas
   
        # PRVNI DOTAZ, cilem je zjistit hodnotu parametru link
   
        #conn = httplib.HTTPConnection(self.IDOS_URL)
        #conn.request("GET", "/ConnForm.asp?"+self.DICT_VYHLEDAVACI_KODY1[self.DOTAZ.TYP_SPOJE], '', self.HEADERS)

        if HTTP_PROXY != '':
            conn = httplib.HTTPConnection(HTTP_PROXY)
            conn.connect()
            prefix_link = "http://"+self.IDOS_URL
        else:
            conn = httplib.HTTPConnection(self.IDOS_URL)
            prefix_link = ""

        conn.request("GET", prefix_link+"/ConnForm.asp?"+self.DICT_VYHLEDAVACI_KODY1[self.DOTAZ.TYP_SPOJE], '', self.HEADERS)

   
        if DEBUG:
            print "posilam dotaz pro zjisteni parametru 'link'"


        r = conn.getresponse()
        data = r.read()

        if DEBUG:
            print "Odpoved:", r.status, r.reason
            of = file('idos_debug_link.html', 'w')
            of.write(data)
            of.close()
       
        parametr_link = ""
       
        vyber = re.search('name="link" value="(\w{,6})"', data, re.I)
        if vyber:
            parametr_link = vyber.group(1)
            #print "Hodnota link:", parametr_link
        else:
            #print "nepodarilo se zjistit hodnotu parametru 'link'"
            self.ODPOVED.POPIS_CHYBY = u"nepodařilo se zjistit hodnotu parametru 'link'"
            conn.close()
            self.ODPOVED.NAVRATOVY_KOD = KOD_NEZNAMY_PARAMETR_LINK
            return

        # DRUHY DOTAZ, posilam udaje o hledanem spoji
   
        # pridam k hlavicce content-type
        self.HEADERS["Content-type"] = "application/x-www-form-urlencoded"
   
        max_prestupu = self.DOTAZ.MAX_PRESTUPU
        if max_prestupu:
            prestup_povolen = 1
        else:  
            prestup_povolen = 0
            max_prestupu = 1
   
        posilana_data = 'FromStn=%s&FromList=-1&ToStn=%s&ToList=-1&ViaStn=&ViaList=-1&ConnDate=%s&ConnTime=%s&ConnIsDep=%s&ConnAlg=%s&Prest=%s&search=Vyhledat&tt=f&changeext=0&Mask1=-1&Min1=%s&Max1=%s&Std1=1&beds=0&alg=1&chn=5&odch=50&odcht=0&ConnFromList=-1&ConnToList=-1&ConnViaList=-1&recalc=0&pars=0&process=0&link=%s' % (odkud2, kam2, kdy, cas, `self.DOTAZ.CAS_URCUJE_ODJEZD`, prestup_povolen, max_prestupu, `self.DOTAZ.MIN_CAS_PRESTUPU`, `self.DOTAZ.MAX_CAS_PRESTUPU`, parametr_link)
   
        #conn.request("POST", "/ConnForm.asp?"+self.DICT_VYHLEDAVACI_KODY2[self.DOTAZ.TYP_SPOJE], posilana_data, self.HEADERS)
        conn.request("POST", prefix_link+"/ConnForm.asp?"+self.DICT_VYHLEDAVACI_KODY2[self.DOTAZ.TYP_SPOJE], posilana_data, self.HEADERS)
   
        r = conn.getresponse()
        #print "Odpoved:", r.status, r.reason
        data = r.read()
        #print data
           
        nova_adresa = r.getheader("location", "")
   
        if r.status == 200:
            #print "Nejednoznacne zadan pocatek ci cil cesty"
           
            # ulozeni souboru jen pro ladici ucely            
            if DEBUG:
                of = file('idos_debug_spec.html', 'w')
                of.write(data)
                of.close()
           
            # ulozim data jako Unicode
            self.DATA = unicode(data, KODOVANI_IDOS)
            conn.close()
            self.ODPOVED.NAVRATOVY_KOD = KOD_NEJEDNOZNACNE_KONCOVE_BODY
            return

        elif r.status == 302 and re.search('ConnRes', nova_adresa, re.I):
            # nasel jsem spoj, zacnu vypisovat
           
            #print "Spoj nalezen"
            del self.HEADERS['Content-type']
            #conn.request("GET", "/"+nova_adresa, '', self.HEADERS)
            #print nova_adresa
            conn.request("GET", prefix_link+"/"+nova_adresa, '', self.HEADERS)
           
            r = conn.getresponse()
            #print "Odpoved:", r.status, r.reason
            data = r.read()
            #print data
            # ukoncim spojeni
            conn.close()
           
            # ulozeni souboru pro ladici ucely            
            if DEBUG:
                of = file('idos_debug_conn.html', 'w')
                of.write(data)
                of.close()
           
            if re.search('ErrRes', r.getheader('location', ""), re.I):
                # zapisi do souboru spravu o chybe
                self.ODPOVED.POPIS_CHYBY = u"Spoj vyhovující kritériím se nepodařilo nalézt (zkuste zvýšit počet přestupů) nebo došlo k nějaké jiné chybě."    
                self.ODPOVED.NAVRATOVY_KOD = KOD_SPOJ_NENALEZEN
               
            else:
                # ulozim data jako Unicode
                self.DATA = unicode(data, KODOVANI_IDOS)
                self.ODPOVED.NAVRATOVY_KOD = KOD_SPOJ_NALEZEN
         
        else:
            # zapisu do souboru chybovou hlasku
            self.ODPOVED.POPIS_CHYBY = u"Spoj vyhovující kritériím se nepodařilo nalézt (zkuste zvýšit počet přestupů) nebo došlo k nějaké jiné chybě."
            conn.close()
            self.ODPOVED.NAVRATOVY_KOD = KOD_SPOJ_NENALEZEN



    def parsuj_koncove_body(self):
        """ Parsuje html stranku a extrahuje z ni nabizene moznosti pro upresneni koncovych bodu spojeni """
       
        # zjistim co bylo spatne a naplnim pole nalezenymi moznostmi
        zpracovavana_cast = u"From"
        nenalezeno = [0,0]
        self.DOTAZ.VYBER_ODKUD = []
        self.DOTAZ.VYBER_KAM = []
       
        # ziskam generator radku
        gen = self.generator_dat()
       
        # ziskana data budu zpracovavat po radcich, je to tak snazsi
        # vyhozeni vyjimky StopIteration kdekoliv v cyklu znamena, ze jsem zpracoval vsechny radky
        try:
            while 1:  # cyklus ukoncim bud rucne nebo vyhozenim vyjimky

                # ziskam dalsi radek
                radek = gen.next()
           
                # zacnu vyhledavat konkretni tagy a z nich dolovat data
                # pocatek sekce s udaji o koncovych bodech spojeni
                r = re.search(u'<label for="(From|To)Stn"', radek, re.I)
                if r:            
                    zpracovavana_cast = r.group(1)
           
                if re.search(u'objekt nebyl nalezen', radek, re.I):
                    if zpracovavana_cast == u'From':
                        nenalezeno[0] = 1
                    else:                                            
                        nenalezeno[1] = 1
           
                # nalezl jsem vycet moznosti pro koncovy/cilovy bod
                r = re.search(u'<select name="(From|To)Stn"', radek, re.I)
                if r:            
                    zpracovavana_cast = r.group(1)
               
                    # dokud nenarazim na konec vyctu
                    while not re.search(u'</select>', radek, re.I):
                        radek = gen.next()    # nactu dalsi radek
                       
                        # nalezl jsem radek s polozkou vyberu
                        r = re.search(u'<option value="(.+?)".+?>(.+)</option>', radek, re.I)
                        if r:
                            pom = r.group(1).replace(u'%', u":25")
                            pom = pom.replace(u'!', u"%21")
                            pom = pom.replace(u':', u"%")

                            if zpracovavana_cast == u'From':
                                self.ODPOVED.VYBER_ODKUD.append(r.group(2)+u":"+pom)
                            else:                                            
                                self.ODPOVED.VYBER_KAM.append(r.group(2)+u":"+pom)
               
                    # pokud jsem na konci nabidky v casti KAM, ukoncim zpracovavani radku, je to jiz zbytecne
                    if zpracovavana_cast == u'To':
                        break

        except StopIteration:
            # prosel jsem uz vsechny radky, pouze odchytim vyjimku, aby nedoslo k ukonceni programu
            pass
       
        # pokud nektery z koncovych bodu nebyl vubec nalezen
        if nenalezeno[0]:
            self.ODPOVED.POPIS_CHYBY += self.DOTAZ.ODKUD+" - Objekt nenalezen\n"
            self.ODPOVED.NAVRATOVY_KOD = KOD_OBJEKT_NENALEZEN
            return
        elif nenalezeno[1]:
            self.ODPOVED.POPIS_CHYBY += self.DOTAZ.KAM+" - Objekt nenalezen\n"
            self.ODPOVED.NAVRATOVY_KOD = KOD_OBJEKT_NENALEZEN
            return
       
        # je-li seznam prazdny, vlozim alespon hledany udaj
        if len(self.ODPOVED.VYBER_ODKUD) == 0:
            self.ODPOVED.VYBER_ODKUD.append(self.DOTAZ.ODKUD)
        if len(self.ODPOVED.VYBER_KAM) == 0:
            self.ODPOVED.VYBER_KAM.append(self.DOTAZ.KAM)
   
   
   
    def parsuj_nalezena_spojeni(self):
        """ Parsuje html stranku s nalezenym spojenim a extrahuje z ni udaje o spojenich """
       
        pocet_spoju = 0
        self.ODPOVED.NALEZENA_SPOJENI = []
       
        # ziskam generator radku
        gen = self.generator_dat()
       
        # ziskana data budu zpracovavat po radcich (je to tak snazsi s ohledem na predchozi funkcnost skriptu)
        # vyhozeni vyjimky StopIteration kdekoliv v cyklu znamena, ze jsem zpracoval vsechny radky
        try:
            while 1:
         
                # ziskam dalsi radek
                radek = gen.next()

                # hledam prvni (ci nasledujici) nalezeny spoj, kupodivu staci hledat '<td colspan=15>'
                while not re.search(u'<td colspan=15>', radek, re.I):
                    radek = gen.next()

                # vytvorim novou instanci tridy IDOS_Spojeni
                spojeni = IDOS_Spojeni()

                # najdu datum spoje
                while not re.search(u'<td align="right">', radek, re.I):
                    radek = gen.next()

                spojeni.datum = self.nahrad_nechtene_retezce(self.odstran_tagy(radek)).strip()
                #print spojeni.datum.encode(KODOVANI_SYSTEM)
               
                # nyni budu hledat zastavky (jednotliva mista nastupu/prestupu) a pro kazdou zastavku dalsi udaje
                while 1:

                    r = 0
                    while not r:
                        radek = gen.next()
                        # hledam vzdy bud dalsi zastavku a nebo uz zaverecnou poznamku
                        r = re.search(u'<td nowrap>(.+?)</td>', radek, re.I) or re.search(u'<td colspan="11">(.+?)</td>', radek, re.I)
               
                    # pokud jsem nasel zastavku
                    if re.search(u'<td nowrap>', radek, re.I):
               
                        # vytvorim novou instanci tridy IDOS_Prestup
                        prestup = IDOS_Prestup()
                        
                        # ulozim nazev zastavky
                        pom_str = r.group(1).replace(u' ',u' ')
                        pom_str = self.nahrad_nechtene_retezce(self.odstran_tagy(pom_str))

                        prestup.zastavka = pom_str
               
                        # najdu casy prijezdu spoju
                        r = 0
                        while not r:
                            radek = gen.next()
                            r = re.search(u'<td align="right" nowrap>(.+)</td>', radek, re.I)
                        pom_str = r.group(1).replace(u'&#160;',u'')
                        pom_str = self.nahrad_nechtene_retezce(pom_str)
                        
                        if pom_str:
                            prestup.cas_prijezdu = pom_str
                        else:
                            prestup.cas_prijezdu = u"  *  "

                        # najdu casy odjezdu
                        r = 0
                        while not r:
                            radek = gen.next()
                            r = re.search(u'<td align="right">(.+?)</td>', radek, re.I)
                        pom_str = r.group(1).replace(u'&#160;',u'')
                        pom_str = self.nahrad_nechtene_retezce(pom_str)

                        if pom_str:
                            prestup.cas_odjezdu = pom_str
                        else:
                            prestup.cas_odjezdu = u"  *  "

                        # najdu pripadne poznamky
                        r = 0
                        while not r:
                            radek = gen.next()
                            r = re.search(u'<td align="right" nowrap>(.+?)</td>', radek, re.I)
                        pom_str = r.group(1).replace(u'&#160;',u'')

                        pom_str = self.nahrad_nechtene_retezce(self.odstran_tagy(pom_str))
                        
                        prestup.poznamka = pom_str
       
                        # hledam radek s odkazem na detaily o spoji (url na zpozdeni vlaku, url na razeni vlaku,...)
                        while not re.search(u'<td nowrap align="right">', radek, re.I):
                            radek = gen.next()
                        # poloha a zpozdeni vlaku
                        url_poloha = ''
                        r = re.search(u"<a href='(\S+)' target='_blank' title='Poloha vlaku", radek, re.I)
                        if r:
                            url_poloha = r.group(1).replace('&amp;', '&')
                            #print url_poloha
                        # razeni vlaku
                        url_razeni = ''
                        r = re.search(u"<a href='(\S+)' target='RAZENI'", radek, re.I)
                        if r:
                            url_razeni = r.group(1).replace('&amp;', '&')
       
                        # najdu typ spoje  (bus, vlak, pesky)
                        while not re.search(u'<td nowrap>(.+?)</td>', radek, re.I):
                            radek = gen.next()
                        r = re.search(u"<a href='(Route.asp\S+)'.+?>(.+?)<", radek, re.I)

                        if r:
                            url_detaily_spoje = r.group(1).replace('&amp;', '&')
                            prestup.cislo_spoje = self.nahrad_nechtene_retezce(r.group(2))

                            # pokud nemam polozku pro nazev spoje, vytvorim ji
                            if not prestup.cislo_spoje in self.ODPOVED.DICT_URL_DETAILY_SPOJU:
                                self.ODPOVED.DICT_URL_DETAILY_SPOJU[prestup.cislo_spoje] = {}

                            # ulozim nasbirane detaily
                            d = self.ODPOVED.DICT_URL_DETAILY_SPOJU[prestup.cislo_spoje]
                            d["trasa"] = url_detaily_spoje
                            if url_poloha:
                                d["poloha"] = url_poloha
                            if url_razeni:
                                d["razeni"] = url_razeni
                        else:
                            prestup.cislo_spoje = u''
                            url_detaily_spoje = u''

                        if re.search(u'bus_p.gif|Bus:', radek, re.I):
                            prestup.typ = u"autobus"
                        elif re.search(u'train_p.gif|Vlak:', radek, re.I):
                            prestup.typ = u"vlak"
                        elif re.search(u'trol_p.gif|Trol:', radek, re.I):
                            prestup.typ = u"trolejbus"
                        elif re.search(u'tram_p.gif|Tram:', radek, re.I):
                            prestup.typ = u"tramvaj"
                        elif re.search(u'metro_p.gif', radek, re.I):
                            prestup.typ = u"metro"
                        elif re.search(u'foot_p.gif', radek, re.I):
                            r = re.search(u'esun asi (\d+) min', radek, re.I)
                            if r:
                                prestup.typ = u"přesun asi "+r.group(1)+u" min"
                            else:    
                                prestup.typ = u"přesun pěšky"
                        else:
                            prestup.typ = u""
                            
                        # pridam prave nacteny prestup do seznamu prestupu
                        spojeni.prestupy.append(prestup)

                    else:
                        # nasel jsem zaverecnou poznamku - delka cesty apod.
                        spoj_delka_a_cena = r.group(1)
                        spoj_delka_a_cena = self.nahrad_nechtene_retezce(spoj_delka_a_cena)

                        # ulozim zaverecnou poznamku k informacim o spojeni
                        spojeni.poznamka = spoj_delka_a_cena
                        
                        # opustim nekonecnou smycku
                        break
                
                
                self.ODPOVED.NALEZENA_SPOJENI.append(spojeni)

        except StopIteration:
            # prosel jsem uz vsechny radky, pouze odchytim vyjimku, aby to nevedlu k ukonceni programu
            pass

        # nyni nalezena spojeni trochu salamounsky zkratim na zadany max. pocet
        # sice bych je mohl nechat, ale v pripade, kdy chci i detaily, tak by se zbytecne hledaly i detaily ke spojum, ktere me nezajimaji
        # takhle je snazsi
        if self.DOTAZ.CAS_URCUJE_ODJEZD:
            # v pripade ze cas uctuje odjezd, chci ty ze zacatku seznamu
            self.ODPOVED.NALEZENA_SPOJENI = self.ODPOVED.NALEZENA_SPOJENI[:self.DOTAZ.MAX_SPOJU]
        else:
            # v pripade ze cas uctuje prijezd, chci ty z konce seznamu
            # v pripade ze cas uctuje odjezd, chci ty ze zacatku seznamu
            self.ODPOVED.NALEZENA_SPOJENI = self.ODPOVED.NALEZENA_SPOJENI[-self.DOTAZ.MAX_SPOJU:]

   

    def ziskej_z_idosu_detail_spoje(self, nazev_spoje, typ):
        """ ziska z IDOSu detail spoje (autobus, vlak,..) zadaneho typu a ziskany HTML ulozi do promenne self.DATA2 """

        self.DATA2 = ''
        # pokud mam ke spoji ulozene URL na dotaz...
        if nazev_spoje in self.ODPOVED.DICT_URL_DETAILY_SPOJU:
            url = self.ODPOVED.DICT_URL_DETAILY_SPOJU[nazev_spoje][typ]
            #print nazev_spoje, url
        else:
            # pokud ne, koncim
            return KOD_DETAIL_NELZE_ZISKAT
       
        # DOTAZ, chci ziskat html stranku s detaily spoje
   
        #conn = httplib.HTTPConnection(self.IDOS_URL)
        #conn.request("GET", '/'+url, '', self.HEADERS)
        if HTTP_PROXY != '':
            conn = httplib.HTTPConnection(HTTP_PROXY)
            conn.connect()
            prefix_link = "http://"+self.IDOS_URL
        else:
            conn = httplib.HTTPConnection(self.IDOS_URL)
            prefix_link = ""

        conn.request("GET", prefix_link+'/'+url, '', self.HEADERS)


        #print self.IDOS_URL+'/'+url
   
        #print "posilam dotaz"
        r = conn.getresponse()
        #print "Odpoved:", r.status, r.reason

        if r.status == 200: # "OK"
            # nactu data a ulozim je v unicode do self.DATA2
            data = r.read()
            self.DATA2 = unicode(data, KODOVANI_IDOS)

            if DEBUG:
                of = file('idos_debug_'+typ+'.html', 'w')
                of.write(data)
                of.close()

            return KOD_DETAIL_ZISKAN
        else:
            return KOD_DETAIL_NELZE_ZISKAT



    def parsuj_detail_spoje(self):
        """ Parsuje html stranku s detailem spoje a extrahuje z ni jednotlive zastavky """
       
        # ziskam generator radku
        gen = self.generator_dat(data = 2)
       
        # ziskana data budu zpracovavat po radcich, je to tak snazsi
        # ziskam dalsi radek
        radek = gen.next()
           
        # zacnu vyhledavat konkretni tagy a z nich dolovat data
        # pocatek sekce s udajem o cisle spojeni
        while not re.search(u"<a title='", radek, re.I):
            radek = gen.next()
        nazev = self.nahrad_nechtene_retezce(self.odstran_tagy(radek)).strip()
        
        seznam_zastavek = []

        try:
            while 1:
           
                # pocatek sekce se seznamem zastavek
                while not re.search(u'<td align="left" nowrap>', radek, re.I):
                    radek = gen.next()
                
                # vytvorim novou instanci tridy IDOS_prestup a ulozim nazev zastavky a nazev spoje
                prestup = IDOS_Prestup()
                prestup.cislo_spoje = nazev

                prestup.zastavka = self.odstran_tagy(self.nahrad_nechtene_retezce(radek)).strip()
                if radek.find(u'<b>') >=0 :  # je-li zastavka tucne, jedna se o nastupni ci vystupni zastavku - pridam na zacatek *, abych ji poznal
                    prestup.zastavka = u'*'+prestup.zastavka

                # sekce s casy prijezdu
                while not re.search(u'<td nowrap>', radek, re.I):
                    radek = gen.next()
                prestup.cas_prijezdu = self.odstran_tagy(self.nahrad_nechtene_retezce(radek)).strip()

                # pocatek sekce s casy odjezdu
                while not re.search(u'<td>', radek, re.I):
                    radek = gen.next()
                prestup.cas_odjezdu = self.odstran_tagy(self.nahrad_nechtene_retezce(radek)).strip()

                # pocatek sekce s poznamkami
                while not re.search(u'<td nowrap align="right">', radek, re.I):
                    radek = gen.next()
                prestup.poznamka = self.odstran_tagy(self.nahrad_nechtene_retezce(radek)).strip()

                # pocatek sekce s kilometry
                while not re.search(u'<td>', radek, re.I):
                    radek = gen.next()
                prestup.kilometr = self.odstran_tagy(self.nahrad_nechtene_retezce(radek)).strip()
                
                # pridam zastavku do seznamu zastavek
                seznam_zastavek.append(prestup)
           
        except StopIteration:
            # prosel jsem uz vsechny radky, pouze odchytim vyjimku, aby to nevedlu k ukonceni programu
            pass

        # vratim udaje o spoji
        return seznam_zastavek



    def parsuj_zpozdeni_vlaku(self):
        """ Parsuje html stranku s detailem o pozici spoje a extrahuje z ni zpozdeni """
        # ziskam generator radku
        gen = self.generator_dat(data = 2)
        # ziskana data budu zpracovavat po radcich, je to tak snazsi
        # ziskam dalsi radek
        radek = gen.next()
        
        zpozdeni = ''
        # zacnu vyhledavat konkretni tagy a z nich dolovat data
        # nejdrive se posunu bliz tomu spravnemu mistu
        try:
            while not re.search(u"Zpoždění", radek, re.I):
                radek = gen.next()
            # a nyni jiz na to spravne
            while not re.search(u'<td nowrap>', radek, re.I):
                radek = gen.next()
            zpozdeni = self.nahrad_nechtene_retezce(self.odstran_tagy(radek.split(u'<br>')[-1])).strip()

        # vyjimka - nenasel jsem informace v pozadovanem formatu
        except StopIteration:
            pass

        return zpozdeni





class IDOS_Prostrednik_vlak_cz(IDOS_Prostrednik_jizdnirady_cz):
    """ Trida zprostredkovava vyhledavani dopravnich spojeni prostrednictvim serveru vlaky.cz """

    def __init__(self):

        # vyhledavaci kody pro identifikaci typu spojeni pri hledani pres idos
        self.DICT_VYHLEDAVACI_KODY1 = {
            "BRNO": "tt=f",
            "VLAK": "tt=a",#tt=a&p=CD",
            "BUS": "tt=b",
            "KOMB": "tt=X&cl=C",
            "PRAHA": "tt=e",
            "OSTRAVA": "tt=g",
            "LIBEREC": "tt=LI",
        }
    
        self.DICT_VYHLEDAVACI_KODY2 = {
            "BRNO": "tt=f",
            "VLAK": "tt=a",#tt=a&p=CD",
            "BUS": "tt=b",
            "KOMB": "tt=c",
            "PRAHA": "tt=e",
            "OSTRAVA": "tt=g",
            "LIBEREC": "tt=LI",
        }
    
        self.DATA = ""              # do teto promenne se ulozi data ziskana z idosu (html stranka)
        self.DATA2 = ""             # do teto promenne se ulozi data ziskana z idosu - detail spojeni (html stranka), ale pouze jen pro posledni dotazovane spojeni
    
        self.DOTAZ = ""             # parametry hledaneho spojeni
        self.ODPOVED = ""       # nalezena spojeni

        self.HEADERS = { 
                "Host": "jizdnirady.idnes.cz",
                "User-Agent": "User-Agent: Mozilla/5.0 (Windows; U; Windows NT 5.1; cs-CZ; rv:1.7.8) Gecko/20050511 Firefox/1.0.4",
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "cs,en-us;q=0.7,en;q=0.3",
                "Accept-Encoding": "text/plain",
                "Accept-Charset": "ISO-8859-2,utf-8;q=0.7,*;q=0.7",
                "Referer": "http://jizdnirady.idnes.cz/ConnForm.asp",
                "Keep-Alive": "300",
                "Connection": "keep-alive",
              }
    
        self.IDOS_URL = "www.vlak.cz"


    #===================
    # pomocne procedury
    #===================


    def parsuj_nalezena_spojeni(self):
        """ Parsuje html stranku s nalezenym spojenim a extrahuje z ni udaje o spojenich """
        
        pocet_spoju = 0
        self.ODPOVED.NALEZENA_SPOJENI = []
        
        # ziskam generator radku
        gen = self.generator_dat()
        
        # ziskana data budu zpracovavat po radcich (je to tak snazsi s ohledem na predchozi funkcnost skriptu)
        # vyhozeni vyjimky StopIteration kdekoliv v cyklu znamena, ze jsem zpracoval vsechny radky
        try:
            while 1: 
          
                # ziskam dalsi radek
                radek = gen.next() 

                # hledam prvni (ci nasledujici) nalezeny spoj, kupodivu staci hledat '<tr valign="top">'
                while not re.search(u'<tr valign="top">', radek, re.I):
                    radek = gen.next()

                # vytvorim novou instanci tridy IDOS_Spojeni
                spojeni = IDOS_Spojeni()

                # najdu datum spoje
                while not re.search(u'<td align="right">', radek, re.I):
                    radek = gen.next()
                spojeni.datum = self.nahrad_nechtene_retezce(self.odstran_tagy(radek)).strip()

                # najdu zastavku
                r = 0
                while not r:
                    radek = gen.next()
                    r = re.search(u'<td nowrap>(.+?)</td>', radek, re.I)
                pom_str = r.group(1).replace(u'&nbsp;',u' ')
                spoj_zastavky = re.split(u'<br>', pom_str)
                spoj_zastavky = map(self.odstran_tagy, spoj_zastavky)
                spoj_zastavky = map(self.nahrad_nechtene_retezce, spoj_zastavky)

                # najdu casy nastupu spoju
                r = 0
                while not r:
                    radek = gen.next()
                    r = re.search(u'<td align="right" nowrap>(.+)</td>', radek, re.I)
                pom_str = r.group(1).replace(u'&#160;',u'')
                spoj_vystupy = re.split(u'<br>', pom_str)
                spoj_vystupy = map(self.nahrad_nechtene_retezce, spoj_vystupy)

                # najdu casy vystupu spoju
                r = 0
                while not r:
                    radek = gen.next()
                    r = re.search(u'<td align="right">(.+?)</td>', radek, re.I)
                pom_str = r.group(1).replace(u'&#160;',u'')
                spoj_nastupy = re.split(u'<br>', pom_str)

                # najdu pripadne poznamky 
                r = 0
                while not r:
                    radek = gen.next()
                    r = re.search(u'<td align="right" nowrap>(.+?)</td>', radek, re.I)
                pom_str = r.group(1).replace(u'&#160;',u'')
                spoj_poznamky = re.split(u'<br>', pom_str)
                spoj_poznamky = map(self.odstran_tagy, spoj_poznamky)
                spoj_poznamky = map(self.nahrad_nechtene_retezce, spoj_poznamky)

                # hledam radek s odkazem na detaily o spoji (url na zpozdeni vlaku, url na razeni vlaku,...)
                while not re.search(u'<td nowrap align="right">', radek, re.I):
                    radek = gen.next()
                # poloha a zpozdeni vlaku
                url_poloha = ''
                r = re.search(u"<a href='(\S+)' target='_blank' title='Poloha vlaku'>", radek, re.I)
                if r:
                    url_poloha = r.group(1)
                # razeni vlaku
                url_razeni = ''
                r = re.search(u"<a href='(\S+)' target='RAZENI'", radek, re.I)
                if r:
                    url_razeni = r.group(1)

                # najdu typ spoje  (bus, vlak, pesky)
                while not re.search(u'<td nowrap>(.+?)</td>', radek, re.I):
                    radek = gen.next()
                pom_list = re.split(u'<br>', radek)
                spoj_typ_spoje = []
                spoj_cislo_spoje = []
                for pom_spoj in pom_list:
                    r = re.search(u"<a href='(Route.asp\S+)'.+?>(.+?)<", pom_spoj, re.I)
                    if r:
                        url_detaily_spoje = r.group(1)
                        cislo_spoje = self.nahrad_nechtene_retezce(r.group(2))
                        # pokud nemam polozku pro nazev spoje, vytvorim ji
                        if not cislo_spoje in self.ODPOVED.DICT_URL_DETAILY_SPOJU:
                            self.ODPOVED.DICT_URL_DETAILY_SPOJU[cislo_spoje] = {}
                        # ulozim nasbirane detaily
                        d = self.ODPOVED.DICT_URL_DETAILY_SPOJU[cislo_spoje]
                        d["trasa"] = url_detaily_spoje
                        if url_poloha:
                            d["poloha"] = url_poloha
                        if url_razeni:
                            d["razeni"] = url_razeni
                    else:
                        cislo_spoje = u''
                        url_detaily_spoje = u''
                    spoj_cislo_spoje.append(cislo_spoje)
                    if re.search(u'bus_p.gif|Bus:', pom_spoj, re.I):
                        spoj_typ_spoje.append(u"autobus")
                    elif re.search(u'train_p.gif|Vlak:', pom_spoj, re.I):
                        spoj_typ_spoje.append(u"vlak")
                    elif re.search(u'trol_p.gif|Trol:', pom_spoj, re.I):
                        spoj_typ_spoje.append(u"trolejbus")
                    elif re.search(u'tram_p.gif|Tram:', pom_spoj, re.I):
                        spoj_typ_spoje.append(u"tramvaj")
                    elif re.search(u'metro_p.gif', pom_spoj, re.I):
                        spoj_typ_spoje.append(u"metro")
                    elif re.search(u'foot_p.gif', pom_spoj):
                        r = re.search(u'esun asi (\d+) min', pom_spoj, re.I)
                        if r:
                            spoj_typ_spoje.append(u"přesun asi "+r.group(1)+u" min")
                        else:    
                            spoj_typ_spoje.append(u"přesun pěšky")
                    else:
                        spoj_typ_spoje.append(u'')

                # najdu zaverecnou poznamku - delka cesty apod.
                r = 0
                while not r:
                    radek = gen.next()
                    r = re.search(u'<td colspan="11">(.+?)</td>', radek, re.I)
                spoj_delka_a_cena = r.group(1)
                spoj_delka_a_cena = self.nahrad_nechtene_retezce(spoj_delka_a_cena)
                spojeni.poznamka = spoj_delka_a_cena
                    
                # vytvorim instance pro jednotlive prestupy a ulozim je
                spojeni.prestupy = []
                for pom_i in range(len(spoj_zastavky)):
                    # vytvorim novou instanci pro prestup
                    prestup = IDOS_Prestup()
                    # cas prijezdu
                    if pom_i<len(spoj_vystupy) and spoj_vystupy[pom_i]:
                        prestup.cas_prijezdu = string.rjust(spoj_vystupy[pom_i],5)
                    else:
                        prestup.cas_prijezdu = u"  *  "
                    # cas odjezdu
                    if pom_i<len(spoj_nastupy) and spoj_nastupy[pom_i]:
                        prestup.cas_odjezdu = string.rjust(spoj_nastupy[pom_i],5)
                    else:    
                        prestup.cas_odjezdu = u"  *  "
                    # zastavka
                    prestup.zastavka = spoj_zastavky[pom_i].rstrip()
                    # poznamka
                    if pom_i<len(spoj_poznamky):
                        prestup.poznamka = spoj_poznamky[pom_i]
                    # typ
                    if pom_i<len(spoj_typ_spoje):
                        prestup.typ = spoj_typ_spoje[pom_i]
                    # cislo spoje
                    if pom_i<len(spoj_cislo_spoje):
                        prestup.cislo_spoje = spoj_cislo_spoje[pom_i]
                    # pridam prestup do seznamu
                    spojeni.prestupy.append(prestup)
                
                # pridam spojeni do seznamu nalezenych
                self.ODPOVED.NALEZENA_SPOJENI.append(spojeni)

        except StopIteration:
            # prosel jsem uz vsechny radky, pouze odchytim vyjimku, aby to nevedlo k ukonceni programu
            pass

        # nyni nalezena spojeni trochu salamounsky zkratim na zadany max. pocet
        # sice bych je mohl nechat, ale v pripade, kdy chci i detaily, tak by se zbytecne hledaly i detaily ke spojum, ktere me nezajimaji
        # takhle je snazsi
        if self.DOTAZ.CAS_URCUJE_ODJEZD:
            # v pripade ze cas uctuje odjezd, chci ty ze zacatku seznamu
            self.ODPOVED.NALEZENA_SPOJENI = self.ODPOVED.NALEZENA_SPOJENI[:self.DOTAZ.MAX_SPOJU]
        else:
            # v pripade ze cas uctuje prijezd, chci ty z konce seznamu
            # v pripade ze cas uctuje odjezd, chci ty ze zacatku seznamu
            self.ODPOVED.NALEZENA_SPOJENI = self.ODPOVED.NALEZENA_SPOJENI[-self.DOTAZ.MAX_SPOJU:]

    

    def parsuj_detail_spoje(self):
        """ Parsuje html stranku s detailem spoje a extrahuje z ni jednotlive zastavky """
        
        # ziskam generator radku
        gen = self.generator_dat(data = 2)
        
        # ziskana data budu zpracovavat po radcich, je to tak snazsi
        # ziskam dalsi radek
        radek = gen.next()
            
        # zacnu vyhledavat konkretni tagy a z nich dolovat data
        # pocatek sekce s udajem o cisle spojeni
        while not re.search(u"<a title='", radek, re.I):
            radek = gen.next()
        nazev = self.nahrad_nechtene_retezce(self.odstran_tagy(radek)).strip()

        # pocatek sekce se seznamem zastavek
        while not re.search(u'<td align="left" nowrap>', radek, re.I):
            radek = gen.next()
        zastavky = self.nahrad_nechtene_retezce(gen.next()).split(u'<br>')

        # sekce s casy prijezdu
        while not re.search(u'<td nowrap>', radek, re.I):
            radek = gen.next()
        prijezdy = self.nahrad_nechtene_retezce(radek[radek.find(u'>')+1:]).split(u'<br>')

        # pocatek sekce s casy odjezdu
        while not re.search(u'<td>', radek, re.I):
            radek = gen.next()
        odjezdy = self.nahrad_nechtene_retezce(radek[radek.find(u'>')+1:]).split(u'<br>')

        # pocatek sekce s poznamkami
        while not re.search(u'<td nowrap align="right">', radek, re.I):
            radek = gen.next()
        poznamky = self.nahrad_nechtene_retezce(radek[radek.find(u'>')+1:]).split(u'<br>')

        # pocatek sekce s kilometry
        while not re.search(u'<td>', radek, re.I):
            radek = gen.next()
        kilometry = self.nahrad_nechtene_retezce(radek[radek.find(u'>')+1:]).split(u'<br>')
        
        # zpracuji jednotlive udaje o zastavkach
        seznam_zastavek = []
        for i in range(len(zastavky)-1):   # staci projit o 1 polozku min, to kvuli <br> na konci radku
        
            # vytvorim novou instanci pro zastavku 
            prestup = IDOS_Prestup()
            
            prestup.zastavka = self.odstran_tagy(zastavky[i])  # nazev zastavky
            if zastavky[i].find(u'<b>') >=0 :  # je-li tucne, jedna se o nastupni ci vystupni zastavku - pridam na zacatek *, abych ji poznal
                prestup.zastavka = u"*"+prestup.zastavka

            prestup.cas_prijezdu = self.odstran_tagy(prijezdy[i]) 
            prestup.cas_odjezdu = self.odstran_tagy(odjezdy[i])
            prestup.poznamka = self.odstran_tagy(poznamky[i])
            prestup.kilometr = self.odstran_tagy(kilometry[i])            

            # pridam ziskane udaje do seznamu
            seznam_zastavek.append(prestup)

        # vratim udaje se seznamem zastavek
        return seznam_zastavek



    def parsuj_zpozdeni_vlaku(self):
        """ Parsuje html stranku s detailem o pozici spoje a extrahuje z ni zpozdeni """
        # ziskam generator radku
        gen = self.generator_dat(data = 2)
        
        # ziskana data budu zpracovavat po radcich, je to tak snazsi
        # ziskam dalsi radek
        radek = gen.next()
        
        zpozdeni = ''
        # zacnu vyhledavat konkretni tagy a z nich dolovat data
        # nejdrive se posunu bliz tomu spravnemu mistu
        try:
            while not re.search(u"Informace ze stanice:", radek, re.I):
                radek = gen.next()
            # a nyni jiz na to spravne
            while not re.search(u'<td nowrap>', radek, re.I):
                radek = gen.next()
            zpozdeni = self.nahrad_nechtene_retezce(self.odstran_tagy(radek.split(u'<br>')[-1])).strip()

        # vyjimka - nenasel jsem informace v pozadovanem formatu
        except StopIteration:
            pass

        return zpozdeni





class IDOS:
    """ Trida IDOS slouzi k vyhledavani dopravnich spojeni prostrednictvim serveru typu Idos """


    def __init__(self):

        self.TYPY_SPOJU = ["VLAK", "BUS", "KOMB", "BRNO", "PRAHA", "OSTRAVA", "LIBEREC"]
        self.PROSTREDNICI = [IDOS_Prostrednik_jizdnirady_cz(), IDOS_Prostrednik_vlak_cz()]
        self.DOTAZ = ""             # parametry hledaneho spojeni
        self.ODPOVED = ""       # nalezena spojeni
        self.CLI_MOD = 0   # ovlivnuje chovani programu (0 = zadne vystupy, 1 = vypis pro batch mode, 2 = interaktivni pri spusteni z konole



    def vyhledej_spojeni(self, parametry_spoje):
        """ Vyhleda dopravni spojeni, v pripade CLI je i vytiskne """
        
        self.DOTAZ = parametry_spoje
        
        # smycka, ve ktere budu posilat dotaz na kazdy z definovanych prostredniku, dokud u nejakeho neuspeji
        while len(self.PROSTREDNICI)>0:

            if DEBUG:
                print "pouzivam server: ", self.PROSTREDNICI[0].IDOS_URL

            self.ODPOVED = self.PROSTREDNICI[0].vyhledej_spojeni(self.DOTAZ)

            # pokud doslo k chybe, odstranim prostrednika a opakuji dotaz
            if self.ODPOVED.NAVRATOVY_KOD == KOD_NEZNAMY_PARAMETR_LINK:
                if DEBUG:
                    print "doslo k chybe, zkusim dalsi server", self.PROSTREDNICI
                self.PROSTREDNICI.pop(0)
            else:
                break
        
        # pokud vsechny servery selhaly
        if DEBUG and (self.ODPOVED.NAVRATOVY_KOD == KOD_NEZNAMY_PARAMETR_LINK):
            print "vsechny servery selhaly, koncim..."
        
        if self.CLI_MOD > 0:
            self.vypis_zpracovana_data()



    def vypis_zpracovana_data(self):
        """ V zavislosti na pouzitem rozhrani prezentuje nalezene vysledky """
   
        kod = self.ODPOVED.NAVRATOVY_KOD

        if kod == KOD_NEJEDNOZNACNE_KONCOVE_BODY:
            # nejednoznacne zadane koncove body    
           
            #print self.VYBER_ODKUD
            #print self.VYBER_KAM

            if self.CLI_MOD == 2:  # interaktivni mod

                # nepresne zadane misto odkud
                if len(self.ODPOVED.VYBER_ODKUD) > 1:
                    volba = self.CLI_vyber_z_menu(self.ODPOVED.VYBER_ODKUD, u"Upřesněte počátek cesty")
                    self.DOTAZ.ODKUD2 = self.ODPOVED.VYBER_ODKUD[volba].split(u":")[-1]
   
                # nepresne zadane misto kam
                if len(self.ODPOVED.VYBER_KAM) > 1:
                    volba = self.CLI_vyber_z_menu(self.ODPOVED.VYBER_KAM, u"Upřesněte cíl cesty")
                    self.DOTAZ.KAM2 = self.ODPOVED.VYBER_KAM[volba].split(u":")[-1]
               
                #print self.DOTAZ.ODKUD2, self.DOTAZ.KAM2
               
                # novy dotaz s upresnenymi udaji
                self.ODPOVED = self.vyhledej_spojeni(self.DOTAZ)

            if self.CLI_MOD == 1:  # batch mod
                # vypisi nabidku moznosti pro koncove body
                print(u"CHOOSE".encode(KODOVANI_SYSTEM))
                print(u"FromList".encode(KODOVANI_SYSTEM))
                for misto in self.ODPOVED.VYBER_ODKUD:
                    print(misto.encode(KODOVANI_SYSTEM))
                # cast kam
                print(u"ToList".encode(KODOVANI_SYSTEM))
                for misto in self.ODPOVED.VYBER_KAM:
                    print(misto.encode(KODOVANI_SYSTEM))
                print(u"ENDCHOOSE".encode(KODOVANI_SYSTEM))

        elif kod == KOD_SPOJ_NALEZEN:
            # hledane spojeni bylo nalezeno
            #self.parsuj_nalezena_spojeni()

            # vypisu nalezena spojeni
            for spojeni in self.ODPOVED.NALEZENA_SPOJENI:

                spojeni.tiskni(zpozdeni = self.ODPOVED.DICT_ZPOZDENI_VLAKU)

                if self.DOTAZ.ZISKAT_TRASU_SPOJE:  # vypisi detaily o jednotlivych spojich
                    for prestup in spojeni.prestupy:
                        print
                        self.vypis_detaily_spoje(prestup.cislo_spoje)
            print

        else:
            # behem k hledani doslo k chybe
            #if DEBUG:
            print self.ODPOVED.POPIS_CHYBY.encode(KODOVANI_SYSTEM)


   
    def vypis_detaily_spoje(self, cislo):
        """ Vypise detaily zadaneho spoje. Tyto detaily jiz musi byt nacteny ve slovniku self.DICT_DETAILY_SPOJU """
       
        if cislo in self.ODPOVED.DICT_DETAILY_SPOJU:

            detaily = self.ODPOVED.DICT_DETAILY_SPOJU[cislo]
           
            # podle typu vypisu profiltruji vypisovane zastavky
            if self.DOTAZ.ZISKAT_TRASU_SPOJE == 1:   # vypisuji pouze zastavky mezi nastupem a vystupem
                vypsat = False
                vypisovane_zastavky = []
                for i in range(0, len(detaily)):
                    if detaily[i].zastavka[0] == u'*' and (not vypsat):  # zastavka kde nastupuji
                        vypsat = True
                        vypisovane_zastavky.append(i)
                    elif detaily[i].zastavka[0] == u'*' and vypsat:  # zastavka kde vystupuji
                        vypisovane_zastavky.append(i)
                        break
                    elif vypsat: # jsem mezi nastupni a vystupni zastavkou
                        vypisovane_zastavky.append(i)  
                   
            elif self.DOTAZ.ZISKAT_TRASU_SPOJE == 2:  # vypisuji vsechny zastavky
                vypisovane_zastavky = range(0, len(detaily))
           
            else:  # neznama hodnota, nemelo by nastat
                return
           
            # najdu nejvetsi sirku nazvu a poznamky
            hlavicka = u"=== "+detaily[0].cislo_spoje+u" ==="
            max1 = len(hlavicka)
            max2 = 3
            for i in vypisovane_zastavky:
                max1 = max(max1, len(detaily[i].zastavka))
                max2 = max(max2, len(detaily[i].poznamka))
            max1 += 3
            if max2 > 0:
                max2 += 2

            s = hlavicka.ljust(max1)+u' Příj. '+u'  Odj.'+u'  Pozn.'
            print s.encode(KODOVANI_SYSTEM)

            for i in vypisovane_zastavky:
                zastavka = detaily[i].zastavka
                if zastavka[0] == u'*':
                    zastavka = zastavka.upper()
                else:
                    zastavka = u' '+zastavka
                s = zastavka.ljust(max1)+detaily[i].cas_prijezdu.center(7)+detaily[i].cas_odjezdu.center(7)+u'  '+detaily[i].poznamka.ljust(max2)+detaily[i].kilometr.rjust(4)+u' km'
                print s.encode(KODOVANI_SYSTEM)


    def CLI_vypis_verzi(self):
        """ Program vypise verzi pro pouziti v CLI """
        print "Skript hleda dopravni spoje prostrednictvim serveru idos.cz\nVerze ", VERSION
   

    def CLI_vypis_napovedu(self):
        """ Program vypise napovedu pro pouziti v CLI """
       
        self.CLI_vypis_verzi()
        print """
Pouziti:  spoje.py [prepinace] typ_spoje odkud[:kod] kam[:kod]

Argumenty:
    typ_spoje   jedna z nasledujicich moznosti:
                  vlak - vlakova spojeni v CR
                  bus - autobusove spoje v CR
                  komb - autobusove a vlakove spoje v CR
                  brno - MHD v Brne (vcetne IDS JMK)
                  praha - MHD v Praze
                  ostrava - MHD v Ostrave
                  liberec - MHD v Liberci
    odkud       Retezec urcujici misto (zastavku) odjezdu. Viceslovny
                nazev je treba (spolu s pripadnym kodem) uzavrit do
                uvozovek nebo apostrofu.
    kam         Retezec urcujici misto (zastavku) prijezdu. Viceslovny
                nazev je treba (spolu s pripadnym kodem) uzavrit do
                uvozovek nebo apostrofu.
    kod         Retezec identifikujici misto v pripade nejednoznacneho
                zadani.

Prepinace:
    -b          Batch mode - nepta se na pripadne upresneni spoje.
    -c cas      Cas odjezdu resp. prijezdu (do cilove stanice)
                hledaneho spojeni (defaultni hodnotou je aktualni cas).
                Cas odjezdu specifikujeme absolutne, napriklad '-c 10:00'
                nebo relativne, napriklad '-c +2:00' nebo '-c +20'.
                Cas prijezdu se specifikuje pomoci znaku 'p' hned za
                zadanym casem, tedy napriklad '-c 10:00p' oznacuje
                spojeni s casem prijezdu pred 10:00.
    -d datum    Datum odjezdu/prijezdu (defaultni hodnotou je aktualni
                datum), napriklad '-d 25.7.' nebo '-d 25.7.2008' pripadne
                relativne, napriklad '-d +2'.
                Pri neuvedeni roku se pouzije aktualni kalendarni rok.
    -p cislo    Maximalni pocet prestupu (defaultni hodnota 3)
    -s cislo    Pocet hledanych spoju (defaultni hodnota 5)
    -t          U kazdeho spoje vypise zastavky na hledane trase
    -T          U kazdeho spoje vypise zastavky na cele jeho trase
    -z          Dohledani informace o zpozdeni vlaku
    -v          Mod slouzici pouze pro ladici ucely
    --proxy=url Nastaveni proxy bez 'http://', napr. --proxy=my_company.cz:8080
    --version   Verze programu
    """


   

    def CLI_vyber_z_menu(self, option_list, otazka=u"Upřesněte výběr", prompt=u'Vaše volba: '):
        """ Vypise dialog pro vyber z nabizenych moznosti a vraci cislo vybrane polozky """

        print otazka.encode(KODOVANI_SYSTEM)
        n = len(option_list)
        for i in range(n):
            print `i+1`+") "+option_list[i].split(":",1)[0].encode(KODOVANI_SYSTEM)
        c = 0
        while c not in range(1,n+1):
            c = raw_input(prompt.encode(KODOVANI_SYSTEM))
            if c.isdigit():
                c = int(c)
            else:
                c = 0
            print
        return c-1



if __name__ == "__main__":

    idos = IDOS()
    
    parametry = IDOS_Dotaz()

    if ZPRACOVAT_ARGUMENTY:
   
        try:
            #opts, args = getopt.getopt(sys.argv[1:], "c:d:p:s:btTzv", ["version"])
            opts, args = getopt.getopt(sys.argv[1:], "c:d:p:s:btTzv", ["proxy=", "version"])
        except getopt.GetoptError, err:
            #     print help information and exit:
            print str(err) # will print something like "option -a not recognized"
            idos.CLI_vypis_napovedu()
            sys.exit(2)
   
        dict_opts = dict(opts)
   
        # zpracuji predane parametry
   
        if "--version" in dict_opts:
            idos.CLI_vypis_verzi()
            sys.exit(0)

        elif len(args) != 3:
            idos.CLI_vypis_napovedu()
            sys.exit(2)

        if "-v" in dict_opts:
            DEBUG = 1

        if "--proxy" in dict_opts:
            HTTP_PROXY = dict_opts["--proxy"]
            if DEBUG:
                print "pouzivam proxy: ", HTTP_PROXY
   
        typ = args[0].upper()
        if not typ in idos.TYPY_SPOJU:
            idos.CLI_vypis_napovedu()
            sys.exit(2)
        else:
            parametry.TYP_SPOJE = typ
   
        if args[1].find(":")>-1:
            parametry.ODKUD, parametry.ODKUD2 = unicode(args[1], KODOVANI_SYSTEM).split(u":", 1)
        else:
            parametry.ODKUD = unicode(args[1], KODOVANI_SYSTEM)
            parametry.ODKUD2 = u""

        if args[2].find(":")>-1:
            parametry.KAM, parametry.KAM2 = unicode(args[2], KODOVANI_SYSTEM).split(u":", 1)
        else:
            parametry.KAM = unicode(args[2], KODOVANI_SYSTEM)
            parametry.KAM2 = u""

        if "-d" in dict_opts:
            datum = dict_opts["-d"]

            if datum[0] == '+':    # pokud je datum zadano relativne, prictu zadany pocet dni k aktualnimu datu
                d = datum[1:]
                t = time.localtime(time.time()+int(d)*3600*24)
                datum = time.strftime("%d.%m.%Y", t)
            elif datum[-1] == u'.':   # konci teckou, tedy byl zadan jen den a mesic
                datum += time.strftime("%Y")   # pridam na konec aktualni rok

            parametry.KDY = unicode(datum, KODOVANI_SYSTEM)
                
        else:
            parametry.KDY = unicode(time.strftime("%d.%m.%Y"))
   
        if "-c" in dict_opts:
            if dict_opts["-c"][-1] == "p":
                cas = dict_opts["-c"][:-1]
                parametry.CAS_URCUJE_ODJEZD = 0
            else:
                cas = dict_opts["-c"]
            
            if cas[0] == '+':    # pokud je cas zadan relativne
                cas = "0:"+cas[1:]      # ziskam zadane hodiny a minuty 
                h = cas.split(":")[-2]
                m = cas.split(":")[-1]
                t = time.localtime(time.time()+int(h)*3600+int(m)*60)   # prictu prislusny pocet sekund k aktualnimu casu
                cas = (time.strftime("%H:%M",t))
                
                if not "-d" in dict_opts:   # pokud nebylo explicitne zadano datum, upravim datum podle relativniho casu (muze presahovat do dalsiho dne) 
                    parametry.KDY = unicode(time.strftime("%d.%m.%Y",t))
            
            parametry.CAS = unicode(cas, KODOVANI_SYSTEM)
            
        else:
            parametry.CAS = unicode(time.strftime("%H:%M"))
  
        if "-p" in dict_opts:
            parametry.MAX_PRESTUPU = int(dict_opts["-p"])
        else:
            parametry.MAX_PRESTUPU = 3
   
        if "-s" in dict_opts:
            parametry.MAX_SPOJU = int(dict_opts["-s"])
        else:
            parametry.MAX_SPOJU = 5
       
        if "-b" in dict_opts:
            idos.CLI_MOD = 1
        else:
            idos.CLI_MOD = 2

        if "-t" in dict_opts:
            parametry.ZISKAT_TRASU_SPOJE = 1   # pouze zastavky na trase
        elif "-T" in dict_opts:
            parametry.ZISKAT_TRASU_SPOJE = 2   # vsechny zastavky uvedenych spoju

        if "-z" in dict_opts:
            parametry.ZISKAT_ZPOZDENI_VLAKU = 1


    # vyhledam pozadovane spojeni
    idos.vyhledej_spojeni(parametry)



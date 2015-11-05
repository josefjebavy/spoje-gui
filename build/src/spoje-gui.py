#!/usr/bin/env python
# -*- coding: utf-8 -*-
#! coding:utf8


#    @license: 
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
# Program slouzi k hledani dopravnich spojeni prostrednictvim serveru IDOS
# Je to graficka nadstavba nad program spoje.py
#
# @requires: spoje.py (http://code.google.com/p/spoje/)
# @author: Josef 'multi' Jebavý 
# @email:josef.jebavy[at]gmail.com
#
#     

import elementary
import evas




from functools import partial
import spoje
import string
import os
import sqlite3

"""TODO 
odchytavat  chyby :
        -sitove pripojeni k serveru - hotovo
        -spatne zadane konce zastavek - hotovo
        -pokud nic nenajde - hotovo
        
 moznost prehodit odkud kam-hotovo
 moznost ragovat nebo aspon vypsat pokud se nepresne urci mesto - hotovo
  (nejdrive pouzito inner window ted se zobrazuje vse pres pager
  obsluhuju pomoci tridy showData)
 
 pridat prepinac z , ktery dohledava zpozdeni
 taky -t se obcas hodi, ale trva dlouho vypisuje zastavky na hledane trase
 
 vypnuti/zapnuti zobrazovani poznamky - hotovo
 max pocet prestumu(bez prestupu)(by mohl bejt posuvnik)? -hotovo, urceni cislem
 
 zapamatovani vyhledaneho spoje ! nebo i vice a ukladat je
    - ukladadat do DB - SQLlite
          - defaultni nastaveni  - hotovo
                 - zobrazovat poznamku
                 - pocet prestupu
                 - mista od do
                 - typ spoje
          - ukladani vyhledaneho spojeni do DB - hotovo
            -pripadne v tom i vyhledavat
          
    
 
 upresneniMista mista prepsat tak ze tlacika budou ubjekty,
      ktere se uz o vse samy postaraji - hotovo
 
 
 #pokud budou samostatne tak dat do export PYTHONPATH=/usr/lib/python2.6/site-packages/remoko
"""

"""
add v0.2 :
    - prepsani kodu
    - vyber mista pri nejeasne specifikaci
    - check(box) jestli se ma nebo neba zobrazovat poznamka
    - max pocet spojeni a prestupu
add v0.3:
    - uprava struktury kodu
    -pozor do verze 0.2 program obsahoval bug, 
    ktery v pripade ze bylo nalezeno vice spojeni zobrazil jen posledni najity
    - jednoduche osetreni vyjimky pri nefunkcnim internetu
add v0.3.1:
    -new icon
add v0.3.2:
    - upravy kvuli nove verzi python-elementary
add v0.4.0:
    - ukladani nastaveni do DB
    - ukladani vyhledanaho spojeni do DB
add v0.4.1:
    - oprava chyby nefunkcnosti zapricinena kodovanim
    - zobrazovani dat neni pres innerwindow -> zobrazuje se pres celou obrazovku

unicode(text, 'utf-8')
decode('utf-8')
encode('utf-8')
"""
version="0.4.1"

class database:
    def __init__(self):
        self.cfg_path = os.path.join(os.path.expanduser("~"), ".config/spoje")
        if not os.path.exists(self.cfg_path):
            os.makedirs(self.cfg_path)
        self.db_path = os.path.join(self.cfg_path, 'spoje.db')      
        
        self.connect()
            
        #TODO ulozit si tam i verzi programu bude se do budoucna hodit
        #if not exists
        try:            
            self.curs.execute("""create table   config 
        (id integer primary key, poznamka integer,prestupu integer,spoju integer, odkud text, kam text,typ text )
        """)
            self.curs.execute("""insert into config values (1,1,3,2,'Odkud','Kam','VLAK')""") 
        except sqlite3.OperationalError: 
            print "tabulka config uz existuje"
            
        try:            
            self.curs.execute("""create table   version 
        (id integer primary key, version text )
        """)
            self.curs.execute("""insert into version (version)values (?)""",[version]) 
        except sqlite3.OperationalError: 
            print "tabulka version uz existuje"
            
                          
        self.curs.execute("""create table if not exists  spoje
        (idSpoje integer primary key, datum text, odkud text,kam text,spoj text,typ text,poznamka text)
        """)
        
    def __del__(self):
#        self.conn.commit()
        self.close()
        
        
    def connect(self):
        print "pripojeni k DB"
        self.conn = sqlite3.connect(self.db_path)
        self.curs = self.conn.cursor()
            
             
    def close(self):
        print "odpojeni od DB"
        self.conn.commit()
        self.curs.close();
        self.conn.close();
        
#    def getConfig(self):
#        """select id,poznamka,prestup,odkud,kam,typ"""
#        return self.curs.execute("""select id,poznamka,prestupu,spoju,odkud,kam,typ""")
    
    def getPoznamka(self):
        return self.curs.execute("""select poznamka from config""").next()[0]
    def getPrestupu(self):
        return self.curs.execute("""select prestupu from config""").next()[0]
    def getSpoju(self):
        return self.curs.execute("""select spoju from config""").next()[0]
    def getOdkud(self):
        return self.curs.execute("""select odkud from config""").next()[0]
    def getKam(self):
        return self.curs.execute("""select kam from config""").next()[0]
    def getTyp(self):
        return self.curs.execute("""select typ from config""").next()[0]

        
    def deleteSpoj(self, idSpoje):
        print "deleteSpoj:"
        print idSpoje
        self.curs.execute("""delete from spoje where idSpoje=?""" , [int(idSpoje)])
        
    def insertSpoj(self,  datum , odkud,kam ,spojText,typ,poznamka):
        print "insertSpoj"
        self.curs.execute(""" insert into spoje  (datum, odkud ,kam ,spoj,typ,poznamka ) 
             values(?,?,?,?,?,?)  """,(datum,odkud,kam,spojText,typ,poznamka))
        
    def selectSpoje(self):
        print "selectSpoje"
        return self.curs.execute(""" select idSpoje,datum, odkud ,kam ,spoj,typ,poznamka from spoje """)
        

    def selectSpoj(self,idSpoje):
        print "selectSpoj" 
        self.curs.execute(""" select datum, odkud ,kam ,spoj,typ,poznamka from spoje where idSpoje=?""",(idSpoje))
                
    def updateConfig(self, poznamka, prestupu, spoju, odkud, kam, typ):
        
        
        self.curs.execute("""update config set 
           poznamka=?,prestupu=?,
           spoju=?,odkud=?,
           kam=?,typ=?
           where id=1
        """,(poznamka, prestupu, spoju, odkud, kam, typ)) 
        


class Info (elementary.Box):
    def __init__(self,win,database,bubble):
        
        elementary.Box.__init__(self,win)
        self.bubble=bubble
        self.database=database
        
        self.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
        self.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)       
        self.show()
        
        self.button = elementary.Button(win)
        self.button.show()

        self.pack_end(self.bubble)
        self.pack_end(self.button)




class InfoSave (Info):
    def __init__(self,win,database,bubble):
        Info.__init__(self,win,database,bubble)

        self.button.label_set("Save")
        self.button.callback_clicked_add(self.save)
    
    def save(self,evn):
        print "save spoje"
        self.database.insertSpoj(self.bubble.datum.decode(spoje.KODOVANI_SYSTEM) ,
                                 self.bubble.odkud.decode(spoje.KODOVANI_SYSTEM), 
                                 self.bubble.kam.decode(spoje.KODOVANI_SYSTEM),
                                  self.bubble.text.decode(spoje.KODOVANI_SYSTEM),
                                  self.bubble.typ.decode(spoje.KODOVANI_SYSTEM), 
                                  self.bubble.poznamka.decode(spoje.KODOVANI_SYSTEM))
        
        
class InfoDelete (Info):
    def __init__(self,win,database,bubble,idSpoje):
        self.idSpoje=idSpoje
        Info.__init__(self,win,database,bubble)
        self.button.label_set("Delete")
        self.button.callback_clicked_add(self.delete)
    
    def delete(self,evn):
        self.database.deleteSpoj(self.idSpoje)
        
        #zavolam metodu nadtridy
        Info.delete(self)
#        self.delete()
    
class Bubble(elementary.Bubble):
    def __init__(self,win,odkud,kam,typ,datum,text,poznamka,poznamkaCheck):
        elementary.Bubble.__init__(self,win)
        
        
        self.win=win
        
        self.odkud=odkud
        self.kam=kam     
        self.typ=typ   
        self.datum=datum
        self.text=text
        self.poznamka=poznamka
        
        self.label_set(typ+":"+odkud+"->"+ kam +" "+datum)
        #nepouzito
#        self.info_set(datum)
        
        labelData = elementary.Label(win)
        labelData.show()
        labelData.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
        labelData.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)  
        if poznamkaCheck == True:
#            poznamka= 'Pozn.: ' + spojeni.poznamka + oddelovac
            labelData.label_set(text+poznamka)
        else:
            labelData.label_set(text)
#        
#        labelData.label_set(text)
                                      
                        
        labelData.show()
        
        self.content_set(labelData)
        self.show()   

class showData(elementary.Box):   
#class showData(elementary.InnerWindow):
#class showData(elementary.Window):   
#    def __init__(self,win,elementary):
    """okno, ktere zobrazy nalezene vysledky"""

    def __init__(self,win,mainPage,pager):
            

#        elementary.InnerWindow.__init__(self,win)
        super(showData, self).__init__(win)

        self.win=win
        self.pager=pager
        self.mainPage=mainPage
        
        box = elementary.Box(win)
        box.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
        box.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)       
        box.show()

#        self.content_set(box)
        self.pack_end(box)
   
        self.scroller = elementary.Scroller(win)
        self.scroller.show()
        self.scroller.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
        self.scroller.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)    
    
    
        btCloseIW = elementary.Button(win)
        btCloseIW.label_set("zavrit")
        btCloseIW.show()
        btCloseIW.callback_clicked_add(self.hideIW)

        
        box.pack_end(self.scroller)
        box.pack_end(btCloseIW)
        
        #----------------------------
        
        self.makeNewBox()
        
        self.show()
        
            

       
    def showDatabox(self, data):
        """pridava polozky pro zobrazeni"""
        """pak je jeste potreba zalovat show() !!!"""

        self.box2.pack_end(data)
        
    def show(self):
        self.pager.content_promote(self)

            
    def showError(self, data):
        """metoda pro zobrazeni textu"""
        self.labelData = elementary.Label(self.win)
        self.labelData.show()
        self.labelData.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
        self.labelData.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)

        
        self.labelData.label_set(data)

        self.showDatabox(self.labelData)
        self.show() 


    def hideIW(self, event):
        """posluchac, ktery zavre okno s vysledky""" 
        self.pager.content_promote(self.mainPage)

        self.box2.delete()
        self.makeNewBox()
        
    def makeNewBox(self):
        self.box2 = elementary.Box(self.win)
        self.box2.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
        self.box2.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)       
        self.box2.show()
        self.scroller.content_set(self.box2)
        
        

         
        
class SpojeGUI:
    
           
  
       
    def destroy(self, event, *args, **kargs):
            """metoda ktera zavre okno a ukonci program"""
            
            elementary.exit()
            self.database.close()
            
    def saveConfig(self, event, *args, **kargs):
        """metoda ulozi soucasne nastaveni"""
        print "saveConfig" 
#        print self.poznamkaCheck.state_get()
 
        if         self.poznamkaCheck.state_get() == True:
            poznamka = 1
        else:
            poznamka = 0

        prestupu = int(self.prestupyEntry.entry_get())
        spoju = int(self.spojeEntry.entry_get())
        odkud = str (self.odkudEntry.entry_get())
        kam = str (self.kamEntry.entry_get())
        
        self.database.updateConfig(poznamka, prestupu, spoju, odkud, kam, self.typSpoje)
        
            
    def showSaved(self, event, *args, **kargs):
        """metoda ktera zobrazi ulozene spoje"""
       
        for i in self.database.selectSpoje():
            bb=Bubble(self.win, i[2], i[3], i[5], i[1], i[4], i[6],self.poznamkaCheck.state_get()  )            
            self.showData.showDatabox(InfoDelete(self.win, self.database, bb, i[0]) )
            print i

        self.showData.show()
        
   

        
                            
    def search(self, event, *args, **kargs):
            """posluchac tlacitka search, nastavuje parametry vyhledavani 
                a pak zavola hledani spoju"""
        

            print "search"

            print "typSpoje:" + self.typSpoje
#            idos = self.idos       
            #idos.CLI_MOD=1 

            self.idosDotaz = spoje.IDOS_Dotaz()
            
            str = self.prestupyEntry.entry_get() #[: - 4] 
            print "str prestupu:\"" + str + "\""
            try:
                self.idosDotaz.MAX_PRESTUPU = int(str)  
            except  ValueError:
                errorStr = "spatne hodnota pro maximum prestupu"
                print  errorStr + " ValueError"
                self.showData.showError(errorStr)
                return 
                
            str = self.spojeEntry.entry_get() #[: - 4]  
            print "str spoju:\"" + str + "\""
            try:
                self.idosDotaz.MAX_SPOJU = int(str)
            except  ValueError:
                errorStr = "spatne hodnota pro maximum spoju"
                print  errorStr + " ValueError"
                self.showData.showError(errorStr)
                return 

            
            str = self.odkudEntry.entry_get()#[: - 4] 
            print "str Odkud:\"" + str + "\""
            self.idosDotaz.ODKUD = str            
            str = self.kamEntry.entry_get()#[: - 4]
            print "str Kam :\"" + str + "\""
            self.idosDotaz.KAM = str
            
            str1 = self.hodinaEntry.entry_get()#[: - 4]
            print "str Hodina :\"" + str1 + "\""
            str2 = self.minutaEntry.entry_get()#[: - 4]
            print "str Minuta :\"" + str2 + "\""
            self.idosDotaz.CAS = str1 + ":" + str2                        
          
            str1 = self.denEntry.entry_get()#[: - 4]
            print "str Den :\"" + str1 + "\""
            str2 = self.mesicEntry.entry_get()#[: - 4]
            print "str Mesic :\"" + str2 + "\""
            self.idosDotaz.KDY = str1 + "." + str2
            
            
            self.idosDotaz.TYP_SPOJE = self.typSpoje
            
        

    
            try:
                self.idos.vyhledej_spojeni(self.idosDotaz)
            except :
                errorStr1 = "problem pri vyhledavani spojeni"
                errorStr2 = "napr problem se siti"
                print errorStr1
                print errorStr2
                self.showData.showError(errorStr1 + "<br>" + errorStr2)
                
                return
        

            print "dotaz proveden"
               
                     
            znovaDotaz = False
            
            
            """ jako prvni testovat KAM pak se jako posledni zobrazi ODKUD\
             a bude tedy na vrchu a videt jako prvni"""
            if len(self.idos.ODPOVED.VYBER_KAM) > 1:
                print "Kam je vetsi-vice moznosti:"
                for i in self.idos.ODPOVED.VYBER_KAM:
                    print i.encode(spoje.KODOVANI_SYSTEM)
                self.upresneniMista("Upresneni Kam",
                                     self.idos.ODPOVED.VYBER_KAM,
                                      self.idos.DOTAZ, 
                                      self.kamEntry)
#                                    unicode(self.idos.ODPOVED.VYBER_KAM, spoje.KODOVANI_SYSTEM),
#                                    unicode(self.idos.DOTAZ, spoje.KODOVANI_SYSTEM),
#                                    unicode(self.kamEntry, spoje.KODOVANI_SYSTEM) )
                znovaDotaz = True
                
               
            else:
                print "Kam je mensi-jen jedna moznost"
            
            if len(self.idos.ODPOVED.VYBER_ODKUD) > 1:
                print "Odkud je vetsi-vice moznosti:"
                for i in self.idos.ODPOVED.VYBER_ODKUD:
                    print i.encode(spoje.KODOVANI_SYSTEM)
                self.upresneniMista("Upresneni odkud", self.idos.ODPOVED.VYBER_ODKUD, self.idos.DOTAZ.ODKUD2, self.odkudEntry)
                znovaDotaz = True
            else:
                print "Odkud je mensi-jen jedna moznost"
        

                
                
                
            if znovaDotaz:
                print "dotaz se bude muset provest znova"
               
                
            else:
                self.vypis_zpracovana_data()
          
     
    def upresneniMista(self, text, pole, dotazUloz, entryUloz):
        """zobrazy okno pro moznost vyberu upresneni mista"""

        label = elementary.Label(self.win)
        label.label_set(text)
        label.show()

        self.showData.showDatabox(label)

        """vytvoreni tlacitek s presnymi nazvy mist"""
        for i in pole:
            misto = i.split(":")
            mistoJmeno = misto[0]
            mistoKod = misto[1]
            print "[" + i.encode(spoje.KODOVANI_SYSTEM) + "] " + "split 0: " + \
             mistoJmeno.encode(spoje.KODOVANI_SYSTEM) + " split 1: " + \
             mistoKod.encode(spoje.KODOVANI_SYSTEM)
            
     
            button = elementary.Button(self.win)
            button.label_set(mistoJmeno)
            button.show()

            button.callback_clicked_add(self.nastavUpresneniMista,  entryUloz, mistoKod , mistoJmeno)
            button.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            button.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
    
            self.showData.showDatabox(button)

        self.showData.show()
        
        
    def nastavUpresneniMista(self, event, entryUloz, mistoKod , mistoJmeno):
        """nastavuje spravne mesto """
        """nevymyslel jsem jak nastavit, aby nastavovalo primo hodnoty pro IDOS ODKUD2/KAM2"""
        """pak je treba znova zmackout search"""
        

        print "mistoJmeno:" + mistoJmeno.encode(spoje.KODOVANI_SYSTEM)
        print "mistoKod:" + mistoKod.encode(spoje.KODOVANI_SYSTEM)
        entryUloz.entry_set(mistoJmeno)


        #print "mistoKod:"+mistoKod
        #print "dotazUloz"+dotazUloz
        
#        print self.idos.DOTAZ
#        print "ODKUD: "+ self.idos.DOTAZ.ODKUD
#        print "KAM: "+ self.idos.DOTAZ.KAM
#        
#        print "ODKUD2: "+ self.idos.DOTAZ.ODKUD2
#        print "KAM2: "+ self.idos.DOTAZ.KAM2
        
        #self.idos.vyhledej_spojeni(self.idos.DOTAZ)
#        print "dotaz proveden znova"
        print "dotaz provedte znova!"
        #data=self.vypis_zpracovana_data(self.idos)
        #self.showData(data)
        
        self.showData.hideIW(None)
#        iw.delete()
        
    def vypis_zpracovana_data(self):
            """ V zavislosti na pouzitem rozhrani prezentuje nalezene vysledky """
        
            oddelovac = "<br>"        
            odpoved = self.idos.ODPOVED
            zpozdeni = self.idos.ODPOVED.DICT_ZPOZDENI_VLAKU
            kod = odpoved.NAVRATOVY_KOD
            KOD_SPOJ_NALEZEN = 0
            
         
              
            if kod == KOD_SPOJ_NALEZEN: #idos.KOD_SPOJ_NALEZEN:
                # hledane spojeni bylo nalezeno
                #self.parsuj_nalezena_spojeni()
                
              
                # vypisu nalezena spojeni
#                str = "" #definice uz tady jinak me to ulozi jen posledni spojeni
                for spojeni in self.idos.ODPOVED.NALEZENA_SPOJENI:
                    ################
                
                    
                   
            
            # projdu jednotlive nastupy/prestupy
                    str=""
                    poznamka=""
                    for prestup in spojeni.prestupy:
    
                        spoj_vypis = prestup.cas_prijezdu.rjust(5) + u'  ' + prestup.cas_odjezdu.rjust(5) + u'  ' + prestup.zastavka  # prijezd, odjezd, zastavka
                        if prestup.poznamka:  # poznamka
                            spoj_vypis += u", " + prestup.poznamka
                        if prestup.typ:  # typ spoje
                            spoj_vypis += u", " + prestup.typ
                        if prestup.cislo_spoje:  # jmeno (cislo) spoje
                            spoj_vypis += u" " + prestup.cislo_spoje
                    # pokud byl predan slovnik se zpozdenimi spoju, vytisknu i zpozdeni tohoto konkretniho spoje
                            if prestup.cislo_spoje in zpozdeni:
                                spoj_vypis += u", zpoždění " + zpozdeni[prestup.cislo_spoje]
                
                # vytisknu nalezeny spoj
                        str += spoj_vypis + oddelovac
                        
                    #########33
                    bb=Bubble(self.win,self.idosDotaz.ODKUD,self.idosDotaz.KAM,self.typSpoje,spojeni.datum, str, spojeni.poznamka,self.poznamkaCheck.state_get())
                    self.showData.showDatabox(InfoSave( self.win,self.database,bb))
                    self.showData.show()
                    

            
            else:
                  str = " zadny spoj nenalezen "
                  
                  self.showData.showError(str)

                # behem k hledani doslo k chybe
    #            if DEBUG:
    #                print self.ODPOVED.POPIS_CHYBY.encode(KODOVANI_SYSTEM)
            print str.encode()

#    def save_zpracovana_data(self,event,data):
#        """ulozi spojeni do DB"""    
##        print "save_zpracovana_data NOT IMPLEMENTED YET"
##        print event
#        
#        self.database.insertSpoj(data)
         
          
    
    def hoverselUpdate (self, typ, arg, event):
        """posluchac pro vyber typu spojeni"""

       # print "event: " + event

        print "typ:" + typ
                        
        self.typSpoje = typ
            

        self.hoversel.label_set(typ)
        
    def prehodit(self, obj):
        """prehodi misto odkud kam""" 

        temp = self.odkudEntry.entry_get()
        self.odkudEntry.entry_set(self.kamEntry.entry_get())
        self.kamEntry.entry_set(temp)
        print "prehozeno odkud kam"
        

    def fillTypSpoje (self):
            """vytvori hlavni okno a naplni ho objekty"""
        
            
                        
            hoverFrame = elementary.Frame(self.win)
            hoverFrame.show()
            hoverFrame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL) 
            hoverFrame.label_set("typ spoje:     ")   
       
            
       
            self.hoversel = elementary.Hoversel(self.win)
            hoversel = self.hoversel
            hoversel.hover_parent_set(self.win) # kdyz todle nedam tak to vyjizdi nahoru
            hoverFrame.content_set(hoversel)
            hoversel.show()
            hoversel.label_set("typy spoju")

            
            hoversel.label_set(self.typSpoje)
    
            for i in range(len(self.typySpoju)):
                name = self.typySpoju[i]
                hoversel.item_add(name,
                              "arrow_down",
                              elementary.ELM_ICON_STANDARD,
              #         hoverSelUpdate  )
                  partial(self.hoverselUpdate, name))
                      #===> def hoverSelUpdate (self,obj, name, typ):
                         #obj: BRNO   name XXXX     typ:callback_clicked_add

                
                   #partial(self.hoverSelUpdate, typ=name))
                #===> def hoverSelUpdate (self,obj, name, typ):
                #obj XXXX   name: callback_clicked_add    typ:BUS
        ###############################################
            self.box.pack_end(hoverFrame)

            """defaultni nastaveni tubu spoje"""
            self.hoversel.label_set(self.typSpoje)

    def fillMisto(self):
            """vytvori box pro urceni mist odkud kam"""
            ##################   MISTO ##############################################3
            
            mistoBox = elementary.Box(self.win)
            mistoBox.horizontal_set(True)
            mistoBox.size_hint_weight_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            mistoBox.show()
            
            ################  ODKUD #############################
            odkudFrame = elementary.Frame(self.win)
            odkudFrame.show()
            odkudFrame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL) 
            odkudFrame.label_set("odkud: ")  
        
            self.odkudEntry = elementary.Entry(self.win)
            odkudEntry = self.odkudEntry
            odkudEntry.single_line_set(True) #pak se nezalamuji radku

            odkudEntry.entry_set(self.database.getOdkud())    
            odkudEntry.show()  
            
            odkudFrame.content_set(odkudEntry)
            mistoBox.pack_end(odkudFrame)

            ############## PREHODIT ################
            
            prehoditBT = elementary.Button(self.win)
            prehoditBT.label_set("prehodit")
            prehoditBT.show()    
            prehoditBT.callback_clicked_add(self.prehodit)
            
            mistoBox.pack_end(prehoditBT)
        
    
            ###############  KAM #################
            kamFrame = elementary.Frame(self.win)
            kamFrame.show()
            kamFrame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL) 
            kamFrame.label_set("kam: ") 
            
            self.kamEntry = elementary.Entry(self.win)
            kamEntry = self.kamEntry
            kamEntry.single_line_set(True)
            kamEntry.entry_set(self.database.getKam())   
            kamEntry.show()      

            kamFrame.content_set(kamEntry)
            mistoBox.pack_end(kamFrame)
            
            
            
            
            ##
            self.box.pack_end(mistoBox)
    def fillCasDatum(self):        
            """vytvori box pro dastaveni datumu a casu"""
            ################### CAS DATUM FRAME#####################
            
            casDatumBox = elementary.Box(self.win)
            casDatumBox.horizontal_set(True)
            casDatumBox.size_hint_weight_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            casDatumBox.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL) 


            casDatumBox.show()
                        
            ###################  CAS ###################
            
            casFrame = elementary.Frame(self.win)
            casFrame.show()
            casFrame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL) 
            casFrame.size_hint_weight_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)

            casFrame.label_set("Cas: ") 
            
            casBox = elementary.Box(self.win)
            casBox.horizontal_set(True)
            casBox.size_hint_weight_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            casBox.show()
                    
            self.hodinaEntry = elementary.Entry(self.win)
            hodinaEntry = self.hodinaEntry
            hodinaEntry.single_line_set(True)
            hodinaEntry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            hodinaEntry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            hodinaEntry.show()  
            
            label = elementary.Label(self.win)
            label.label_set(":")
            label.size_hint_align_set(0.0, - 1.0)

            label.show() 
            
            self.minutaEntry =  elementary.Entry(self.win)
            minutaEntry = self.minutaEntry
            minutaEntry.single_line_set(True)
            minutaEntry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            minutaEntry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            minutaEntry.show()  
              
          
             
            casBox.pack_end(hodinaEntry)
            casBox.pack_end(label)
            casBox.pack_end(minutaEntry)
            
            
            casFrame.content_set(casBox)
          
                
            ########       DATUM     ########
            datumFrame = elementary.Frame(self.win)
            datumFrame.show()
            datumFrame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL) 
            datumFrame.label_set("Datum: ") 
            
            
            datumBox = elementary.Box(self.win)
            datumBox.horizontal_set(True)
            datumBox.size_hint_weight_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            datumBox.show()
                    
            self.denEntry = elementary.Entry(self.win)
            denEntry = self.denEntry
            denEntry.single_line_set(True)
            denEntry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            denEntry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            denEntry.show()  
            
            label = elementary.Label(self.win)
            label.label_set(".")
            label.size_hint_align_set(0.0, - 1.0)

            label.show()  
            
            self.mesicEntry = elementary.Entry(self.win)
            mesicEntry = self.mesicEntry
            mesicEntry.single_line_set(True)
            mesicEntry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            mesicEntry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            mesicEntry.show()  
              
   
             
            datumBox.pack_end(denEntry)
            datumBox.pack_end(label)
            datumBox.pack_end(mesicEntry)
              
      
          
            datumFrame.content_set(datumBox)
            casDatumBox.pack_end(casFrame)
            casDatumBox.pack_end(datumFrame)
    
            self.box.pack_end(casDatumBox)
    
    def fillNastaveni(self):        
            """nastaveni poctu prestupu ve spoji a poctu zobrazenych(vlastne vyhledanych) spoju"""
            
            nastavaniFrame = elementary.Frame(self.win)
            nastavaniFrame.show()
            nastavaniFrame.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL) 
            nastavaniFrame.label_set("Maximum ") 
            #######
            nastaveniBox = elementary.Box(self.win)
            nastaveniBox.horizontal_set(True)
            nastaveniBox.size_hint_weight_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            nastaveniBox.show()
            
            nastavaniFrame.content_set(nastaveniBox)

            prestupyLabel = elementary.Label(self.win)
            prestupyLabel.label_set("Prestupu:")
            prestupyLabel.size_hint_align_set(0.0, - 1.0)

            prestupyLabel.show()
            
            
            nastaveniBox.pack_end(prestupyLabel)
            
            self.prestupyEntry = elementary.Entry(self.win)
            prestupyEntry = self.prestupyEntry
            prestupyEntry.single_line_set(True)
            prestupyEntry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            prestupyEntry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            prestupyEntry.show()  
            prestupyEntry.entry_set(str(self.database.getPrestupu()))
            
#            frame = self.elementary.Frame(self.win)
#            frame.show() 
#            frame.style_set("outdent_top")
#            frame.content_set(prestupyEntry)
            
            nastaveniBox.pack_end(prestupyEntry)
            
            spojeLabel = elementary.Label(self.win)
            spojeLabel.label_set("     Spoju:")
            spojeLabel.size_hint_align_set(0.0, - 1.0)

            spojeLabel.show()
            
            nastaveniBox.pack_end(spojeLabel)
            
            self.spojeEntry = elementary.Entry(self.win)
            spojeEntry = self.spojeEntry
            spojeEntry.single_line_set(True)
            spojeEntry.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            spojeEntry.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            spojeEntry.show()  
            spojeEntry.entry_set(str(self.database.getSpoju()))
            
#            frame = self.elementary.Frame(self.win)
#            frame.show() 
#            frame.style_set("outdent_top")
#            frame.content_set(spojeEntry)
            
            nastaveniBox.pack_end(spojeEntry)
            
            
            self.box.pack_end(nastavaniFrame)


    def fillPoznamka(self):
            """ vytvori check(box) pro zobrazeni/nezobrazeni poznamky"""
            poznamkaBox = elementary.Box(self.win)
            poznamkaBox.horizontal_set(True)
            poznamkaBox.size_hint_weight_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            poznamkaBox.show()
            
            self.box.pack_end(poznamkaBox)
            
            poznamkaLabel = elementary.Label(self.win)
            poznamkaLabel.label_set("zobrazit poznamku")
            poznamkaLabel.show()
            
            poznamkaBox.pack_end(poznamkaLabel)
            
            
            
            self.poznamkaCheck = elementary.Check(self.win)
            poznamkaCheck = self.poznamkaCheck 
            poznamkaCheck.show()

            poznamkaCheck.state_set(self.database.getPoznamka())
            
            poznamkaBox.pack_end(poznamkaCheck)
            
        
            
    
    def fillTlacitka(self):
            """ vytvori tlacitka search a exit"""
            searchBT = elementary.Button(self.win)
            searchBT.label_set("search")
            searchBT.show()      
            searchBT.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            searchBT.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            searchBT.callback_clicked_add(self.search)
        
    
        
#            exitBT = self.elementary.Button(self.win)
#            exitBT.label_set("exit")
#            exitBT.show()       
#            exitBT.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
#            exitBT.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
#            exitBT.callback_clicked_add(self.destroy)

            configBT = elementary.Button(self.win)
            configBT.label_set("save config")
            configBT.show()       
            configBT.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            configBT.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            configBT.callback_clicked_add(self.saveConfig)
        
            showSavedBT = elementary.Button(self.win)
            showSavedBT.label_set("show old ")
            showSavedBT.show()       
            showSavedBT.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)  
            showSavedBT.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
            showSavedBT.callback_clicked_add(self.showSaved)
                    
        
            self.box.pack_end(searchBT)
            self.box.pack_end(showSavedBT)
#            self.box.pack_end(exitBT)
            self.box.pack_end(configBT)
          
          
            
    def __init__(self):
#            print spoje.KODOVANI_SYSTEM
            self.database = database()
            self.idos = spoje.IDOS()
            

#            odkudText = "Jablonec" 
#            kamText = "Praha"

                        
            self.typySpoju = spoje.IDOS().TYPY_SPOJU
#            self.typSpoje = self.typySpoju[0]
            self.typSpoje = self.database.getTyp()
            elementary.init() 
            
            self.win = elementary.Window("spoje-gui", elementary.ELM_WIN_BASIC)
            self.win.title_set("Spoje GUI")
            #win.autodel_set(True) ## window manageru uvoznuje zavreni okna, ale skript porad bezi dal    
            self.win.callback_destroy_add(self.destroy)  
            ##window manageru umozni zavreni  programu
              
            
            bg = elementary.Background(self.win)
            self.win.resize_object_add(bg)
            bg.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
            bg.show()
 

        ##################  SCROLOVANI #################
        
            self.pager = elementary.Pager(self.win)
            self.pager.show()
        
            scroller = elementary.Scroller(self.win)
            scroller.show()
            scroller.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
            scroller.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
           

            self.win.resize_object_add(self.pager)
            
            self.pageMain=scroller


            self.box = elementary.Box(self.win)
            self.box.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
            self.box.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)       
            self.box.show()
            
            scroller.content_set(self.box)

                    
            ########## VYPLNENI OKNA POLOZKAMI
            self.fillTypSpoje()
            self.fillMisto()
            self.fillCasDatum()
            self.fillTlacitka()
            self.fillPoznamka()
            self.fillNastaveni()   
            ################### showData      ################
            #musi bej na konci aby se zobrazovalo navrchu
            self.showData=showData(self.win,self.pageMain,self.pager);
            self.pager.content_push(self.showData)

            ######
            self.pager.content_push( self.pageMain)
            ########### ZAVERECNE ZOBRAZENI
            self.win.show() 
    
            elementary.run()
            elementary.shutdown()
            
if __name__ == "__main__":
    print "spoustim se "
    

    print version
    SpojeGUI()
    
#    database=database()
#    print database.getOdkud()

    
            

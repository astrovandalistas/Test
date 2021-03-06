# -*- coding: utf-8 -*-

import sys, time, subprocess, getopt
from Queue import Queue
from random import random, uniform
sys.path.append("../LocalNet")
from interfaces import PrototypeInterface, runPrototype
import langid
from nltk import UnigramTagger, BigramTagger
from cPickle import dump, load

FESTIVAL_ES = "voice_cstr_upc_upm_spanish_hts"
FESTIVAL_EN = "voice_kal_diphone"
FESTIVALBIN = "./festival"
FESTIVALCMD = "echo \"(LANG) (SayText \\\"XXXXX\\\")\" | "

class ISO(PrototypeInterface):
    """ ISO prototype class
        all prototypes must define setup() and loop() functions
        self.messageQ will have all messages coming in from LocalNet """
    def setup(self):
        ## subscribe to all receivers
        self.subscribeToAll()
        """
        ## or pick which ones
        for k in self.allReceivers.keys():
            self.subscribeTo(k)
        ## or subscribe to osc
            self.subscribeTo('osc')
        """
        ## some variables
        self.queueDelay = 1
        self.lastQueueCheck = time.time()

        ## turn up the volume
        subprocess.call("amixer set PCM -- -100", shell=True)

        ## for language identification
        langid.set_languages(['en','es'])

        ## for tagging
        input = open('uniTag.en.pkl', 'rb')
        self.enTagger = load(input)
        input.close()
        input = open('uniTag.es.pkl', 'rb')
        self.esTagger = load(input)
        input.close()
        self.tagDict = {}

    def loop(self):
        ## check state
        if ((not self.messageQ.empty()) and
            (time.time() - self.lastQueueCheck > self.queueDelay)):
            self.lastQueueCheck = time.time()
            (locale,type,txt) = self.messageQ.get()

            ## detect language!
            mLanguage = FESTIVAL_ES if(langid.classify(txt)[0] == 'es') else FESTIVAL_EN
            mTagger = self.esTagger if(mLanguage == FESTIVAL_ES) else self.enTagger

            ## make up a message
            madeUpMessage = txt.lower()
            txtWords = madeUpMessage.replace(",","").replace(".","").replace("?","").replace("!","").split()
            replaceCount = 0
            longishWords = 0
            for (word,tag) in mTagger.tag(txtWords):
                ## if word is worth using
                if((tag) and (len(word) > 4) and (type != "madeup")):
                    longishWords += 1
                    if(tag in self.tagDict):
                        newWord = self.tagDict[tag][int(uniform(0,len(self.tagDict[tag])))]
                        if((newWord != word) and (random() < 0.66)):
                            ##print "%s <-%s-> %s"%(word,tag,newWord)
                            madeUpMessage = madeUpMessage.replace(" "+word+" "," "+newWord+" ")
                            replaceCount += 1
                    ## tag not in dict
                    else:
                        self.tagDict[tag] = []
                        
                    ## if array is full, pop a random word
                    if(len(self.tagDict[tag]) > 9):
                        self.tagDict[tag].pop(int(uniform(0,len(self.tagDict[tag]))))
                    ## finally, put word in array
                    self.tagDict[tag].append(word)

            if((longishWords != 0) and (float(replaceCount)/float(longishWords) > 0.5)):
                print "pushing madeup message: "+madeUpMessage
                self.messageQ.put(("","madeup",madeUpMessage))

            ## then remove accents and nonAscii characters
            txt = self.removeNonAscii(self.removeAccents(txt.encode('utf-8')))
            toSay = (FESTIVALCMD+FESTIVALBIN).replace("LANG",mLanguage)
            toSay = toSay.replace("XXXXX",txt)
            subprocess.call(toSay, shell=True)

if __name__=="__main__":
    (inIp, inPort, localNetAddress, localNetPort) = ("127.0.0.1", 8989, "127.0.0.1", 8900)
    opts, args = getopt.getopt(sys.argv[1:],"i:p:n:o:",["inip=", "inport=","localnet=","localnetport="])
    for opt, arg in opts:
        if(opt in ("--inip","-i")):
            inIp = str(arg)
        elif(opt in ("--inport","-p")):
            inPort = int(arg)
        elif(opt in ("--localnet","-n")):
            localNetAddress = str(arg)
        elif(opt in ("--localnetport","-o")):
            localNetPort = int(arg)

    mM = ISO(inIp, inPort, localNetAddress, localNetPort)
    runPrototype(mM)

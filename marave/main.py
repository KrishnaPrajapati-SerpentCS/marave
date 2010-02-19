#-*- coding: utf-8 -*-


"""The user interface for our app"""

# Marave, a relaxing text editor.
# Copyright (C) 2010 Roberto Alsina <ralsina@netmanagers.com.ar>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os, sys, codecs, re, optparse

if hasattr(sys, 'frozen'):
    PATH = os.path.abspath(os.path.dirname(sys.executable))
else:
    PATH = os.path.abspath(os.path.dirname(__file__))

# Import Qt modules
from PyQt4 import QtCore, QtGui, QtSvg

# Try to import Phonon from PyQt or PyKDE
SOUND=False
try:
    from PyQt4.phonon import Phonon
    SOUND=True
except ImportError:
    try:
        from PyKDE4.phonon import Phonon
        SOUND=True
    except ImportError:
        pass

from plugins.plugins import Plugin

# Syntax highlight support
try:
    from highlight.SyntaxHighlighter import srchiliteqt
except ImportError:
    srchiliteqt = None

from spelltextedit import SpellTextEdit

from Ui_searchwidget import Ui_Form as UI_SearchWidget
from Ui_searchreplacewidget import Ui_Form as UI_SearchReplaceWidget
from Ui_searchreplacewidget import Ui_Form as UI_SearchReplaceWidget
from Ui_prefs import Ui_Form as UI_Prefs

class animatedOpacity:
    step = .1
    def moveOpacity(self):
        if abs(abs(self.proxy.opacity())-abs(self.targetOpacity))<.1:
            self.proxy.setOpacity(self.targetOpacity)
            if self.targetOpacity==0:
                self.hide()
            self.movingOp=False
        else:
            self.show()
            self.movingOp=True
            if self.proxy.opacity()<self.targetOpacity:
                self.proxy.setOpacity(self.proxy.opacity()+self.step)
            else:
                self.proxy.setOpacity(self.proxy.opacity()-self.step)
            QtCore.QTimer.singleShot(10,self.moveOpacity)

    def showChildren(self):
        for c in self.children:
            c.targetOpacity=.8
            c.moveOpacity()

    def hideChildren(self):
        for c in self.children:
            c.targetOpacity=0.
            c.moveOpacity()

class Handle(QtGui.QGraphicsRectItem, animatedOpacity):
    def __init__(self,x,y,w,h):
        QtGui.QGraphicsRectItem.__init__(self,x,y,w,h)
        self.setBrush(QtGui.QColor(100,100,100,80))
        self.setPen(QtGui.QColor(0,0,0,0))
        self.targetOpacity=0
        self.proxy=self
        self.children=[]

class PrefsWidget(QtGui.QWidget, animatedOpacity):
    def __init__(self, scene, opacity=0, mainwindow=None):
        QtGui.QWidget.__init__(self)
        # Set up the UI from designer
        self.mainwindow=mainwindow
        self.ui=UI_Prefs()
        self.baseOpacity=opacity
        self.proxy=scene.addWidget(self)
        self.proxy.setOpacity(opacity)
        self.movingOp=False
        self.children=[]
        self.ui.setupUi(self)
        self.loadthemelist()
        self.loadstylelist()
        self.loadSpellcheckers()
        self.loadLexers()
        self.loadPlugins()
        self.proxy.setZValue(100)
        self.proxy.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)

    def loadPlugins(self):
        Plugin.initPlugins()
        classes = Plugin.listPlugins()
        enabled = self.mainwindow.settings.value('enabledplugins')
        if enabled.isValid():
            enabled=unicode(enabled.toString()).split(',')
        else:
            enabled=[]
        for p in classes:
            sel=p.selectorWidget()
            if p.name in enabled:
                sel.check.setChecked(True)
            f=lambda b: self.enablePlugin(p,b)
            c=lambda: self.showPluginConf(p)
            sel.check.toggled.connect(f)
            sel.conf.clicked.connect(c)
            self.ui.pluginLayout.addWidget(sel)

    def showPluginConf(self, pluginClass):
        pluginClass.showConfig(self.mainwindow)

    def enablePlugin(self, pluginClass, enabled=None):
        if enabled is None: return
        enabledPlugins = self.mainwindow.settings.value('enabledplugins')
        if enabledPlugins.isValid():
            enabledPlugins=unicode(enabledPlugins.toString()).split(',')
        else:
            enabledPlugins=[]
        if pluginClass.name not in enabledPlugins and enabled:
            enabledPlugins.append(pluginClass.name)
        elif pluginClass.name in enabledPlugins and not enabled:
            enabledPlugins.remove(pluginClass.name)
        
        self.mainwindow.settings.setValue('enabledplugins',','.join(enabledPlugins))
        self.mainwindow.settings.sync()
        
        Plugin.instance(pluginClass, self.mainwindow)

    def loadLexers(self):
        self._l={}
        if srchiliteqt:
            self._langs=srchiliteqt.LanguageComboBox()
            self._styles=srchiliteqt.StyleComboBox()
            self.ui.syntaxList.clear()
            for i in range(self._langs.count()):
                t=unicode(self._langs.itemText(i))
                if t:
                    self.ui.syntaxList.addItem(t.split('.')[0])
                    self._l['lang-'+t.split('.')[0]]=t
            self.ui.schemeList.clear()
            for i in range(self._styles.count()):
                t=unicode(self._styles.itemText(i))
                if t:
                    self.ui.schemeList.addItem(t.split('.')[0])
                    self._l['scheme-'+t.split('.')[0]]=t

    def loadSpellcheckers(self):
        self.ui.langBox.clear()
        self.ui.langBox.addItem(self.tr('None'))
        try:
            import enchant
            for l, _ in enchant.Broker().list_dicts():
                self.ui.langBox.addItem(l)
        except ImportError:
            self.ui.langBox.setEnabled(False)
        
    def loadthemelist(self):
        self.ui.themeList.clear()
        self.ui.themeList.addItem(self.tr('Current'))
        tdir=os.path.join(PATH,'themes')
        l=os.listdir(tdir)
        l.sort()
        for t in l:
            if t.startswith('.') or t.endswith('~'):
                continue
            self.ui.themeList.addItem(t)

    def loadstylelist(self):
        self.ui.styleList.clear()
        sdir=os.path.join(PATH,'stylesheets')
        l=os.listdir(sdir)
        l.sort()
        for t in l:
            if t.startswith('.') or t.endswith('~'):
                continue
            self.ui.styleList.addItem(t)
        

class SearchWidget(QtGui.QWidget, animatedOpacity):
    def __init__(self, scene, opacity=0):
        QtGui.QWidget.__init__(self)
        # Set up the UI from designer
        self.ui=UI_SearchWidget()
        self.baseOpacity=opacity
        self.proxy=scene.addWidget(self)
        self.proxy.setOpacity(opacity)
        self.movingOp=False
        self.children=[]
        self.ui.setupUi(self)
        self.proxy.setZValue(100)
        self.proxy.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)

class MenuStrip(QtGui.QWidget, animatedOpacity):
    def __init__(self, scene, opacity = 0):
        QtGui.QWidget.__init__(self)
        # Set up the UI from designer
        self.baseOpacity=opacity
        self.proxy=scene.addWidget(self)
        self.proxy.setOpacity(opacity)
        self.movingOp=False
        self.children=[]
        self.proxy.setZValue(100)
        self.proxy.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
        self.setPos=self.proxy.setPos

class SearchReplaceWidget(QtGui.QWidget, animatedOpacity):
    def __init__(self, scene, opacity=0):
        QtGui.QWidget.__init__(self)
        # Set up the UI from designer
        self.ui=UI_SearchReplaceWidget()
        self.baseOpacity=opacity
        self.proxy=scene.addWidget(self)
        self.proxy.setOpacity(opacity)
        self.movingOp=False
        self.children=[]
        self.ui.setupUi(self)
        self.proxy.setZValue(100)


buttons=[]

class FunkyButton(QtGui.QPushButton, animatedOpacity):
    def __init__(self, icon, text, scene, opacity=.3, name=None):
        QtGui.QPushButton.__init__(self,QtGui.QIcon(os.path.join(PATH,'icons',icon)),"")
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.baseOpacity=opacity
        self.proxy=scene.addWidget(self)
        self.proxy.setOpacity(opacity)
        self.movingOp=False
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)
        self.children=[]
        self.icon=icon
        self.text=text
        if name is None:
            name=text
        self.setObjectName(name)
        buttons.append(self)
        
class FunkyFontList(QtGui.QFontComboBox, animatedOpacity):
    def __init__(self, scene,opacity=.3):
        QtGui.QFontComboBox.__init__(self)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.baseOpacity=opacity
        self.proxy=scene.addWidget(self)
        self.proxy.setOpacity(opacity)
        self.movingOp=False
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.children=[]

class FunkyStatusBar(QtGui.QStatusBar, animatedOpacity):
    def __init__(self, scene,opacity=.3):
        QtGui.QStatusBar.__init__(self)
        self.baseOpacity=opacity
        self.proxy=scene.addWidget(self)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.proxy.setOpacity(opacity)
        self.movingOp=False
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.children=[]
        self.setSizeGripEnabled(False)


class FunkyEditor(SpellTextEdit, animatedOpacity):
    def __init__(self, parent, canvaseditor=None):
        # This is for Issue 28
        
        if canvaseditor is None:
            if QtCore.QCoreApplication.instance().style().objectName() == 'oxygen' \
                and QtCore.QT_VERSION_STR < '4.6.0':
                canvaseditor = False
            else:
                canvaseditor = True
        
        if not canvaseditor:
            print 'Using non-canvas editor'
            SpellTextEdit.__init__(self, parent)
            self.setMouseTracking(True)
            self.viewport().setMouseTracking(True)
            self.defSize=self.font().pointSize()
            # This is for Issue 20
        else:
            print 'Using canvas editor'
            SpellTextEdit.__init__(self)
            self.setMouseTracking(True)
            self.viewport().setMouseTracking(True)
            self.defSize=self.font().pointSize()
            self.docName=''
            self.proxy=parent._scene.addWidget(self)
            self.proxy.setOpacity(1)
            self.movingOp=False
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.children=[]
            self.parent=lambda: parent
            self.proxy.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)

class BGItem(QtGui.QGraphicsPixmapItem, animatedOpacity):
    def __init__(self):
        QtGui.QGraphicsPixmapItem.__init__(self)
        self.targetOpacity=1
        self.setOpacity(0)
        self.proxy=self
        self.step=.2

class MainWidget (QtGui.QGraphicsView):
    def __init__(self, opengl=False, canvaseditor=None):
        QtGui.QGraphicsView.__init__(self)
        self.setWindowIcon(QtGui.QIcon(os.path.join(PATH,'icons','marave.svg')))
        self.setGeometry(QtCore.QCoreApplication.instance().desktop().screenGeometry(self))
        self._scene=QtGui.QGraphicsScene()
        self.setObjectName ("Main")
        if opengl:
            if QtCore.QCoreApplication.instance().style().objectName() == 'oxygen' \
               and QtCore.QT_VERSION_STR < '4.6.0':
                print "OpenGL acceleration doesn't work well with Oxygen, disabling it"
            else:
                try:
                    from PyQt4 import QtOpenGL
                    self.setViewport(QtOpenGL.QGLWidget())
                except ImportError:
                    print 'Qt OpenGL support not available'
        self.setScene(self._scene)
        self.settings=QtCore.QSettings('NetManagers','Marave')
        #
        self.changing=False
        self.visibleWidget=None

        # Used for margins and border sizes
        self.m=5
        
        # FIXME: self.minW should be a reasonable value based on text size 
        # or something.
        self.minW=100*self.m
        self.minH=80*self.m
        self.hasSize=False
        
        self.editor=None
        self.setMouseTracking(True)
        self.currentBG=None
        self.currentClick=None
        self.currentStation=None
        self.bgcolor=None
        self.fontcolor=None
        self.bg=None
        self.bgItem=BGItem()
        self.bgItem.setZValue(-1000)
        self._scene.addItem(self.bgItem)
        self.notifBar=FunkyStatusBar(self._scene, .7)
        self.notifBar.messageChanged.connect(self.notifChanged)
        self.beep=None
        self.music=None
        self.buttonStyle=0
        self.lang=None

        #self.mainMenu=QtGui.QGraphicsWidget()
        self.mainMenu=MenuStrip(self._scene)
        #self._scene.addItem(self.mainMenu)

        self.stations=[x.strip() for x in open(os.path.join(PATH,'radios.txt')).readlines()]

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # These are the positions for the elements of the screen
        # They are recalculated on resize
        
        self.editorX=100
        self.editorY=40
        self.editorH=400
        self.editorW=400

        self.editor=FunkyEditor(self, canvaseditor)
        self.editor.show()
        self.editor.setMouseTracking(True)
        self.editor.setFrameStyle(QtGui.QFrame.NoFrame)
        self.editor.langChanged.connect(self.editorLangChanged)
        
        # Keyboard shortcuts
        self.sc1 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+F","Find")), self);
        self.sc1.activated.connect(self.showsearch)
        self.sc1b = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+R","Find and Replace")), self);
        self.sc1b.activated.connect(self.showsearchreplace)

        # Taj mode!
        self.sc2 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+T","Taj Mode")), self);
        self.sc2.activated.connect(self.tajmode)

        ## Spell checker toggle
        #self.sc3 = QtGui.QShortcut(QtGui.QKeySequence("Shift+Ctrl+Y"), self);
        #self.sc3.activated.connect(self.togglespell)

        # Action shortcuts
        self.sc4 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+O","Open File")), self);
        self.sc4.activated.connect(self.editor.open)
        self.sc5 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+S","Save File")), self);
        self.sc5.activated.connect(self.editor.save)
        self.sc6 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Shift+Ctrl+S","Save File As")), self);
        self.sc6.activated.connect(self.editor.saveas)
        self.sc7 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+N","New File")), self);
        self.sc7.activated.connect(self.editor.new)
        self.sc8 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+Q","Quit")), self);

        # Prefs
        self.sc9 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Shift+Ctrl+P","Show Preferences")), self);
        self.sc9.activated.connect(self.showprefs)

        # Document information
        self.sc10 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("Ctrl+I","Show Document Info")), self);
        self.sc10.activated.connect(self.showinfo)

        # Help
        self.sc11 = QtGui.QShortcut(QtGui.QKeySequence(self.tr("F1","Help")), self);
        self.sc11.activated.connect(self.showhelp)

        self.editorBG=QtGui.QGraphicsRectItem()
        self.editorBG.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.editorBG.setCursor(QtCore.Qt.PointingHandCursor)
        self.editorBG.setBrush(QtGui.QColor(255,255,255))
        self.editorBG.setZValue(-999)
        self._scene.addItem(self.editorBG)

        self.handles=[]
        
        for h in range(0,4):
            h=Handle(0,0,10,10)
            h.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
            h.setCursor(QtCore.Qt.SizeAllCursor)
            h.setOpacity(.5)
            h.setZValue(100)
            self._scene.addItem(h)
            self.handles.append(h)

        self.fontButton=FunkyButton("fonts.svg", self.tr('Font'), self._scene, 0)
        self.sizeButton=FunkyButton("size.svg", self.tr('Size'), self._scene, 0)
        self.fileButton=FunkyButton("file.svg", self.tr('File'), self._scene, 0)
        self.bgButton=FunkyButton("bg.svg", self.tr('Bg'), self._scene, 0)
        if SOUND:
            self.clickButton=FunkyButton("click.svg", self.tr('Click'), self._scene, 0)
            self.musicButton=FunkyButton("music.svg", self.tr('Music'), self._scene, 0)
        self.configButton=FunkyButton("configure.svg", self.tr('Options'), self._scene, 0)
        self.configButton.clicked.connect(self.showprefs)
        self.quitButton=FunkyButton("exit.svg", self.tr('Quit'), self._scene, 0)
        self.quitButton.clicked.connect(self.close)
        self.sc8.activated.connect(self.quitButton.animateClick)

        self.buttons=[self.fontButton, 
                      self.sizeButton, 
                      self.fileButton, 
                      self.bgButton]
        if SOUND:
            self.buttons+=[self.clickButton,
                           self.musicButton]
        self.buttons+=[self.configButton,
                       self.quitButton]


        self.fontList=FunkyFontList(self._scene,0)
        self.fontList.currentFontChanged.connect(self.changefont)
        self.fontColor=FunkyButton("color.svg", self.tr('Color'), self._scene, 0,"FontColor")
        self.fontColor.clicked.connect(self.setfontcolor)
        self.fontButton.children+=[self.fontList,self.fontColor]

        self.size1=FunkyButton("minus.svg", self.tr('Smaller'), self._scene,0)
        self.size2=FunkyButton("equals.svg", self.tr('Default'), self._scene,0)
        self.size3=FunkyButton("plus.svg", self.tr('Larger'), self._scene,0)
        self.size1.clicked.connect(self.editor.smaller)
        self.size3.clicked.connect(self.editor.larger)
        self.size2.clicked.connect(self.editor.default)
        self.sizeButton.children+=[self.size1, self.size2, self.size3]


        self.file1=FunkyButton("open.svg", self.tr('Open'), self._scene, 0)
        self.file2=FunkyButton("save.svg", self.tr('Save'), self._scene, 0)
        self.file3=FunkyButton("saveas.svg", self.tr('Save As'), self._scene, 0, "SaveAs")
        self.file1.clicked.connect(self.editor.open)
        self.file2.clicked.connect(self.editor.save)
        self.file3.clicked.connect(self.editor.saveas)
        self.fileButton.children+=[self.file1, self.file2, self.file3]

        self.bg1=FunkyButton("previous.svg", self.tr('Previous'), self._scene,0,"PreviousBG")
        self.bg2=FunkyButton("next.svg", self.tr('Next'), self._scene,0, "NextBG")
        self.bg3=FunkyButton("color.svg", self.tr('Color'), self._scene,0, "ColorBG")
        self.bg1.clicked.connect(self.prevbg)
        self.bg2.clicked.connect(self.nextbg)
        self.bg3.clicked.connect(self.setbgcolor)
        self.bgButton.children+=[self.bg1, self.bg2, self.bg3]

        if SOUND:
            self.click1=FunkyButton("previous.svg", self.tr('Previous'), self._scene,0, "PreviousClick")
            self.click2=FunkyButton("next.svg", self.tr('Next'), self._scene,0, "NextClick")
            self.click3=FunkyButton("mute.svg", self.tr('None'), self._scene,0, "NoCLick")
            self.click1.clicked.connect(self.prevclick)
            self.click2.clicked.connect(self.nextclick)
            self.click3.clicked.connect(self.noclick)
            self.clickButton.children+=[self.click1, self.click2, self.click3]
        
            self.music1=FunkyButton("previous.svg", self.tr('Previous'), self._scene,0,"PreviousMusic")
            self.music2=FunkyButton("next.svg", self.tr('Next'), self._scene,0,"NextMusic")
            self.music3=FunkyButton("mute.svg", self.tr('None'), self._scene,0,"NoMusic")
            self.music1.clicked.connect(self.prevstation)
            self.music2.clicked.connect(self.nextstation)
            self.music3.clicked.connect(self.nostation)
            self.musicButton.children+=[self.music1, self.music2, self.music3]


        # Prefs widget
        self.prefsWidget=PrefsWidget(self._scene,mainwindow=self)
        self.prefsWidget.ui.close.clicked.connect(self.hidewidgets)
        self.prefsWidget.ui.saveTheme.clicked.connect(self.savetheme)
        self.prefsWidget.ui.themeList.currentIndexChanged.connect(self.loadtheme)
        self.prefsWidget.ui.styleList.currentIndexChanged.connect(self.loadstyle)
        self.prefsWidget.ui.buttonStyle.currentIndexChanged.connect(self.buttonstyle)
        self.prefsWidget.ui.langBox.currentIndexChanged.connect(self.setHL)
        self.prefsWidget.ui.opacity.valueChanged.connect(self.editoropacity)
        self.prefsWidget.ui.buttonStyle.setCurrentIndex(self.settings.value('buttonstyle').toInt()[0])
        self.prefsWidget.ui.autoSave.valueChanged.connect(self.setsavetimer)
        self.prefsWidget.ui.syntaxList.currentIndexChanged.connect(self.setHL)
        self.prefsWidget.ui.schemeList.currentIndexChanged.connect(self.setHL)
        self.prefsWidget.ui.syntax.toggled.connect(self.setHL)
        self.prefsWidget.ui.spelling.toggled.connect(self.setHL)
        self.saveTimer=QtCore.QTimer()
        self.saveTimer.timeout.connect(self.savebytimer)
        self.prefsWidget.ui.autoSave.setValue(self.settings.value('autosave').toInt()[0])
        
        prefsLayout=QtGui.QGraphicsLinearLayout()
        prefsLayout.setContentsMargins(0,0,0,0)
        prefsLayout.addItem(self.prefsWidget.proxy)
        
        self.prefsBar=QtGui.QGraphicsWidget()
        self.prefsBar.setLayout(prefsLayout)
        self._scene.addItem(self.prefsBar)


        # Search widget
        self.searchWidget=SearchWidget(self._scene)
        self.searchWidget.ui.close.clicked.connect(self.hidewidgets)
        self.searchWidget.ui.next.clicked.connect(self.doFind)
        self.searchWidget.ui.previous.clicked.connect(self.doFindBackwards)
        
        searchLayout=QtGui.QGraphicsLinearLayout()
        searchLayout.setContentsMargins(0,0,0,0)
        searchLayout.addItem(self.searchWidget.proxy)
        
        self.searchBar=QtGui.QGraphicsWidget()
        self.searchBar.setLayout(searchLayout)
        self._scene.addItem(self.searchBar)

        # Search and replace widget
        self.searchReplaceWidget=SearchReplaceWidget(self._scene)
        self.searchReplaceWidget.ui.close.clicked.connect(self.hidewidgets)
        self.searchReplaceWidget.ui.next.clicked.connect(self.doFindR)
        self.searchReplaceWidget.ui.previous.clicked.connect(self.doFindRBackwards)
        self.searchReplaceWidget.ui.replace.clicked.connect(self.doReplace)
        self.searchReplaceWidget.ui.replaceall.clicked.connect(self.doReplaceAll)
        
        searchReplaceLayout=QtGui.QGraphicsLinearLayout()
        searchReplaceLayout.setContentsMargins(0,0,0,0)
        searchReplaceLayout.addItem(self.searchReplaceWidget.proxy)
        
        self.searchReplaceBar=QtGui.QGraphicsWidget()
        self.searchReplaceBar.setLayout(searchReplaceLayout)
        self._scene.addItem(self.searchReplaceBar)

    def editorLangChanged(self, lang):
        lang=unicode(lang).split('.')[0]
        idx=self.prefsWidget.ui.syntaxList.findText(lang)
        self.prefsWidget.ui.syntax.setChecked(True)
        self.prefsWidget.ui.syntaxList.currentIndexChanged.disconnect(self.setHL)
        self.prefsWidget.ui.syntaxList.setCurrentIndex(idx)
        self.prefsWidget.ui.syntaxList.currentIndexChanged.connect(self.setHL)

    def setHL(self, idx):
        # Ignore args, take the data from prefsWidget
        if self.prefsWidget.ui.spelling.isChecked():
            # Enable spellchecking
            l=unicode(self.prefsWidget.ui.langBox.currentText())
            self.setspellchecker(l)
            self.settings.setValue('lang',l)
        elif srchiliteqt:
            # Enable syntax highlighting
            l=self.prefsWidget._l
            lang='lang-'+unicode(self.prefsWidget.ui.syntaxList.currentText())
            scheme='scheme-'+unicode(self.prefsWidget.ui.schemeList.currentText())
            self.settings.setValue('scheme', self.prefsWidget.ui.schemeList.currentText())
            self.editor.setHL(l[lang], l[scheme])
            self.settings.setValue('lang',QtCore.QVariant())
        self.settings.sync()

    def setsavetimer(self, value=None):
        if value is None:
            return
        self.settings.setValue('autosave', value)
        self.settings.sync()
        if value:
            self.notify(self.tr('Saving every %n minutes','',value))
            self.saveTimer.setInterval(60*1000*value)
            self.saveTimer.start()
        else:
            self.notify(self.tr('Disabled automatic saving'))
            self.saveTimer.stop()

    def savebytimer(self):
        try:
            if self.editor.docName: # No autosaving UNNAMED
                self.editor.save()
        except:
            pass
        self.setsavetimer()

    def warnnosound(self):
        self.notify(unicode(self.tr('Sound support is not available, disabling sound')))

    def showhelp(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl('file://'+PATH+'/README.html'))

    def showinfo(self):
        txt=unicode(self.editor.toPlainText())
        lc=len(txt.splitlines())
        wc=len(re.split('[\n\t ]',txt))
        name=os.path.basename(self.editor.docName) or "UNNAMED"
        s1=unicode(self.tr('Document: %s'))%name
        s2=unicode(self.tr('%n words','',wc))
        s3=unicode(self.tr('%n lines','',lc))
        s4=unicode(self.tr('%n characters','',len(txt)))
        
        self.notify(s1+u' -- '+s2+u' -- '+s3+u' -- '+s4)

    def notifChanged(self, msg):
        if unicode(msg):
            self.notifBar.targetOpacity=.7
        else:
            self.notifBar.targetOpacity=.0
        self.notifBar.moveOpacity()

    def notify(self, text):
        self.notifBar.showMessage(text, 3000)
        self.notifBar.proxy.setPos(self.editorX, self.editorY+self.editorH+self.m)

    def layoutButtons(self):
        mainMenuLayout=QtGui.QGraphicsGridLayout()
        mainMenuLayout.setContentsMargins(0,0,0,0)
        for pos, button in enumerate(self.buttons):
            mainMenuLayout.addItem(button.proxy,pos,0)
        mainMenuLayout.setRowSpacing(len(self.buttons)-2,self.m*2)
        mainMenuLayout.addItem(self.fontList.proxy,0,2,1,2)
        mainMenuLayout.addItem(self.fontColor.proxy,0,1)
        mainMenuLayout.addItem(self.size1.proxy,1,1)
        mainMenuLayout.addItem(self.size2.proxy,1,2)
        mainMenuLayout.addItem(self.size3.proxy,1,3)
        mainMenuLayout.addItem(self.file1.proxy,2,1)
        mainMenuLayout.addItem(self.file2.proxy,2,2)
        mainMenuLayout.addItem(self.file3.proxy,2,3)
        mainMenuLayout.addItem(self.bg1.proxy,3,1)
        mainMenuLayout.addItem(self.bg2.proxy,3,2)
        mainMenuLayout.addItem(self.bg3.proxy,3,3)
        if SOUND:
            mainMenuLayout.addItem(self.click1.proxy,4,1)
            mainMenuLayout.addItem(self.click2.proxy,4,2)
            mainMenuLayout.addItem(self.click3.proxy,4,3)
            mainMenuLayout.addItem(self.music1.proxy,5,1)
            mainMenuLayout.addItem(self.music2.proxy,5,2)
            mainMenuLayout.addItem(self.music3.proxy,5,3)

        self.mainMenu=QtGui.QGraphicsWidget()
        self._scene.addItem(self.mainMenu)
        self.mainMenu.setLayout(mainMenuLayout)
        self.mainMenu.setPos(self.editorX+self.editorW+20,self.editorY)

    def editoropacity(self, v):
        self.notify(unicode(self.tr("Setting opacity to: %s%%"))%v)
        self.editorBG.setOpacity(v/100.)
        self.settings.setValue("editoropacity",v)
        self.settings.sync()

    def buttonstyle(self, idx):
        self.buttonStyle=idx
        self.settings.setValue('buttonstyle',self.buttonStyle)
        self.settings.sync()
        for b in buttons:
            if idx==0:
                b.setIcon(QtGui.QIcon(os.path.join(PATH,'icons',b.icon)))
                b.setText("")
                b.adjustSize()
            elif idx==1:
                b.setIcon(QtGui.QIcon())
                b.setText(b.text)
                b.adjustSize()
            elif idx==2:
                b.setIcon(QtGui.QIcon(os.path.join(PATH,'icons',b.icon)))
                b.setText(b.text)
                b.adjustSize()
        self.layoutButtons()

    def loadstyle(self, styleidx):
        stylename=unicode(self.prefsWidget.ui.styleList.itemText(styleidx))
        stylefile=os.path.join(PATH,'stylesheets',stylename)
        self.notify (unicode(self.tr('Changing to style %s requires restarting Marave'))%stylename)
        self.settings.setValue('style',stylename)
        self.settings.sync()
        
    def loadtheme(self, themeidx):
        if not themeidx:
            return
        themename=unicode(self.prefsWidget.ui.themeList.itemText(themeidx))
        themefile=os.path.join(PATH,'themes',themename)
        self.oldSettings=self.settings
        self.settings=QtCore.QSettings(themefile,QtCore.QSettings.IniFormat)
        #self.loadprefs()
        self.loadBG()
        self.loadOpacity()
        self.loadFont()
        self.settings=self.oldSettings
        self.saveprefs()
        
    def savetheme(self, themefile=None):
        #from pudb import set_trace; set_trace()
        try:
            self.prefsWidget.ui.themeList.currentIndexChanged.disconnect()
        except TypeError:
            pass
        if themefile is None or themefile is False:
            tdir=os.path.join(PATH,'themes')
            self.savetheme(unicode(QtGui.QFileDialog.getSaveFileName(self.parent(), "Marave - Save Theme",tdir)))
            return
        self.oldSettings=self.settings
        self.settings=QtCore.QSettings(QtCore.QString(themefile),QtCore.QSettings.IniFormat)
        self.saveprefs()
        # Don't save the size and position of the editor in the theme
        self.settings.remove('x')
        self.settings.remove('y')
        self.settings.remove('w')
        self.settings.remove('h')
        self.settings.sync()
        
        self.settings=self.oldSettings
        self.prefsWidget.loadthemelist()
        self.prefsWidget.ui.themeList.currentIndexChanged.connect(self.loadtheme)

    def saveprefs(self):
        # Save all settings at once
        self.settings.setValue('font',self.editor.font())
        self.settings.setValue('fontsize',self.editor.font().pointSize())
        if self.currentClick:
            self.settings.setValue('click',self.currentClick)
        else:
            self.settings.setValue('click',QtCore.QVariant())
        if self.currentStation:
            self.settings.setValue('station',self.currentStation)
        else:
            self.settings.setValue('station',QtCore.QVariant())
        if self.bgcolor:
            self.settings.setValue('bgcolor',self.bgcolor.name())
            self.settings.setValue('background',QtCore.QVariant())
        else:
            self.settings.setValue('bgcolor',QtCore.QVariant())
            self.settings.setValue('background',self.currentBG)
            
        if self.fontcolor:
            self.settings.setValue('fontcolor',self.fontcolor.name())

        self.saveEditorGeometry()
        self.settings.setValue('buttonstyle',self.buttonStyle)
        self.settings.setValue('editoropacity', self.editorBG.opacity()*100)
        self.settings.setValue('autosave', self.prefsWidget.ui.autoSave.value())

        self.settings.sync()

    def saveEditorGeometry(self):
        if self.hasSize:
            self.settings.setValue('x',int(self.editorX))
            self.settings.setValue('y',int(self.editorY))
            self.settings.setValue('w',int(self.editorW))
            self.settings.setValue('h',int(self.editorH))
            self.settings.sync()

    def loadBG(self):
        "Load background from the preferences"
        
        bgcolor=self.settings.value('bgcolor')
        bg=self.settings.value('background')
        if not bg.isValid() and not bgcolor.isValid():
            # Probably first run
            self.nextbg()        
        elif bg.isValid():
            self.setbg(unicode(bg.toString()))
        elif bgcolor.isValid():
            self.setbgcolor(QtGui.QColor(bgcolor.toString()))

    def loadSound(self):
        "Load sound settings from config file"
        c=self.settings.value('click')
        if c.isValid():
            self.setclick(unicode(c.toString()))
        else:
            self.noclick()
        
        s=self.settings.value('station')
        if s.isValid():
            self.setstation(unicode(s.toString()))
        else:
            self.nostation()

    def loadGeometry(self):
        x=self.settings.value('x')
        y=self.settings.value('y')
        w=self.settings.value('w')
        h=self.settings.value('h')
        if x.isValid() and y.isValid() and w.isValid() and h.isValid():
            self.hasSize=True
            self.editorX=x.toInt()[0]
            self.editorY=y.toInt()[0]
            self.editorW=max(w.toInt()[0], self.minW)
            self.editorH=max(h.toInt()[0], self.minH)
        self.adjustPositions()

    def loadFont(self):
        f=QtGui.QFont()
        fname=self.settings.value('font')
        if fname.isValid():
            f.fromString(fname.toString())
            print 'Loaded font:',f.family()
        else:
            f.setFamily('courier')
        fs,ok=self.settings.value('fontsize').toInt()
        if ok:
            f.setPointSize(fs)
        self.editor.setFont(f)
        self.fontList.setCurrentFont(f)
        fontcolor=self.settings.value('fontcolor')
        if fontcolor.isValid():
            self.setfontcolor(QtGui.QColor(fontcolor.toString()))
        else:
            self.setfontcolor(QtGui.QColor('black'))

    def loadOpacity(self):
        o,ok=self.settings.value('editoropacity').toInt()
        if ok:
            self.editorBG.setOpacity(o/100.)
        else:
            self.editorBG.setOpacity(.03)

    def loadprefs(self):
        # Load all settings

        if len(self.settings.allKeys()) == 0:
            # First run
            self.loadtheme(1)
            
        self.loadGeometry()
        self.loadFont()
        self.loadOpacity()
        
        bs,ok=self.settings.value('buttonstyle').toInt()
        if ok:
            self.buttonStyle=bs
        else:
            self.buttonStyle=0
        self.buttonstyle(self.buttonStyle)
        
        self.loadBG()
        
        l=self.settings.value('lang')
        if l.isValid():
            self.setspellchecker(unicode(l.toString()))
        else:
            self.setspellchecker('None')
            
        style=self.settings.value('style')
        if style.isValid():
            style=unicode(style.toString())
        else:
            style='default'
        print 'Loading style:',style
        self.prefsWidget.ui.styleList.setCurrentIndex(self.prefsWidget.ui.styleList.findText(style))
        QtCore.QCoreApplication.instance().setStyleSheet(open(os.path.join(PATH,'stylesheets',style)).read())
        
        # Color scheme for syntax highlighter
        scheme=self.settings.value('scheme')
        if scheme.isValid():
            scheme=unicode(scheme.toString())
        else:
            scheme='default'
        self.prefsWidget.ui.schemeList.setCurrentIndex(self.prefsWidget.ui.schemeList.findText(scheme))        
        QtCore.QTimer.singleShot(10,self.loadSound)

    def setspellchecker(self, code):
        if isinstance (code, int):
            code=unicode(self.prefsWidget.ui.langBox.itemText(code))
        if "dict" not in self.editor.__dict__:
            # No pyenchant
            return
        if code == 'None':
            self.lang=None
            self.editor.killDict()
            self.prefsWidget.ui.langBox.setCurrentIndex(0)
        else:
            self.lang=code
            self.editor.initDict(self.lang)
            self.prefsWidget.ui.langBox.setCurrentIndex(self.prefsWidget.ui.langBox.findText(self.lang))
        if self.prefsWidget.ui.spelling.isChecked():
            self.settings.setValue('lang',self.lang)
        else:
            self.settings.setValue('lang',QtCore.QVariant())
        self.settings.sync()
        

    def close(self):
        QtCore.QCoreApplication.instance().setOverrideCursor(QtCore.Qt.ArrowCursor)
        if self.editor.document().isModified():
            r=QtGui.QMessageBox.question(self, self.tr("Close Document - Marave"), 
                unicode(self.tr("The document \"%s\" has been modified."))%(self.editor.docName or self.tr("UNNAMED"))+
                self.tr("\nDo you want to save your changes or discard them?"),
                QtGui.QMessageBox.Save|QtGui.QMessageBox.Discard|QtGui.QMessageBox.Cancel,QtGui.QMessageBox.Cancel)
            if r==QtGui.QMessageBox.Save:
                self.editor.save()
            elif r==QtGui.QMessageBox.Discard:
                self.saveprefs()
                QtGui.QGraphicsView.close(self)
                QtCore.QCoreApplication.instance().quit()
        else:
            self.saveprefs()
            QtGui.QGraphicsView.close(self)
            QtCore.QCoreApplication.instance().quit()
        QtCore.QCoreApplication.instance().restoreOverrideCursor()

    def showbar(self, w):
        self.hidewidgets()
        self.visibleWidget=w
        w.show()
        self.editor.resize(self.editorW, self.editorH-w.height())
        self.setFocus()
        w.targetOpacity=.9
        w.moveOpacity()

    def showsearchreplace(self):
        self.showbar(self.searchReplaceWidget)
        self.searchReplaceWidget.ui.text.setFocus()

    def showsearch(self):
        self.showbar(self.searchWidget)
        self.searchWidget.ui.text.setFocus()

    def showprefs(self):
        self.prefsWidget.ui.opacity.setValue(self.editorBG.opacity()*100)
        self.showbar(self.prefsWidget)


    def hidewidgets(self):
        for w in [self.searchWidget, self.searchReplaceWidget, self.prefsWidget]:            
            w.targetOpacity=.0
            w.moveOpacity()
            #w.hide()
        self.editor.setFocus()
        self.visibleWidget=None
        #self.editor.resize(self.editorW,self.editorH)

    def doReplaceAllBackwards(self):
        # Backwards and forwards are exactly the
        # same thing if we are replacing all!
        self.doReplaceAll(backwards=True)

    def doReplaceAll(self):
        # Replace all occurences without interaction
        
        old=self.searchReplaceWidget.ui.text.text()
        new=self.searchReplaceWidget.ui.replaceWith.text()

        # Beginning of undo block
        cursor=self.editor.textCursor()
        cursor.beginEditBlock()
        
        # Use flags for case match
        flags=QtGui.QTextDocument.FindFlags()
        if self.searchReplaceWidget.ui.matchCase.isChecked():
            flags=flags|QtGui.QTextDocument.FindCaseSensitively
            
        # Replace all we can
        while True:
            r=self.editor.find(old,flags)
            if r:
                qc=self.editor.textCursor()
                if qc.hasSelection():
                    qc.insertText(new)
            else:
                break
                
        # Mark end of undo block
        cursor.endEditBlock()

    def doReplaceBackwards (self):
        return self.doReplace(backwards=True)
        
    def doReplace(self):
        qc=self.editor.textCursor()
        if qc.hasSelection():
            qc.insertText(self.searchReplaceWidget.ui.replaceWith.text())
        self.doFindR(self.searchReplaceWidget.backwards)
            
    def doFindRBackwards (self):
        return self.doFindR(backwards=True)

    def doFindR(self, backwards=False):
        self.searchReplaceWidget.backwards=backwards
        flags=QtGui.QTextDocument.FindFlags()
        if backwards:
            flags=QtGui.QTextDocument.FindBackward
        if self.searchReplaceWidget.ui.matchCase.isChecked():
            flags=flags|QtGui.QTextDocument.FindCaseSensitively

        text=unicode(self.searchReplaceWidget.ui.text.text())
        r=self.editor.find(text,flags)

    def doFindBackwards (self):
        return self.doFind(backwards=True)

    def doFind(self, backwards=False):
        flags=QtGui.QTextDocument.FindFlags()
        if backwards:
            flags=QtGui.QTextDocument.FindBackward
        if self.searchWidget.ui.matchCase.isChecked():
            flags=flags|QtGui.QTextDocument.FindCaseSensitively

        text=unicode(self.searchWidget.ui.text.text())
        r=self.editor.find(text,flags)

    def rewind(self):
        if self.beep:
            self.beep.seek(0)

    def setclick(self, clickname):
        if not SOUND: return
        self.currentClick=clickname
        self.notify(unicode(self.tr('Switching click to: %s'))%self.currentClick)
        self.beep = Phonon.createPlayer(Phonon.NotificationCategory,
                                  Phonon.MediaSource(os.path.join(PATH,'clicks',self.currentClick)))
        self.beep.finished.connect( self.rewind )
        self.beep.play()
        self.settings.setValue('click',self.currentClick)
        self.settings.sync()

    def prevclick(self):
        clist=os.listdir(os.path.join(PATH,'clicks'))
        clist=[x for x in clist if not x.startswith('.')]
        clist.sort()
        try:
            idx=(clist.index(self.currentClick)-1)%len(clist)
        except ValueError:
            idx=-1
        self.setclick(clist[idx])

    def nextclick(self):
        clist=os.listdir(os.path.join(PATH,'clicks'))
        clist=[x for x in clist if not x.startswith('.')]
        clist.sort()
        try:
            idx=(clist.index(self.currentClick)+1)%len(clist)
        except ValueError:
            idx=-1
        self.setclick(clist[idx])

    def noclick(self):
        self.notify(unicode(self.tr('Disabling click')))
        self.beep=None
        self.currentClick=None

    def audiometadatachanged(self):
        try:
            self.notify (unicode(self.tr('Listening to: %s'))%self.music.metaData('TITLE')[0])
        except:
            pass
    
    def setstation(self, station):
        if not SOUND: return
        self.currentStation=station
        if self.music:
            self.music.deleteLater()
        self.music = Phonon.createPlayer(Phonon.MusicCategory,
                                  Phonon.MediaSource(self.currentStation))
        self.music.metaDataChanged.connect(self.audiometadatachanged)
        self.music.play()
        self.settings.setValue('station',self.currentStation)
        self.settings.sync()

    def prevstation(self):
        try:
            idx=(self.stations.index(self.currentStation)-1)%len(self.stations)
        except ValueError:
            idx=-1
        self.setstation(self.stations[idx])
        
    def nextstation(self):
        try:
            idx=(self.stations.index(self.currentStation)+1)%len(self.stations)
        except ValueError:
            idx=-1
        self.setstation(self.stations[idx])

    def nostation(self):
        if self.music:
            self.music.stop()
            self.notify(unicode(self.tr('Disabling music')))
        self.currentStation=None
        
    def setbg(self, bg):
        #from pudb import set_trace; set_trace()
        if bg != self.currentBG:
            self.currentBG=bg
            self.bgcolor=None
            self.notify(unicode(self.tr('Setting background to: %s'))%self.currentBG)
            if self.currentBG.split('.')[-1] in ["svg","svgz"]:
                # Render the SVG to a QImage
                renderer=QtSvg.QSvgRenderer(os.path.join(PATH,'backgrounds',bg))
                w,h=renderer.defaultSize().width(), renderer.defaultSize().height()
                while w < self.width() or \
                    h < self.height():
                    w *=1.2
                    h *=1.2
                self.bg=QtGui.QImage(w,h,QtGui.QImage.Format_ARGB32_Premultiplied)
                painter=QtGui.QPainter(self.bg)
                renderer.render(painter)
                painter.end()
                #self.bg=QtGui.QImage(pm)
            else:
                print 'LOADING'
                self.bg=QtGui.QImage(os.path.join(PATH,'backgrounds',bg))
        self.realBg=self.bg.scaled( self.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
        self.bgItem.setPixmap(QtGui.QPixmap(self.realBg))
        self.bgItem.setPos(self.width()-self.realBg.width(), self.height()-self.realBg.height())

    def prevbg(self):
        bglist=os.listdir(os.path.join(PATH,'backgrounds'))
        bglist=[x for x in bglist if not x.startswith('.')]
        bglist.sort()
        try:
            idx=(bglist.index(self.currentBG)-1)%len(bglist)
        except ValueError:
            idx=-1
        self.setbg(bglist[idx])
        
    def nextbg(self):
        bglist=os.listdir(os.path.join(PATH,'backgrounds'))
        bglist=[x for x in bglist if not x.startswith('.')]
        bglist.sort()
        try:
            idx=(bglist.index(self.currentBG)+1)%len(bglist)
        except ValueError:
            idx=0
        self.setbg(bglist[idx])
        
    def setbgcolor(self, bgcolor=None):
        if isinstance(bgcolor, QtGui.QColor):
            if bgcolor.isValid():
                self.bg=None
                self.realBG=None
                self.bgcolor=bgcolor
                pm=QtGui.QPixmap(self.width(), self.height())
                pm.fill(bgcolor)
                self.bgItem.setPixmap(pm)
                self.bgItem.setPos(0,0)
                self.notify(unicode(self.tr('Setting background to: %s'))%bgcolor.name())
        else:
            if self.bgcolor:
                self.setbgcolor(QtGui.QColorDialog.getColor(self.bgcolor, self))
            else:
                self.setbgcolor(QtGui.QColorDialog.getColor(QtGui.QColor("white"), self))

    def setfontcolor(self, color=None):
        if isinstance(color, QtGui.QColor):
            if color.isValid():
                self.editor.setStyleSheet("""background-color: transparent;
                                            color: %s;
                                          """%(unicode(color.name())))
                self.settings.setValue('fontcolor',color.name())
                self.fontcolor=color
                self.settings.sync()
        else:
            self.setfontcolor(QtGui.QColorDialog.getColor(QtGui.QColor("black"), self))

    def tajmode(self):
        self.noclick()
        self.nostation()
        self.setbgcolor(QtGui.QColor(0,0,0))
        self.setfontcolor(QtGui.QColor(0,255,0))
        
    def eventFilter(self, obj, event):
        if obj==self.editor:
            if event.type()==QtCore.QEvent.KeyPress:
                if self.beep:
                    if self.beep.state()==2:
                        self.beep.stop()
                    self.beep.play()
                self.hideCursor()
                self.hideButtons()
            elif isinstance(event, QtGui.QMoveEvent):
                self.showButtons()
        elif isinstance(event, QtGui.QHoverEvent):
            for b in self.buttons:
                if b != obj:
                    b.hideChildren()
                else:
                    b.showChildren()
                self.showButtons()
        return QtGui.QGraphicsView.eventFilter(self, obj, event)

    def keyEvent(self, ev):
        self.hideCursor()

    def mouseMoveEvent(self, ev):
        self.showCursor()
        self.showButtons()
        QtGui.QGraphicsView.mouseMoveEvent(self, ev)

    def changefont(self, font):
        f=self.editor.font()
        f.setFamily(font.family())
        self.editor.setFont(f)
        self.settings.setValue('font',self.editor.font())
        self.settings.sync()

    def resizeEvent(self, ev):
        self._scene.setSceneRect(QtCore.QRectF(self.geometry()))
        if self.bg:
            self.setbg(self.currentBG)
        elif self.bgcolor:
            self.setbgcolor(self.bgcolor)
        if not self.hasSize:
            self.editorX=self.width()*.1
            self.editorH=max(self.height()*.9, self.minH)
            self.editorY=self.height()*.05
            self.editorW=max(self.width()*.6, self.minW)

        self.adjustPositions()
        
    def adjustPositions(self):
        m=self.m
        if self.editor:
            if self.visibleWidget:
                self.editor.setGeometry(self.editorX,self.editorY,self.editorW,self.editorH-self.visibleWidget.height()-self.m)
            else:
                self.editor.setGeometry(self.editorX,self.editorY,self.editorW,self.editorH)
            self.editorBG.setPos(self.editorX-m,self.editorY-m)
            # Commenting this fixes Isue 15?????
            #self.editorBG.setBrush(QtGui.QColor(255,255,255,255))
            self.editorBG.setRect(0,0,self.editorW+2*m,self.editorH+2*m)
            self.mainMenu.setPos(self.editorX+self.editorW+3*m,self.editorY)
            self.searchBar.setPos(self.editorX,self.editorY+self.editorH-self.searchWidget.height())
            self.searchWidget.setFixedWidth(self.editor.width())
            self.searchReplaceBar.setPos(self.editorX,self.editorY+self.editorH-self.searchReplaceWidget.height())
            self.searchReplaceWidget.setFixedWidth(self.editor.width())
            self.prefsBar.setPos(self.editorX,self.editorY+self.editorH-self.prefsWidget.height())
            self.prefsWidget.setFixedWidth(self.editor.width())

            self.handles[0].setPos(self.editorX-2*m,self.editorY-2*m)
            self.handles[1].setPos(self.editorX+self.editorW,self.editorY-2*m)
            self.handles[2].setPos(self.editorX+self.editorW,self.editorY+self.editorH)
            self.handles[3].setPos(self.editorX-2*m,self.editorY+self.editorH)
            self.notifBar.proxy.setPos(self.editorX-m, self.editorY+self.editorH+2*m)
            self.notifBar.setFixedWidth(self.editorW+2*m)
            self.saveEditorGeometry()

    def scenechanged(self,region):
        if not self.changing:
            self.changing=True
            # See if the user dragged the editor
            flag=False
            m=self.m
            
            old=self.editorX, self.editorY, self.editorW, self.editorH
            
            # Editor dragged by the edge
            rect=self.editorBG.rect()
            pos=self.editorBG.pos()
            x=rect.x()+pos.x()
            y=rect.y()+pos.y()
            w=rect.width()
            h=rect.height()

            if x != self.editorX-m or   \
               y != self.editorY-m or   \
               w != self.editorW+2*m or \
               h != self.editorH+2*m:
                editorX=x+m
                editorY=y+m
                editorW=w-2*m
                editorH=h-2*m
                
                if editorW >= self.minW and editorH >= self.minH:
                    self.editorX = editorX
                    self.editorY = editorY
                    self.editorW = editorW
                    self.editorH = editorH
                self.hasSize=True
                self.adjustPositions()
                self.changing=False
                return
                   
            # Top-Left corner dragged
            rect=self.handles[0].rect()
            pos=self.handles[0].pos()
            x=rect.x()+pos.x()
            y=rect.y()+pos.y()
            if x != self.editorX-2*m or \
               y != self.editorY-2*m:
                    dx=x-self.editorX+2*m
                    dy=y-self.editorY+2*m
                    editorX=x+2*m
                    editorY=y+2*m
                    editorW=self.editorW-dx
                    editorH=self.editorH-dy
                    if editorW >= self.minW and editorH >= self.minH:
                        self.editorX = editorX
                        self.editorY = editorY
                        self.editorW = editorW
                        self.editorH = editorH                
                    self.hasSize=True
                    self.adjustPositions()
                    self.changing=False
                    return

            # Top-Right corner dragged
            rect=self.handles[1].rect()
            pos=self.handles[1].pos()
            x=rect.x()+pos.x()
            y=rect.y()+pos.y()
            if x != self.editorX+self.editorW or \
               y != self.editorY-2*m:
                    dx=x-self.editorX-self.editorW
                    dy=y-self.editorY+2*m
                    editorY=y+2*m
                    editorW=self.editorW+dx
                    editorH=self.editorH-dy
                    if editorW >= self.minW and editorH >= self.minH:
                        self.editorY = editorY
                        self.editorW = editorW
                        self.editorH = editorH                
                    self.hasSize=True
                    self.adjustPositions()
                    self.changing=False
                    return
                   
            # Bottom-Right corner dragged
            rect=self.handles[2].rect()
            pos=self.handles[2].pos()
            x=rect.x()+pos.x()
            y=rect.y()+pos.y()
            if x != self.editorX+self.editorW or \
               y != self.editorY+self.editorH:
                    dx=x-self.editorX-self.editorW
                    dy=y-self.editorY-self.editorH
                    editorW=self.editorW+dx
                    editorH=self.editorH+dy
                    if editorW >= self.minW and editorH >= self.minH:
                        self.editorW = editorW
                        self.editorH = editorH                
                    self.hasSize=True
                    self.adjustPositions()
                    self.changing=False
                    return

            # Bottom-Left corner dragged
            rect=self.handles[3].rect()
            pos=self.handles[3].pos()
            x=rect.x()+pos.x()
            y=rect.y()+pos.y()
            if x != self.editorX+2*m or \
               y != self.editorY+self.editorH:
                    dx=x-self.editorX+2*m
                    dy=y-self.editorY-self.editorH
                    editorX=x+2*m
                    editorW=self.editorW-dx
                    editorH=self.editorH+dy
                    if editorW >= self.minW and editorH >= self.minH:
                        self.editorX = editorX
                        self.editorW = editorW
                        self.editorH = editorH                
                    self.hasSize=True
                    self.adjustPositions()
                    self.changing=False
                    return

            self.changing=False
               
    def showButtons(self):
        for w in self.buttons + self.handles:
            w.targetOpacity=.8
            w.moveOpacity()

    def hideButtons(self):
        for w in self.buttons + self.handles:
            w.targetOpacity=0.
            w.moveOpacity()
            w.hideChildren()

    def hideCursor(self):
        QtCore.QCoreApplication.instance().setOverrideCursor(QtCore.Qt.BlankCursor)

    def showCursor(self):
        QtCore.QCoreApplication.instance().restoreOverrideCursor()

    def init(self):
        '''Initialization stuff that can really wait a little, so the window
        appears faster'''
        self._scene.changed.connect(self.scenechanged)
        
        self.bgItem.moveOpacity()

        # Event filters for showing/hiding buttons/cursor
        self.editor.installEventFilter(self)
        for b in self.buttons:
            b.installEventFilter(self)
        self.editor.modificationChanged.connect(self.setWindowModified)


def main():

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Marave')

    locale = unicode(QtCore.QLocale.system().name())
    
    qtTranslator=QtCore.QTranslator()
    qtTranslator.load("qt_" + locale,
            QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath))
    app.installTranslator(qtTranslator);    
    
    translator=QtCore.QTranslator()
    translator.load(os.path.join(PATH,"translations","marave_" + unicode(locale)))
    app.installTranslator(translator)


    parser = optparse.OptionParser()
    parser.add_option('--opengl', 
                      dest='opengl', 
                      default=False,
                      action='store_true', 
                      help='Enable OpenGL acceleration')
                      
    parser.add_option('--use-in-canvas-editor', 
                      dest='canvas', 
                      default=None,
                      action='store_true', 
                      help='Use an in-canvas editor, may be slower/prettier')

    parser.add_option('--use-off-canvas-editor', 
                      dest='canvas', 
                      default=None,
                      action='store_false', 
                      help='Use an off-canvas editor, may be faster/uglier')

    options, args = parser.parse_args()

    if len(args) > 1:
        QtGui.QMessageBox.information(None,app.translate('app','FOCUS!'),
        app.translate('app','Marave only opens one document at a time.\nThe whole idea is focusing!\nSo, this is the first one you asked for.'))

    window=MainWidget(opengl=options.opengl, canvaseditor=options.canvas)
    window.loadprefs()
    window.loadBG()
    window.show()
    window.raise_()
    window.showFullScreen()
    app.processEvents()
    window.editor.setFocus()
    app.processEvents()
    if not SOUND:
        QtCore.QTimer.singleShot(2000,window.warnnosound)
    QtCore.QTimer.singleShot(0,window.init)
    if args:
        load=lambda: window.editor.open(args[0])
        QtCore.QTimer.singleShot(10,load)
    
    # It's exec_ because exec is a reserved word in Python
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

import os
import io
import time
import locale
import psutil
import sqlite3
import calendar
import pandas as pd
import streamlit as st
import zstandard as zstd
from datetime import date
from unidecode import unidecode
from brutils.ibge.uf import convert_uf_to_name
from brutils.currency import format_currency
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

class displayQuery():
    def __init__(self, title):
        self.title = title 
        
    def queryDf(self, data, cols, selDf):
        cols[0] = "#"
        df = pd.DataFrame(data, columns=cols)
        nLanc = len(df)
        st.markdown(f"{self.title} <-> Deputado(a) Federal {selDf} <-> {nLanc} lançamento(s)")
        st.dataframe(data=df, width="stretch", hide_index=True)
    
    @st.dialog(title='Resultado', width="medium", icon=":material/analytics:", on_dismiss="ignore") 
    def menSearch(self, *args):
        nNames = args[0]
        nResults = args[1]
        yearStart = args[2]
        monthStart = args[3]
        yearEnd = args[4]
        monthEnd = args[5]
        uf = args[6]
        months = list(calendar.month_name)[1:]
        indStart = months.index(monthStart) + 1
        indEnd = months.index(monthEnd) + 1
        try:
            nameState = convert_uf_to_name(uf)
        except:
            nameState = "não identificável"
        if nNames > 999:
            nNames = format_currency(nNames).replace('R$', '').split(',')[0]
        if nResults > 999:
            nResults = format_currency(nResults).replace('R$', '').split(',')[0]
        exprSearch = f":material/date_range: **período**: {monthStart} de {yearStart} ({indStart}/{yearStart}) a {monthEnd} de {yearEnd} ({indEnd}/{yearEnd})<br>"
        exprSearch += f":material/flag_2: **estado**: {uf} ({nameState})<br>"
        exprSearch += f":material/numbers: **deputados**: {nNames}<br>"
        exprSearch += f":material/article: **registros**: {nResults}<br>"        
        st.markdown(exprSearch, unsafe_allow_html=True)

    @st.dialog(title='Erro', width="small", icon=":material/error:", on_dismiss="ignore") 
    def mensApp(self, *args):
        text = args[0]
        st.markdown(text, unsafe_allow_html=True)

class windowStream():
    def __init__(self, cols, filters, fileDb, tableDb):
        self.cols = cols
        self.filters = filters
        self.keys = sorted(list(filters.keys()))
        self.fileDb = fileDb
        self.tableDb = tableDb
        self.helpPlace = {1:[":material/date_range:", "data inicial", "Seleção da data inicial", 5, 6, "ano", "mês"], 
                          2:[":material/date_range:", "data final", "Seleção da data final", 7, 8, "ano", "mês"], 
                          3:[":material/flag:", "estado", "Seleção da unidade federativa", 9, "sigla"], 
                          4:[":material/person_raised_hand:", "deputados federais", "Seleção de deputados federais", 10, "nome"], 
                          5:[":material/no_accounts:", "deputados federais", "Sem nomes para seleção", 10, "nome"]}
                   
    def insertWidget(self):
        nSize = 4
        colStart, colEnd, colUf, colDf = st.columns([nSize*3, nSize*3, nSize*1.9, nSize**2], vertical_alignment="center", 
                                                    width="stretch")
        self.optMonthsAll = list(calendar.month_name)[1:]
        self.indMonths = [w + 1 for w in range(len(self.optMonthsAll))]
        optYears = self.filters[self.keys[0]] 
        self.optYears = optYears
        optYears.insert(0, '')
        self.optYearsEnd = []
        self.optMonthsEnd = []
        optUfs = self.filters[self.keys[2]]
        nOptUfs = len(optUfs)
        optUfs.insert(0, '')
        self.optMonths = []
        with colStart:
            dictVal = self.helpPlace[1]
            with st.container(border=True, width="stretch", horizontal_alignment="center", 
                              vertical_alignment="center"):
                strStart = self.formatLabel(dictVal[0], dictVal[3], dictVal[4], dictVal[1])
                st.markdown(strStart, unsafe_allow_html=True, text_alignment="left", 
                            anchors=True, help=dictVal[2])
                colYearStart, colMonthStart = st.columns([6, 8], vertical_alignment="center", width="stretch")
                self.yearStart = colYearStart.selectbox(label=dictVal[1], options=optYears, width="stretch", 
                                                        label_visibility="collapsed", key=wordKeys[dictVal[3]],
                                                        placeholder=dictVal[5])
                if self.yearStart:
                   self.defineMonths(1)
                else:
                   self.clearFields(1)
                self.monthStart = colMonthStart.selectbox(label=dictVal[1], options=self.optMonths, width="stretch", 
                                                          label_visibility="collapsed", key=wordKeys[dictVal[4]], 
                                                          disabled=st.session_state[wordKeys[1]], placeholder=dictVal[6])
                if self.monthStart:
                   self.defineMonths(2)
                else:
                   self.clearFields(2)
        with colEnd:
            dictVal = self.helpPlace[2]
            with st.container(border=True, width="stretch", horizontal_alignment="center", 
                              vertical_alignment="center"):
                strStart = self.formatLabel(dictVal[0], dictVal[3], dictVal[4], dictVal[1])
                st.markdown(strStart, unsafe_allow_html=True, text_alignment="left", 
                            anchors=True, help=dictVal[2])
                colYearEnd, colMonthEnd = st.columns([6, 8], vertical_alignment="center", width="stretch")
                self.yearEnd = colYearEnd.selectbox(label=dictVal[1], options=self.optYearsEnd, width="stretch", 
                                                    key=wordKeys[dictVal[3]], label_visibility="collapsed", 
                                                    disabled=st.session_state[wordKeys[2]], placeholder=dictVal[5])
                if self.yearEnd:
                   self.defineMonths(3)
                else:
                   self.clearFields(3)
                self.monthEnd = colMonthEnd.selectbox(label=dictVal[1], options=self.optMonthsEnd, width="stretch", key=wordKeys[dictVal[4]],
                                                      label_visibility="collapsed", disabled=st.session_state[wordKeys[3]], 
                                                      placeholder=dictVal[6])
                try:
                    if not self.monthEnd:
                        self.clearFields(4)
                except:
                    pass
        with colUf:
            dictVal = self.helpPlace[3]
            with st.container(border=True, width="stretch", horizontal_alignment="center", 
                              vertical_alignment="center"):
                strStart = self.formatLabel(dictVal[0], dictVal[3], dictVal[1])
                st.markdown(strStart, unsafe_allow_html=True, text_alignment="left", 
                            anchors=True, help=dictVal[2])
                if all([self.yearStart, self.monthStart, self.yearEnd, self.monthEnd]):
                    st.session_state[wordKeys[4]] = False
                else:
                    st.session_state[wordKeys[4]] = True
                uf = st.selectbox(label=dictVal[1], options=optUfs, width="stretch", label_visibility="collapsed", 
                                  key=wordKeys[dictVal[3]], placeholder=dictVal[4], disabled=st.session_state[wordKeys[4]], 
                                  on_change=self.changeState)
                results = []
                optsName = []
                try:
                    if not uf:
                        self.clearFields(5)
                    else:
                        try:
                            if all([uf is not None, uf.strip() != '']):
                                objOperat = operationFiles(self.tableDb)
                                indStart = self.optMonthsAll.index(self.monthStart) 
                                indEnd = self.optMonths.index(self.monthEnd)
                                optsName, results = objOperat.searchFields(self.fileDb, self.cols, indStart, self.yearStart, indEnd, self.yearEnd, uf, self.indMonths)
                                if st.session_state[wordKeys[11]] == 0:
                                    objDisplay = displayQuery('Resultado da pesquisa')
                                    objDisplay.menSearch(len(optsName), len(results), self.yearStart, self.monthStart, self.yearEnd, self.monthEnd, uf)
                                st.session_state[wordKeys[11]] += 1
                        except:
                            pass
                except:
                    pass
                nResults = len(results)
                self.nResults = nResults
                if nResults >= 1: 
                    dictVal = self.helpPlace[4]            
                    resultDisab = False
                else:
                    dictVal = self.helpPlace[5]
                    resultDisab = True 
        with colDf:
            with st.container(border=True, width="stretch", horizontal_alignment="center", 
                              vertical_alignment="center"):
                strStart = self.formatLabel(dictVal[0], dictVal[3], dictVal[1])
                st.markdown(strStart, unsafe_allow_html=True, text_alignment="left", 
                            anchors=True, help=dictVal[2])
                allSelDf = st.multiselect(label=dictVal[1], options=optsName, width="stretch", label_visibility="collapsed", 
                                          key=wordKeys[dictVal[3]], placeholder="Deputados a selecionar", accept_new_options= True, disabled=resultDisab)
        for selDf in allSelDf:
            objDisplay = displayQuery('Consulta de dados')
            if len(selDf) > 0:
                cotas = [result for result in results if result[15] == selDf]
                newCotas = []
                for c, cota in enumerate(cotas):
                    newCota = list(cota)
                    newCota[0] = c+1
                    newCotas.append(newCota)
                objDisplay.queryDf(newCotas, self.cols, selDf)
        
    def defineMonths(self, num):
        yearNow = date.today().year
        monthNow = date.today().month
        yearSel = self.yearStart
        self.optMonths = list(calendar.month_name)[1:]
        if yearSel == yearNow:
            self.optMonths = self.optMonths[:monthNow]
        self.optMonths.insert(0, '')
        if num == 1:
            st.session_state[wordKeys[num]] = False   
            indYearSel = self.optYears.index(yearSel)
            self.optYearsEnd = [self.optYears[w] for w in range(len(self.optYears)) if w >= indYearSel]
            self.optYearsEnd.insert(0, '')  
        elif num == 2:
            monthSel = self.monthStart
            st.session_state[wordKeys[num]] = False
            st.session_state[wordKeys[num+1]] = False
        elif num == 3:
            monthSel = self.monthStart
            st.session_state[wordKeys[num]] = False
            indMonthSel = self.optMonths.index(monthSel)
            if self.yearStart == self.yearEnd:
                self.optMonthsEnd = [self.optMonths[w] for w in range(len(self.optMonths)) if w >= indMonthSel]
            else:
                self.optMonthsEnd = self.optMonthsAll
            self.optMonthsEnd.insert(0, '')
    
    def clearFields(self, opt):
        match opt:
            case 1:
               st.session_state[wordKeys[1]] = True
               st.session_state[wordKeys[2]] = True
               st.session_state[wordKeys[3]] = True
               st.session_state[wordKeys[9]] = ''
               st.session_state[wordKeys[10]] = [] 
            case 2:
               st.session_state[wordKeys[2]] = True
               st.session_state[wordKeys[3]] = True
               st.session_state[wordKeys[7]] = ''
               st.session_state[wordKeys[8]] = ''
               st.session_state[wordKeys[9]] = ''
               st.session_state[wordKeys[10]] = []                 
            case 3:
               st.session_state[wordKeys[3]] = True
               st.session_state[wordKeys[9]] = ''
               st.session_state[wordKeys[10]] = [] 
            case 4:
               st.session_state[wordKeys[9]] = ''
               st.session_state[wordKeys[10]] = []
            case 5:
                st.session_state[wordKeys[10]]= []
                
    def changeState(self):
        st.session_state[wordKeys[11]] = 0   

    def formatLabel(self, *args):
        try:
            symbol = args[0]
            numOne = args[1]
            numTwo = args[2]
            exprMark = args[3]
            condTest = st.session_state[wordKeys[numOne]] and st.session_state[wordKeys[numTwo]]
        except:
            symbol = args[0]
            numOne = args[1]
            exprMark = args[2]
            condTest = st.session_state[wordKeys[numOne]]
        if condTest:
            strStart = f":blue[{symbol} **{exprMark}** :material/check:]"
        else:
            strStart = f":gray[{symbol} {exprMark} :material/close:]"
        return strStart        
    
class operationFiles():
    def __init__(self, tableDb):    
        self.tableDb = tableDb
    
    @st.cache_data(show_spinner=False)    
    def mergeFilesZsdt(_self, dirDbZsdt, fileDbZsdt):
        filesZsdt = sorted([f for f in os.listdir(dirDbZsdt) if f.lower().find('fake') < 0])
        if not filesZsdt:
            return False
        nTasks = len(filesZsdt)
        with open(fileDbZsdt, "wb") as fOut:
            for n in range(nTasks):
                file = filesZsdt[n]
                pathOut = os.path.join(dirDbZsdt, file)
                with open(pathOut, "rb") as f_chunk:
                    fOut.write(f_chunk.read())
        return True
    
    @st.cache_data(show_spinner=False)
    def readFileSqlZsdt(_self, fileDbZsdt, fileDb):
        dctx = zstd.ZstdDecompressor()
        with open(fileDbZsdt, "rb") as compressFile:
            with dctx.stream_reader(compressFile) as reader:
                decompressData = reader.read()
        dbStream = io.BytesIO(decompressData)
        with open(fileDb, 'wb') as f:
            f.write(dbStream.getvalue())
        return fileDb
    
    @st.cache_data(show_spinner=False)
    def columnSql(_self, fileDb):
        connDisk = sqlite3.connect(fileDb)
        cursor = connDisk.cursor()
        cursor.execute(f"PRAGMA table_info({_self.tableDb})")
        colunas = [info[1] for info in cursor.fetchall()]
        connDisk.close()
        return colunas
        
    @st.cache_data(show_spinner=False)
    def distinctFields(_self, fileDb, allFieldsDb):
        zFieldsDb = len(allFieldsDb)
        dictFilters = {}
        connDisk = sqlite3.connect(fileDb)
        cursor = connDisk.cursor()
        fieldsDb = [allFieldsDb[z] for z in range(zFieldsDb) if z in [1, 14, 26]]
        for fielDb in fieldsDb: 
            query = f"SELECT DISTINCT {fielDb} FROM {_self.tableDb} ORDER BY {fielDb} ASC"
            df = pd.read_sql(query, connDisk)
            try:
                data = sorted([int(field) for field in df[fielDb].tolist()])
            except:
                data = sorted(df[fielDb].tolist())
            dictFilters[fielDb] = data
        connDisk.close()
        return dictFilters
    
    @st.cache_data(show_spinner=False)
    def searchFields(_self, fileDb, cols, indStart, yearStart, indEnd, yearEnd, uf, indMonths):
        monthsDict = {}
        allMonthStart = indMonths[indStart:]
        monthsDict[yearStart] = allMonthStart
        allMonthEnd = indMonths[:indEnd+1]
        monthsDict[yearEnd] = allMonthEnd
        noYears = [year for year in list(range(yearStart, yearEnd))if year != yearStart and year != yearEnd] 
        for year in noYears: 
            monthsDict[year] = indMonths
        yearKeys = sorted(list(monthsDict.keys()))
        names = cols[15]
        dates = cols[6]
        year = cols[1]
        month = cols[14]
        siglaUf = cols[26]
        connDisk = sqlite3.connect(fileDb)
        cursor = connDisk.cursor()
        query = f"""
            SELECT * FROM {_self.tableDb}
            WHERE {year} BETWEEN ? AND ? AND {siglaUf} = ? ORDER BY {dates} ASC;
        """
        cursor.execute(query, (yearStart, yearEnd, uf))
        results = []
        for fetch in cursor.fetchall():
            monthInt = int(fetch[14])
            yearInt = int(fetch[1])
            if monthInt in monthsDict[yearInt]:
                results.append(fetch)
        connDisk.close() 
        optsName = sorted(list(set([result[15] for result in results])))
        nOptsName = len(optsName)
        optsName = sorted(optsName, key=lambda w: unidecode(w).lower())
        return(optsName, results)  

class main():
    def __init__(self):
        st.session_state[wordKeys[0]] += 1
        self.dirDbZsdtSt = r"C:\Users\ACER\Desktop\Ecossistema_Câmara_dos_Deputados\down_CD_chunks_Github"
        self.dirDbZsdtGit = "./quotaAll"
        self.setPage()
        self.isRunning()
        self.fileDbZsdt = "cota_parlamentar_CD_scraping.db.zst"
        self.fileDb = "cota_parlamentar_CD_scraping.db"
        self.tableDb = "gastos_cota_CD"
        self.initiationSql()
        
    def setPage(self):
        st.set_page_config(
            page_title='Cotas parlamentares/Câmara dos Deputados',
            page_icon=':material/image:',
            layout='wide', 
            initial_sidebar_state=None, 
            menu_items=None
        )
        
    def isRunning(self):
        if os.path.exists(self.dirDbZsdtSt):
            self.dirDbZsdt = self.dirDbZsdtSt
            fileCss = r'C:\Users\ACER\Documents\css\configCotasCd.css'
        else:
            self.dirDbZsdt = self.dirDbZsdtGit
            fileCss = 'configCotasCd.css'
        with open(fileCss) as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
            
    def initiationSql(self):
        objOperat = operationFiles(self.tableDb)
        objDisplay = displayQuery('Resultado da pesquisa')
        if st.session_state[wordKeys[0]] == 1:
            verifyZsdt = objOperat.mergeFilesZsdt(self.dirDbZsdt, self.fileDbZsdt)
            if not verifyZsdt:
                mensApp = "Não há base de dados (:material/database:) para leitura!<br>Execute a rotina de scraping!"
                objDisplay.mensApp(mensApp)
        else:
            verifyZsdt = True
        if verifyZsdt:
            process = psutil.Process(os.getpid())
            memoryInfo = process.memory_info()
            memoryUsedMb = memoryInfo.rss / (1024 * 1024 * 1024)
            if memoryUsedMb > 1:
                mensApp = "Foi extrapolado o limite de 1GB. Modifique as opções selecionadas."
            else:
                st.session_state[wordKeys[0]] += 1
                self.sqlRead = objOperat.readFileSqlZsdt(self.fileDbZsdt, self.fileDb)
                self.sqlCols = objOperat.columnSql(self.sqlRead) 
                self.sqlFilters = objOperat.distinctFields(self.sqlRead, self.sqlCols)
                objWindow = windowStream(self.sqlCols, self.sqlFilters, self.fileDb, self.tableDb)
                objWindow.insertWidget()
            
if __name__ == '__main__':
    global wordKeys
    wordKeys = ['count', 'enableMonthStart', 'enableYearEnd', 'enableMonthEnd', 
                'enableUfs', 'valYearStart', 'valMonthStart', 'valYearEnd', 'valMonthEnd', 
                'valUf', 'valDf', 'countSearch']
    for w, wordKey in enumerate(wordKeys):
        if w == 0:
            val = 0
        elif w >= 1 and w <= 4:
            val = True
        elif w >= 5 and w <= 9:
            val = None
        elif w == 10:
            val = []
        else:
            val = 0
        if wordKey not in st.session_state:
            st.session_state[wordKey] = val
    main()
   
#https://budgetcdbrasil-eh29nz9fmk7bkspyv6w3iv.streamlit.app/

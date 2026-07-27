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
from unidecode import unidecode
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

class windowStream():
    def __init__(self, cols, filters, fileDb, tableDb):
        self.cols = cols
        self.filters = filters
        self.keys = sorted(list(filters.keys()))
        self.fileDb = fileDb
        self.tableDb = tableDb
                
    def insertWidget(self):
        nSize = 4
        colStart, colEnd, colUf, colDf = st.columns([nSize*2, nSize*2, nSize*1.2, nSize**2])
        optMonths = list(calendar.month_name)[1:]
        indMonths = [w + 1 for w in range(len(optMonths))]
        optYears = self.filters[self.keys[0]]  
        optUfs = self.filters[self.keys[2]]
        nOptUfs = len(optUfs)
        optUfs.insert(0, '')
        with colStart:
            st.markdown('início')
            colMonthStart, colYearStart = st.columns(spec=2)
            monthStart = colMonthStart.selectbox(label='mês início', options=optMonths, width="stretch", 
                                                 label_visibility="collapsed")
            yearStart = colYearStart.selectbox(label='ano início', options=optYears, width="stretch", 
                                               label_visibility="collapsed")
        with colEnd:
            st.markdown('final')
            colMonthEnd, colYearEnd = st.columns(spec=2)
            monthEnd = colMonthEnd.selectbox(label='mês final', options=optMonths, width="stretch", 
                                             label_visibility="collapsed")
            yearEnd = colYearEnd.selectbox(label='ano final', options=optYears, width="stretch", 
                                            label_visibility="collapsed")
        with colUf:
            st.markdown(f"UF ({nOptUfs})")
            uf = st.selectbox(label='UF', options=optUfs, width="stretch", label_visibility="collapsed", 
                              placeholder="UF a selecionar")
        with colDf:
            results = []
            if all([uf is not None, uf.strip() != '']):
                objOperat = operationFiles(self.tableDb)
                indStart = monthStart.index(monthStart) 
                indEnd = optMonths.index(monthEnd)
                results = objOperat.searchFields(self.fileDb, self.cols, indStart, yearStart, indEnd, yearEnd, uf, indMonths)
            nResults = len(results)
            if nResults >= 1: 
                resultDisab = False
            else:
                resultDisab = True  
            optsName = sorted(list(set([result[15] for result in results])))
            nOptsName = len(optsName)
            optsName = sorted(optsName, key=lambda w: unidecode(w).lower())
            optsName.insert(0, '')
            st.markdown(f"Deputados federais ({nOptsName})")
            allSelDf = colDf.multiselect(label='Nome', options=optsName, width="stretch", label_visibility="collapsed", 
                                      placeholder="Deputados a selecionar", accept_new_options= True, disabled=resultDisab)
        
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
        try:
            with open(fileDbZsdt, "rb") as compressFile:
                with dctx.stream_reader(compressFile) as reader:
                    decompressData = reader.read()
            dbStream = io.BytesIO(decompressData)
            with open(fileDb, 'wb') as f:
                f.write(dbStream.getvalue())
            return fileDb
        except Exception as error:
            st.write(error)
    
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
        return results  

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
        else:
            self.dirDbZsdt = self.dirDbZsdtGit
            
    def initiationSql(self):
        objOperat = operationFiles(self.tableDb)
        if st.session_state[wordKeys[0]] == 0:
            verifyZsdt = objOperat.mergeFilesZsdt(self.dirDbZsdt, self.fileDbZsdt)
        else:
            verifyZsdt = True
        if verifyZsdt:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_used_mb = memory_info.rss / (1024 * 1024 * 1024)
            st.write(f"Memória usada: {memory_used_mb:.2f} GB") 
            st.session_state[wordKeys[0]] += 1
            self.sqlRead = objOperat.readFileSqlZsdt(self.fileDbZsdt, self.fileDb)
            self.sqlCols = objOperat.columnSql(self.sqlRead) 
            self.sqlFilters = objOperat.distinctFields(self.sqlRead, self.sqlCols)
            objWindow = windowStream(self.sqlCols, self.sqlFilters, self.fileDb, self.tableDb)
            objWindow.insertWidget()

if __name__ == '__main__':
    global wordKeys
    wordKeys = ['count']
    if wordKeys[0] not in st.session_state:
        st.session_state[wordKeys[0]] = 0
    main()
    
#https://budgetcdbrasil-eh29nz9fmk7bkspyv6w3iv.streamlit.app/

import os
import io
import time
import sqlite3
import calendar
import pandas as pd
import streamlit as st
import zstandard as zstd

class windowStream():
    def __init__(self, filters, fileDb, tableDb):
        self.filters = filters
        self.keys = sorted(list(filters.keys()))
        self.fileDb = fileDb
        self.tableDb = tableDb
                
    def insertWidget(self):
        colYear, colUf, colDf = st.columns([13, 3, 20])
        optMonths = self.filters[self.keys[2]]
        optYears = self.filters[self.keys[0]]  
        optUfs = self.filters[self.keys[-1]]
        optUfs.insert(0, '')
        with colYear:
            st.markdown('Datas início e término')
            colMonthStart, colYearStart, colMonthEnd, colYearEnd = st.columns(spec=4)
            monthStart = colMonthStart.selectbox(label='mês A', options=optMonths, width="stretch", 
                                                 label_visibility="collapsed")
            yearStart = colYearStart.selectbox(label='ano A', options=optYears, width="stretch", 
                                               label_visibility="collapsed")
            monthEnd = colMonthEnd.selectbox(label='mês B', options=optMonths, width="stretch", 
                                             label_visibility="collapsed")
            yearSEnd = colYearEnd.selectbox(label='ano B', options=optYears, width="stretch", 
                                            label_visibility="collapsed")
        with colUf:
            st.markdown('UF')
            uf = st.selectbox(label='UF', options=self.filters[self.keys[-1]], width="stretch", label_visibility="collapsed")
        if all([uf is not None, uf.strip() != '']):
            with colDf:
                st.markdown('Deputados federais')
                colDf.selectbox(label='Nome', options=[], width="stretch", label_visibility="collapsed")
            objOperat = operationFiles(self.tableDb) 
            results = objOperat.searchFields(self.fileDb, self.keys, 0, -1, year, uf)
            #optResults = sorted(list(set([result[15] for result in results])))
            #colDf.selectbox(label='Nome', options= optResults, width="stretch")

class operationFiles():
    def __init__(self, tableDb):    
        self.tableDb = tableDb
    
    @st.cache_data    
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
    
    @st.cache_data
    def readFileSqlZsdt(_self, fileDbZsdt, fileDb):
        dctx = zstd.ZstdDecompressor()
        with open(fileDbZsdt, "rb") as compressFile:
            with dctx.stream_reader(compressFile) as reader:
                decompressData = reader.read()
        dbStream = io.BytesIO(decompressData)
        with open(fileDb, 'wb') as f:
            f.write(dbStream.getvalue())
        return fileDb
    
    @st.cache_data
    def columnSql(_self, fileDb):
        connDisk = sqlite3.connect(fileDb)
        connMemory = sqlite3.connect(':memory:')
        connDisk.backup(connMemory)
        cursor = connMemory.cursor()
        cursor.execute(f"PRAGMA table_info({_self.tableDb})")
        colunas = [info[1] for info in cursor.fetchall()]
        connMemory.close()
        connDisk.close()
        return colunas
        
    @st.cache_data
    def distinctFields(_self, fileDb, allFieldsDb):
        zFieldsDb = len(allFieldsDb)
        dictFilters = {}
        connDisk = sqlite3.connect(fileDb)
        connMemory = sqlite3.connect(':memory:')
        connDisk.backup(connMemory)
        cursor = connMemory.cursor()
        fieldsDb = [allFieldsDb[z] for z in range(zFieldsDb) if z in [1, 12, 14, 15, 25, 26]]
        for fielDb in fieldsDb: 
            query = f"SELECT DISTINCT {fielDb} FROM {_self.tableDb} ORDER BY {fielDb} ASC"
            df = pd.read_sql(query, connMemory)
            try:
                data = sorted([int(field) for field in df[fielDb].tolist()])
            except:
                data = sorted(df[fielDb].tolist())
            dictFilters[fielDb] = data
        connMemory.close()
        connDisk.close()
        return dictFilters
    
    @st.cache_data
    def searchFields(_self, fileDb, keys, posOne, posTwo, valOne, valTwo):
        fieldOne = keys[posOne]
        fieldTwo = keys[posTwo]        
        connDisk = sqlite3.connect(fileDb)
        connMemory = sqlite3.connect(':memory:')
        cursor = connMemory.cursor()
        connDisk.backup(connMemory)
        query = f"SELECT * FROM {_self.tableDb} WHERE {fieldOne} = ? AND {fieldTwo} = ?"
        cursor.execute(query, (valOne, valTwo))
        results = cursor.fetchall()
        connMemory.close()
        connDisk.close() 
        return results
        
class main():
    def __init__(self):
        self.dirDbZsdtSt = r"C:\Users\ACER\Desktop\Ecossistema_Câmara_dos_Deputados\down_CD_chunks_Github"
        self.dirDbZsdtGit = "./quotaAll"
        self.setPage()
        self.isRunning()
        self.fileDbZsdt = "cota_parlamentar_CD_scraping.db.zst"
        self.fileDb = "cota_parlamentar_CD_scraping.db"
        self.tableDb = "gastos_cota_CD"
        self.sqlRead = None
        self.sqlCols = None
        self.sqlFilters = {}
        self.initiationSql()
        st.session_state[wordKeys[0]] += 1
        objWindow = windowStream(self.sqlFilters, self.fileDb, self.tableDb)
        objWindow.insertWidget()
        
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
        with st.spinner("Atualizando o banco de dados"):
            verifyZsdt = objOperat.mergeFilesZsdt(self.dirDbZsdt, self.fileDbZsdt)
            if verifyZsdt:
                self.sqlRead = objOperat.readFileSqlZsdt(self.fileDbZsdt, self.fileDb)
                self.sqlCols = objOperat.columnSql(self.sqlRead)
                self.sqlFilters = objOperat.distinctFields(self.sqlRead, self.sqlCols)    
                st.write(self.sqlCols)
        
if __name__ == '__main__':
    global wordKeys
    wordKeys = ['count']
    if wordKeys[0] not in st.session_state:
        st.session_state[wordKeys[0]] = 0
    main()
    
#https://budgetcdbrasil-eh29nz9fmk7bkspyv6w3iv.streamlit.app/

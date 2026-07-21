import streamlit as st
import sqlite3
import pandas as pd
import os
import io
import time
import zstandard as zstd

class windowStream():
    def __init__(self, filters):
        self.filters = filters
        
    def insertWidget(self):
        for filter in self.filters:
            st.write(filter)
        
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
        objWindow = windowStream(self.sqlFilters)
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
                st.markdown("Colunas e filtros")
                self.sqlRead = objOperat.readFileSqlZsdt(self.fileDbZsdt, self.fileDb)
                self.sqlCols = objOperat.columnSql(self.sqlRead)
                self.sqlFilters = objOperat.distinctFields(self.sqlRead, self.sqlCols)    
        
if __name__ == '__main__':
    global wordKeys
    wordKeys = ['count']
    if wordKeys[0] not in st.session_state:
        st.session_state[wordKeys[0]] = 0
    main()
    

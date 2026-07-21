import streamlit as st
import sqlite3
import pandas as pd
import os
import io
import time
import zstandard as zstd

class operationFiles():
    def __init__(self):    
        pass 

    @st.cache_data    
    def mergeFilesZsdt(_self, dirDbZsdt, fileDbZsdt):
        filesZsdt = sorted([f for f in os.listdir(dirDbZsdt)])
        filesZsdt = sorted([f for f in os.listdir(dirDbZsdt) if f.lower().find('fake') < 0])
        if not filesZsdt:
            return False
        nTasks = len(filesZsdt)
        st.write(nTasks)
        barProg = st.progress(0.0)
        textProg = st.empty()
        with open(fileDbZsdt, "wb") as fOut:
            for n in range(nTasks):
                file = filesZsdt[n]
                pathOut = os.path.join(dirDbZsdt, file)
                with open(pathOut, "rb") as f_chunk:
                    fOut.write(f_chunk.read())
                textProg.text(f"Progresso: {n} de {nTasks} concluído")
                fracao = n / nTasks
                barProg.progress(fracao)
            barProg.empty()
            textProg.empty()
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
    def selectSql(_self, fileDb, tableDb):
        conn = sqlite3.connect(fileDb)
        query = f"SELECT * FROM {tableDb} LIMIT 100"
        data = pd.read_sql(query, conn)
        return data

    @st.cache_data
    def columnSql(_self, fileDb, tableDb):
        connDisk = sqlite3.connect(fileDb)
        connMemory = sqlite3.connect(':memory:')
        connDisk.backup(connMemory)
        cursor = connMemory.cursor()
        cursor.execute(f"PRAGMA table_info({tableDb})")
        colunas = [info[1] for info in cursor.fetchall()]
        connMemory.close()
        connDisk.close()
        return colunas

    @st.cache_data
    def distinctFields(_self, fileDb, tableDb, fielDb):
        connDisk = sqlite3.connect(fileDb)
        connMemory = sqlite3.connect(':memory:')
        connDisk.backup(connMemory)
        cursor = connMemory.cursor()
        query = f"SELECT DISTINCT {fielDb} FROM {tableDb} ORDER BY {fielDb}"
        data = pd.read_sql(query, connMemory)
        connMemory.close()
        connDisk.close()
        return data

class main():
    def __init__(self):
        self.dirDbZsdtSt = r"C:\Users\ACER\Desktop\Ecossistema_Câmara_dos_Deputados\down_CD_chunks_Github"
        self.dirDbZsdtGit = "./quotaAll"
        self.setPage()
        self.isRunning()
        self.fileDbZsdt = "cota_parlamentar_CD_scraping.db.zst"
        self.fileDb = "cota_parlamentar_CD_scraping.db"
        self.table = "gastos_cota_CD"
        objOperat = operationFiles()
        try:
            with st.spinner("Atualizando o banco de dados"):
                verifyZsdt = objOperat.mergeFilesZsdt(self.dirDbZsdt, self.fileDbZsdt)
                if verifyZsdt:
                    st.markdown("Consolidador de SQLite Local")
                    tempDbFile = objOperat.readFileSqlZsdt(self.fileDbZsdt, self.fileDb)
                    dataSql = objOperat.selectSql(tempDbFile, self.table) 
                    st.dataframe(dataSql)
                    cols = objOperat.columnSql(tempDbFile, self.table)
                    st.write(cols)
                    ind = objOperat.distinctFields(tempDbFile, self.table, cols[15])
                    st.dataframe(ind)

        except Exception as error:
            st.error(f'Erro na abertura do app:{error}')

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

if __name__ == '__main__':
    main()

#https://budgetcdbrasil-4rtegiwypo57t9cuzzacwr.streamlit.app/
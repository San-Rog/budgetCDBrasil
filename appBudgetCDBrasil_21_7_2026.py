import os
import io
import time
import httpx
import locale
import psutil
import sqlite3
import asyncio
import calendar
import pandas as pd
import streamlit as st
import zstandard as zstd
from datetime import date
from unidecode import unidecode
from brutils.currency import format_currency
from brutils.ibge.uf import convert_uf_to_name
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

class acessories():
    def __init__(self, num):
        self.num = num
    
    def convertNumber(self, mode):
        if mode == 0:
            if self.num <= 999:
                num = self.num
            else:
                num = format_currency(self.num).replace('R$', '').split(',')[0]
        else:
            num = format_currency(self.num).replace('R$', '')
        return num 
    
    def extractData(self):
        dataAllSplit = []
        nums = [str(num) for num in range(self.num[0], self.num[1]+1)]
        for data in dataSiteCd:
            dataSplit = data.split(seps[1])
            if len(dataSplit) == 1:
                dataAllSplit.append(dataSplit)
            else:
                for num in nums: 
                    if any([dataSplit[0].find(num) >= 0, dataSplit[0].find(num) >= 0]):
                        dataAllSplit.append(dataSplit)
        return dataAllSplit
            
class displayQuery():
    def __init__(self, title):
        self.title = title 
    
    def queryDf(self, cols, allSelDf, results, colData, start, end):
        nSelDf = len(allSelDf)
        numStr = f"{nSelDf} deputado federal" if nSelDf <= 1 else f"{nSelDf} deputados federais" 
        dataAllSplit = acessories([start, end]).extractData()
        with colData.expander(label="Detalhes da pesquisa", expanded=False, icon=":material/person_search:", 
                              width="stretch"):
            st.markdown(f"{self.title} {'.'.join(dataAllSplit[0])}", width="stretch")
            df = pd.DataFrame(dataAllSplit[1:])
            df.columns = ['link', 'download (arquivo)', 'criação (dia e horário)', 'modificação (dia e horário)', 'tamanho']
            nDf = len(df)
            if nDf == 1:
                exprDetail = "Informações sobre o único arquivo-download utilizado:"
            else:
                exprDetail = f"Informações sobre os {nDf} arquivos-download utilizados:"
            st.markdown(f":material/folder_info: {exprDetail}", width="stretch")
            st.dataframe(data=df, hide_index=True)        
        with colData.container(border=True, width="stretch", horizontal_alignment="center", 
                               vertical_alignment="center"): 
            allDfs = []
            cont = 0
            for s, selDf in enumerate(allSelDf):
                cotas = [result for result in results if result[15] == selDf]
                newCotas = []
                urlDocs = []
                for c, cota in enumerate(cotas):
                    newCota = list(cota)
                    newCota[0] = acessories(c+1).convertNumber(0)
                    newCotas.append(newCota)
                    cont += 1
                cols[0] = "#"
                urlDocs.append(newCotas)
                df = pd.DataFrame(newCotas, columns=cols)
                arrow = ":material/arrow_range:"
                nLanc = len(df)
                exprLanc = f"{nLanc} lançamento" if nLanc <= 1 else f"{acessories(nLanc).convertNumber(0)} lançamentos"
                st.markdown(f":material/tag: {s+1}/{nSelDf} {arrow} deputado(a) federal {selDf} {arrow} {exprLanc}")
                st.dataframe(data=df, width="stretch", hide_index=True)
                if nSelDf > 1:
                    st.divider(width="stretch")
                    allDfs.append(df)
                for url in urlDocs:
                    for u, ur in enumerate(url):
                        cont += u
                        st.markdown(f":material/topic: lançamento {u+1}/{nLanc} {arrow} deputado(a) federal {selDf}")
                        url = ur[29]
                        st.dataframe(data=df.iloc[[u]], width="stretch", hide_index=True)
                        if url.strip() == '':
                            st.markdown(f":material/ad_off: documento de despesa não cadastrado.")
                        else:
                            st.markdown(f":material/link: link para download: {url}")
                            try:
                                pdfBytes = asyncio.run(operationFiles(None).downPdfAsync(url))
                                if pdfBytes.startswith(b'%PDF-'):
                                    st.markdown(f":material/document_scanner: documento baixado") 
                                else:
                                    st.markdown(f":material/skull: documento não baixável de forma direta (captcha ou similiar)")
                                st.pdf(data=pdfBytes, height="stretch", key=f"pdf_{cont}")
                            except Exception as e:
                                st.markdown(f":material/document_scanner: não gerado")
                                st.markdown(f"Erro ao processar: {e}")
            if allDfs != []:
                dfAll = pd.concat(allDfs, ignore_index=True)
                nDfAll = len(dfAll)
                exprLanc = f"{nDfAll} lançamento" if nDfAll <= 1 else f"{acessories(nDfAll).convertNumber(0)} lançamentos"
                st.markdown(f":material/group: todos os deputados federais {arrow} {exprLanc}")
                st.dataframe(data=dfAll, width="stretch", hide_index=True)
    
    @st.dialog(title='Colunas', width="medium", icon=":material/analytics:", on_dismiss="ignore")
    def filterDf(self, cols):
        colsMark = [w for w in range(len(cols))]
        df = pd.DataFrame({"Filtros": cols})
        
        evento = st.dataframe(df, key="tabela", on_select="rerun", 
                              selection_mode="multi-row", selection_default={"selection": {"rows":colsMark}})
        linhas_selecionadas = evento.selection.rows
        if linhas_selecionadas:
            for linha in linhas_selecionadas:
                df_filtrado = df.iloc[linha]
    
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
        nums = [nNames, nResults]
        newNums = list(map(lambda num: acessories(num).convertNumber(0), nums))
        exprSearch = f":material/date_range: **período**: {monthStart} de {yearStart} ({indStart}/{yearStart}) a {monthEnd} de {yearEnd} ({indEnd}/{yearEnd})<br>"
        exprSearch += f":material/flag_2: **estado**: {uf} ({nameState})<br>"
        exprSearch += f":material/numbers: **deputados**: {newNums[0]}<br>"
        exprSearch += f":material/article: **registros**: {newNums[1]}<br>"        
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
        self.helpPlace = {1:[":material/date_range:", "data inicial", "Selecione a data inicial (mês e ano).", 5, 6, "ano", "mês"], 
                          2:[":material/date_range:", "data final", "Selecione a data final (mês e ano).", 7, 8, "ano", "mês"], 
                          3:[":material/flag:", "estado", "Selecione uma unidade federativa por vez", 9, "sigla"], 
                          4:[":material/person_raised_hand:", "deputados federais", "Selecione um ou mais deputados federais por vez", 10, "nome"], 
                          5:[":material/no_accounts:", "deputados federais", "Não existem deputados federais para selecionar.", 10, "nome"]}
        self.yearNow = date.today().year
        self.monthNow = date.today().month 
        self.optMonthsAll = list(calendar.month_name)[1:]
        
    def insertWidget(self):
        nSize = 4
        colStart, colEnd, colUf, colDf = st.columns([nSize*3, nSize*3, nSize*1.9, nSize**2], vertical_alignment="center", 
                                                     width="stretch")
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
                            anchors=True, help=f"{dictVal[2]} ({nOptUfs} existentes)")
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
                self.results = results
                nResults = len(results)
                self.nResults = nResults
                if nResults >= 1: 
                    dictVal = self.helpPlace[4] 
                    resultDisab = False
                else:
                    dictVal = self.helpPlace[5]
                    resultDisab = True 
                nNames = len(optsName)
                encText = ""
                if nNames == 1:
                    encText = f" (somente {nNames} encontrado)."
                elif nNames > 1:
                    encText = f" ({nNames} encontrados)."
                dictHelp =  dictVal[2] + encText
        with colDf:
            with st.container(border=True, width="stretch", horizontal_alignment="center", 
                              vertical_alignment="center"):
                strStart = self.formatLabel(dictVal[0], dictVal[3], dictVal[1])
                st.markdown(strStart, unsafe_allow_html=True, text_alignment="left", 
                            anchors=True, help=dictHelp)
                self.allSelDf = st.multiselect(label=dictVal[1], options=optsName, width="stretch", label_visibility="collapsed", 
                                               key=wordKeys[dictVal[3]], placeholder=dictVal[4], 
                                               accept_new_options=True, disabled=resultDisab, on_change=self.multisel)
        keyButt = "keyButton"
        prefixButt = "button"
        self.click = False
        dictButtons = {"tela_original": ["original", f"{keyButt}Original", ":material/screen_search_desktop:", "Exibe os dados originais do site."], 
                       "tela_modificada": ["modificada", f"{keyButt}Modify", ":material/edit_square:", "Exibe os dados com parcial modificação de formato."], 
                       "tela_grapho": ["gráfico", f"{keyButt}Grapho", ":material/insert_chart:", "Plota gráfico com os dados."], 
                       "tela_pdf": ["pdf", f"{keyButt}Pdf", ":material/picture_as_pdf:", "Gera arquivo PDF."], 
                       "tela_word": ["word", f"{keyButt}Word", ":material/text_snippet:", "Gera arquivo Word."]} 
        keyButtons = list(dictButtons.keys())
        nKeys = len(keyButtons)
        nSelfDf = len(self.allSelDf)
        if nSelfDf > 0:
            colButtons = st.columns(nKeys)
            for c, col in enumerate(colButtons):
                elemButton = dictButtons[keyButtons[c]]
                col.button(label=elemButton[0], key=elemButton[1], on_click=self.checkButton, args=(c, ),  
                           use_container_width=True, width="stretch", icon=elemButton[2], help=elemButton[3])
            self.colData = st.columns(1)[0]
        else:
            st.session_state[wordKeys[13]] = False
        
    def checkButton(self, value):
        st.session_state[wordKeys[13]] = True
        match value:
            case 0:
                title = f":material/data_table: Origem dos dados: "
                objDisplay = displayQuery(title)
                objDisplay.queryDf(self.cols, self.allSelDf, self.results, self.colData, 
                                   self.yearStart, self.yearEnd)
            case 1:
                pass
            case 2:
                #objDisplay.filterDf(self.cols)
                pass
            case 3:
                #objDisplay.filterDf(self.cols)
                pass
            case 4:
                #objDisplay.filterDf(self.cols)
                pass
    
    def defineMonths(self, num):
        yearSel = self.yearStart
        self.optMonths = list(calendar.month_name)[1:]
        if yearSel == self.yearNow:
            self.optMonths = self.optMonths[:self.monthNow]
        self.optMonths.insert(0, '')
        match num:
            case 1:
                st.session_state[wordKeys[num]] = False   
                indYearSel = self.optYears.index(yearSel)
                self.optYearsEnd = [self.optYears[w] for w in range(len(self.optYears)) if w >= indYearSel]
                self.optYearsEnd.insert(0, '')  
            case 2:
                monthSel = self.monthStart
                st.session_state[wordKeys[num]] = False
                st.session_state[wordKeys[num+1]] = False
            case 3:
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
                st.session_state[wordKeys[9]] = ''
                st.session_state[wordKeys[10]]= []
                
    def changeState(self):
        st.session_state[wordKeys[10]]= []
        st.session_state[wordKeys[11]] = 0 

    def multisel(self):
        st.session_state[wordKeys[13]] = False

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

    async def downPdfAsync(self, url: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content    
    
class main():
    def __init__(self):
        global dataSiteCd
        dataSiteCd = []
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
            fileTxt = r'C:\Users\ACER\Desktop\Ecossistema_Câmara_dos_Deputados\down_CD_integration\files_json_zip.txt'
            fileCss = r'C:\Users\ACER\Documents\css\configCotasCd.css'
        else:
            self.dirDbZsdt = self.dirDbZsdtGit
            fileTxt = r'fileQuotas/files_json_zip.txt'
            fileCss = 'configCotasCd.css'
        with open(fileTxt, 'r', encoding='utf-8') as f:
            readTxt = f.readlines()
        for txt in readTxt:
            dataSiteCd.append(txt)
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
    global wordKeys, seps
    wordKeys = ['count', 'enableMonthStart', 'enableYearEnd', 'enableMonthEnd', 
                'enableUfs', 'valYearStart', 'valMonthStart', 'valYearEnd', 'valMonthEnd', 
                'valUf', 'valDf', 'countSearch', 'allFillters', 'borderContainer']
    for w, wordKey in enumerate(wordKeys):
        if w == 0:
            val = 0
        elif w >= 1 and w <= 4:
            val = True
        elif w >= 5 and w <= 9:
            val = None
        elif w in [10, 12]:
            val = []
        elif w == 11:
            val = 0
        else:
            val = False
        if wordKey not in st.session_state:
            st.session_state[wordKey] = val
    seps = ["***", "&&&"]
    main()   
#https://budgetcdbrasil-eh29nz9fmk7bkspyv6w3iv.streamlit.app/

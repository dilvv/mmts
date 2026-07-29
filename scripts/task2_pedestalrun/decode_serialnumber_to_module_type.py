#!/usr/bin/env python3
### source https://github.com/ltsai323/csv_to_xml_converter/blob/main/ComplexFunctionForColumn.py#L196
import logging

log = logging.getLogger(__name__)
import csv

DEBUG_MODE = False
class kind_of_part_mapping:
    def __init__(self, csvFILEs:list):
        self.entries = []
        self.codes_history = set()
        for csvFILE in csvFILEs:
            log.debug(f'[LoadKindOfPart] file "{ csvFILE }" loaded.')
            with open(csvFILE, 'r') as f:
                reader = csv.DictReader(f)
                for entry in reader:
                    # load entry in CSV file and add additional column 'code'.
                    code = entry['LABEL_TYPECODE'].upper().replace('-','')
                    if code == '': continue
                    entry['code'] = code
                    if code in self.codes_history:
                        warning(f'[Duplicated KindOfPart] Got duplicated code "{ code }" in entry "{ entry }". Skip it')
                        continue
                    self.entries.append(entry)
                    self.codes_history.add(code)


        log.debug(f'[Initialized] kind_of_part_mapping() correctly activated')
    def Get(self, barcode):
        if '320' != barcode[0:3]: raise IOError(f'[InvalidBarcode] {barcode}')
        
        try:
            barcode_piece = barcode[3:-5]
            if len(barcode_piece) < 2: raise IndexError()
        except IndexError as e:
            raise IndexError(f'\n\n[InvalidBARCODE] input barcode "{barcode}" cannot get correct barcode piece from barcode[3:-5]\n\n') from e
        for entry in self.entries:
            if entry['code'] in barcode_piece:
                if entry['code'] == "": continue
                if DEBUG_MODE: log.debug(f'[SearchRes] KindOfPart got barcode "{barcode_piece}" matching "{entry["code"]}" so the result is "{entry["DISPLAY_NAME"]}"')
                if not DEBUG_MODE: print( entry['DISPLAY_NAME'] )
                return entry['DISPLAY_NAME']
        err_mesg = f'[NoSearchResult] kind_of_part_mapping() is unable to match barcode "{ barcode }".'

        if DEBUG_MODE: log.debug(err_mesg)
        if DEBUG_MODE: log.debug('[IgnoreEmptyValue] kind_of_part_mapping() puts empty value in this field.')
        if not DEBUG_MODE: print(f'[ERROR] Unable to find module name from barcode = "{ barcode }"')
        return ''

        #raise IOError(err_mesg)

kindofpart_sources = None
def init_kind_of_part_searcher(kindOFpartsCSVs:list):
    global kindofpart_sources
    kindofpart_sources = kind_of_part_mapping(kindOFpartsCSVs)

def FindKindOfPart(BARCODEorSERIALNUMBER:str):
    global kindofpart_sources
    try:
        return kindofpart_sources.Get(BARCODEorSERIALNUMBER)
    except AttributeError as e:
        raise RuntimeError(f'[FindKindOfPart] kindofpart_sources is not initialized, Use init_kind_of_part_searcher() before use this function\n\n\n')

def FindKindOfPart_AncientCoding(BARCODEorSERIALNUMBER:str):
    new_barcode = '320'+BARCODEorSERIALNUMBER
    return FindKindOfPart(new_barcode)

def testfunc_FindKindOfPart():
    kop_file = ['data/Kind_of_parts.csv', 'data/Kind_of_parts_appendix.csv']
    init_kind_of_part_searcher(kop_file)

    serial_number = '320070100300068'
    log.info(FindKindOfPart(serial_number))
    exit()
def mainfunc_FindKindOfPart():
    ### use print to show message that can communicate with bash script ###
    global DEBUG_MODE
    DEBUG_MODE = False
    import sys
    moduleID = sys.argv[1] if len(sys.argv)>1 else ''
    
    kop_file = ['data/Kind_of_parts.csv', 'data/Kind_of_parts_appendix.csv']
    init_kind_of_part_searcher(kop_file)
    FindKindOfPart(moduleID)
    

if __name__ == "__main__":
    #testfunc_FindKindOfPart()
    mainfunc_FindKindOfPart()

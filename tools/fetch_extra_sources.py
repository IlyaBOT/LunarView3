"""Fetch original manufacturer PDFs from known official/archive URLs."""
from pathlib import Path
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor

OUT=Path(__file__).resolve().parents[1]/'docs'/'datasheets'
SOURCES={
 'NM27C010':'https://datasheets.pl/elementy_czynne/IC/NM/NM27C010-2.pdf',
 'NM27C020':'https://www.pselectronic.cz/pdf/1125/11250125.pdf',
 'NM27C040':'https://docs.rs-online.com/a680/0900766b80025540.pdf',
 'MMBT5401':'https://www.diodes.com/datasheet/download/MMBT5401.pdf',
 'MMBT5551':'https://www.diodes.com/datasheet/download/MMBT5551.pdf',
 'BAT54WS':'https://www.topdiode.com/pdf/BAT54WS.pdf',
 'BAT54S':'https://assets.nexperia.com/documents/data-sheet/BAT54S.pdf',
 '74LVC1G08':'https://assets.nexperia.com/documents/data-sheet/74LVC1G08.pdf',
 '74HC595':'https://assets.nexperia.com/documents/data-sheet/74HC_HCT595.pdf',
 'APFA3010':'https://www.kingbrightusa.com/images/catalog/SPEC/APFA3010LSEEZGKQBKC.pdf',
}
def fetch(item):
    name,url=item
    try:
        data=urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
        if not data.startswith(b'%PDF'):raise ValueError('Response is not PDF')
        (OUT/(name+'.pdf')).write_bytes(data)
        return name,len(data),'OK'
    except Exception as exc:return name,str(exc)
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(fetch,SOURCES.items()):print(*result)

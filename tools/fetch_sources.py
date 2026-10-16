"""Fetch original manufacturer PDFs for local verification; reject non-PDF responses."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URLS = {
    'CH340_WCH': 'https://cdn.sparkfun.com/assets/5/0/a/8/5/CH340DS1.PDF',
    'ATmega328P': 'https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf',
    'LM317': 'https://www.ti.com/lit/ds/symlink/lm317.pdf',
    'HCT245': 'https://www.ti.com/lit/ds/symlink/sn74hct245.pdf',
    'IRF9540N': 'https://www.infineon.com/dgdl/irf9540npbf.pdf?fileId=5546d462533600a401535611c1d31dc8',
}
def fetch(item):
    name,url=item
    try:
        data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25).read()
        if not data.startswith(b'%PDF'):
            return name+': response is not a PDF'
        (ROOT/'docs'/'datasheets'/f'{name}.pdf').write_bytes(data)
        return name+': PDF received'
    except Exception as e:
        return name+': '+str(e)
if __name__=='__main__':
    (ROOT/'docs'/'datasheets').mkdir(parents=True,exist_ok=True)
    for result in ThreadPoolExecutor(max_workers=6).map(fetch,URLS.items()):
        print(result)

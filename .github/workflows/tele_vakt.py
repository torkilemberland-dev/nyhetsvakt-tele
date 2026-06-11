import os
import requests
import time
from dotenv import load_dotenv

# 1. Last inn miljøvariabler (GitHub Actions fôrer denne automatisk fra Secrets)
load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_TELENOR")

HEADERS = {"User-Agent": "Nordlys-Nyhetsvakt/3.0 (torkil.emberland@nordlys.no)"}

def sjekk_telenor():
    """Sjekker Telenor via en geografisk boks som dekker HELE Troms fylke."""
    print("Sjekker Telenor...")
    url = "https://www.telenor.no/system/coverage/map/kog/plannedwork/identify"
    troms_fylkesboks = "540000,7600000,820000,7880000"
    
    params = {
        "geometry": troms_fylkesboks,
        "geometryType": "esriGeometryEnvelope",
        "sr": "25833",
        "mapExtent": "300000,6500000,900000,8000000",
        "imageDisplay": "1000,1000,96",
        "tolerance": "0",
        "layers": "all:0,7",
        "f": "json"
    }
    
    try:
        respons = requests.get(url, params=params, headers=HEADERS, timeout=15)
        results = respons.json().get("results", [])
        
        for element in results:
            if element.get("layerId") != 0: # Ignorerer normal dekning
                attr = element.get("attributes", {})
                status = attr.get("STATUS", "Ukjent alvorlighetsgrad")
                start_tid = attr.get("START_DATE", "Ukjent tidspunkt")
                lag_navn = element.get("layerName", "Nettutfall")
                
                msg = (
                    f"🔵 *TELENOR: Aktiv feil registrert i Troms!*\n"
                    f"• *Type:* {lag_navn}\n"
                    f"• *Alvorlighetsgrad:* {status}\n"
                    f"• *Siden:* {start_tid}\n"
                )
                send_slack_varsel(msg)
    except Exception as e:
        print(f"Kunne ikke hente data fra Telenor: {e}")

def sjekk_telia():
    """Sjekker Telia basert på en utvidet liste over lokale knutepunkter."""
    print("Sjekker Telia...")
    url = "https://coverage.ddc.teliasonera.net/coverageportal_no/LocationInfo/GetNetworkStatus"
    
    # 10 strategiske knutepunkter for maksimal geografisk nøyaktighet i Troms
    knutepunkter = [
        {"navn": "Tromsø / Kvaløysletta", "lat": "69.6816", "lon": "18.7845"},
        {"navn": "Harstad", "lat": "68.7986", "lon": "16.5414"},
        {"navn": "Finnsnes / Senja", "lat": "69.2305", "lon": "17.9822"},
        {"navn": "Skjervøy", "lat": "70.0311", "lon": "20.9717"},
        {"navn": "Burfjord (Kvænangen)", "lat": "70.0481", "lon": "22.0514"},
        {"navn": "Olderdalen (Kåfjord)", "lat": "69.6035", "lon": "20.5342"},
        {"navn": "Skibotn (Storfjord)", "lat": "69.3917", "lon": "20.2678"},
        {"navn": "Nordkjosbotn (Balsfjord)", "lat": "69.2167", "lon": "19.5667"},
        {"navn": "Karlsøy (Hansnes)", "lat": "69.9667", "lon": "19.6167"},
        {"navn": "Målselv (Bardufoss)", "lat": "69.0642", "lon": "18.5147"}
    ]
    
    for kp in knutepunkter:
        params = {
            "northing": kp["lat"], 
            "easting": kp["lon"],
            "faultCacheKeys": "PW,242_PW_0610230532_639167295320000000,16|AF,242_TT_0611064046_639167568460000000,2",
            "services": "",
            "profile": "ALL",
            "rt": "zDPM7MkxnWTcHmPA2Yj+llf3TKtcJk4eit/yxK7jV0ACfFybKVZpoVwg8iRHx1M74qipBZ2yYKZ6k9Q8n+p0sTYobJdpTZhuhk8UQ/6qehisZV1rmnw8SJPh3mo8zOuHsb9dchasclOb7EficTGd8xnKC/FUtkYxf2JXdW1kRI9pl2QeXx2gHzAV2opVSbetTsOM7XMt3tw+P+ZzjVf5SA=="
        }
        
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data.get("ActiveFaultIds") or data.get("ActiveFaultCells") or data.get("PlannedFaultIds"):
                    msg = f"💜 *TELIA: Mobilutfall registrert i nærområdet til {kp['navn']}!*"
                    send_slack_varsel(msg)
            time.sleep(0.2)
        except Exception as e:
            print(f"Kunne ikke hente data fra Telia for {kp['navn']}: {e}")

def send_slack_varsel(tekst):
    if not SLACK_WEBHOOK_URL:
        print("Feil: Mangler SLACK_TELENOR")
        return
    payload = {"text": tekst}
    try:
        res = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if res.status_code != 200:
            print(f"Slack feilkode: {res.status_code}")
    except Exception as e:
        print(f"Klarte ikke sende til Slack: {e}")

if __name__ == "__main__":
    print("Starter felles tele-sjekk for Troms...")
    sjekk_telenor()
    sjekk_telia()

import os
import json
import requests
from datetime import datetime, timedelta

# Hent Slack-webhook fra miljøvariabler
SLACK_URL = os.getenv("SLACK_BRREG")
API_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"
STATE_FILE = "brreg_state.json"

# Fylkesnummer 55 = Troms fylke
FYLKE_TROMS = "55"

# Liste over alle kommunenummer i Troms (for referanse eller ekstra filtrering)
KOMMUNER_TROMS = [
    "5501", "5503", "5510", "5512", "5514", "5516", "5518", "5520", 
    "5522", "5524", "5526", "5528", "5530", "5532", "5534", "5536", 
    "5538", "5540", "5542", "5544"
]

def last_state():
    """Laster listen over organisasjonsnumre som allerede er varslet."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"varslede_orgnr": []}
    return {"varslede_orgnr": []}

def lagre_state(state):
    """Lagrer oppdatert liste over varslede organisasjonsnumre."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_slack_varsel(tittel, tekst, farge):
    """Sender et strukturert varsel til Slack-kanalen."""
    if not SLACK_URL:
        print(f"Mangler SLACK_BRREG-adresse. Kunne ikke sende: {tittel}")
        return

    payload = {
        "attachments": [
            {
                "fallback": tittel,
                "color": farge,
                "title": tittel,
                "text": tekst,
                "footer": "Brønnøysundregistrene Overvåking",
                "ts": int(datetime.now().timestamp())
            }
        ]
    }
    try:
        res = requests.post(SLACK_URL, json=payload)
        if res.status_code != 200:
            print(f"Slack feilet med status {res.status_code}")
    except Exception as e:
        print(f"Feil under sending til Slack: {e}")

def sjekk_brreg():
    state = last_state()
    nye_varsler = 0

    print("Starter sjekk mot Enhetsregisteret for Troms...")

    # 1. SJEKK KONKURSER
    print("Sjekker konkurser...")
    params_konkurs = {"fylkesnummer": FYLKE_TROMS, "underKonkursbehandling": "true", "size": 100}
    res = requests.get(API_URL, params=params_konkurs)
    if res.status_code == 200:
        enheter = res.json().get("_embedded", {}).get("enheter", [])
        for e in enheter:
            orgnr = e.get("organisasjonsnummer")
            if orgnr not in state["varslede_orgnr"]:
                navn = e.get("navn")
                kommune = e.get("forretningsadresse", {}).get("kommune", "Ukjent kommune")
                tekst = f"🏢 *{navn}* ({orgnr})\n📍 Kommune: {kommune}\n⚠️ Selskapet er nå registrert *under konkursbehandling*."
                send_slack_varsel("🚨 NY KONKURS I TROMS", tekst, "#danger")
                state["varslede_orgnr"].append(orgnr)
                nye_varsler += 1

    # 2. SJEKK TVANGSAVVIKLINGER
    print("Sjekker tvangsavviklinger...")
    params_tvang = {"fylkesnummer": FYLKE_TROMS, "underTvangsavviklingEllerTvangsopplosning": "true", "size": 100}
    res = requests.get(API_URL, params=params_tvang)
    if res.status_code == 200:
        enheter = res.json().get("_embedded", {}).get("enheter", [])
        for e in enheter:
            orgnr = e.get("organisasjonsnummer")
            if orgnr not in state["varslede_orgnr"]:
                navn = e.get("navn")
                kommune = e.get("forretningsadresse", {}).get("kommune", "Ukjent kommune")
                tekst = f"🏢 *{navn}* ({orgnr})\n📍 Kommune: {kommune}\n⚠️ Selskapet er besluttet *tvangsavviklet eller tvangsoppløst* av Myndighetene."
                send_slack_varsel("⚖️ NY TVANGSAVVIKLING I TROMS", tekst, "#warning")
                state["varslede_orgnr"].append(orgnr)
                nye_varsler += 1

    # 3. SJEKK NYETABLERINGER (Siste 3 dager for å være sikker på å fange opp helger/helligdager)
    print("Sjekker nyetableringer...")
    tre_dager_siden = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    params_nye = {"fylkesnummer": FYLKE_TROMS, "fraRegistreringsdatoEnhetsregisteret": tre_dager_siden, "size": 100}
    res = requests.get(API_URL, params=params_nye)
    if res.status_code == 200:
        enheter = res.json().get("_embedded", {}).get("enheter", [])
        for e in enheter:
            orgnr = e.get("organisasjonsnummer")
            if orgnr not in state["varslede_orgnr"]:
                navn = e.get("navn")
                kommune = e.get("forretningsadresse", {}).get("kommune", "Ukjent kommune")
                formål = e.get("institusjonellSektorkode", {}).get("beskrivelse", "Ikke oppgitt")
                tekst = f"🎉 *{navn}* ({orgnr})\n📍 Kommune: {kommune}\n📋 Sektortype: {formål}\n🌱 Selskapet er splitter nytt og nyregistrert i fylket."
                send_slack_varsel("✨ NY ETABLERING I TROMS", tekst, "#good")
                state["varslede_orgnr"].append(orgnr)
                nye_varsler += 1

    # Lagre oppdatert tilstand hvis vi fant noe nytt
    if nye_varsler > 0:
        lagre_state(state)
        print(f"Ferdig! Sendte {nye_varsler} nye varsler og oppdaterte state.")
    else:
        print("Ferdig! Ingen nye endringer funnet i denne timen.")

if __name__ == "__main__":
    sjekk_brreg()

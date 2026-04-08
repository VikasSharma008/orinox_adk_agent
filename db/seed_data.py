"""ORINOX v2 Seed Data — Run: python -m db.seed_data"""
import asyncio, random
from db.database import get_db

CLIENTS = [
    {"name":"Priya Sharma","email":"priya.sharma@email.com","phone":"+91-9820100001","risk_profile":"aggressive","channel_preference":"email","occupation":"Tech Executive","city":"Mumbai","aum":8500000,"date_of_birth":"1985-03-15"},
    {"name":"Rajesh Patel","email":"rajesh.patel@email.com","phone":"+91-9820100002","risk_profile":"conservative","channel_preference":"email","occupation":"Retired Banker","city":"Mumbai","aum":12000000,"date_of_birth":"1958-07-22"},
    {"name":"Ananya Desai","email":"ananya.desai@email.com","phone":"+91-9820100003","risk_profile":"moderate","channel_preference":"email","occupation":"Doctor","city":"Pune","aum":6200000,"date_of_birth":"1978-11-08"},
    {"name":"Vikram Mehta","email":"vikram.mehta@email.com","phone":"+91-9820100004","risk_profile":"aggressive","channel_preference":"email","occupation":"Real Estate Developer","city":"Mumbai","aum":25000000,"date_of_birth":"1972-01-30"},
    {"name":"Sunita Reddy","email":"sunita.reddy@email.com","phone":"+91-9820100005","risk_profile":"moderate","channel_preference":"email","occupation":"Business Owner","city":"Nashik","aum":4800000,"date_of_birth":"1980-05-12"},
    {"name":"Amit Kulkarni","email":"amit.kulkarni@email.com","phone":"+91-9820100006","risk_profile":"conservative","channel_preference":"email","occupation":"Professor","city":"Mumbai","aum":3500000,"date_of_birth":"1965-09-18"},
    {"name":"Deepika Joshi","email":"deepika.joshi@email.com","phone":"+91-9820100007","risk_profile":"aggressive","channel_preference":"email","occupation":"Startup Founder","city":"Mumbai","aum":15000000,"date_of_birth":"1990-02-28"},
    {"name":"Mohan Nair","email":"mohan.nair@email.com","phone":"+91-9820100008","risk_profile":"conservative","channel_preference":"email","occupation":"Government Officer","city":"Thane","aum":5500000,"date_of_birth":"1960-12-05"},
    {"name":"Kavita Singh","email":"kavita.singh@email.com","phone":"+91-9820100009","risk_profile":"moderate","channel_preference":"email","occupation":"Lawyer","city":"Mumbai","aum":7200000,"date_of_birth":"1982-06-20"},
    {"name":"Arjun Banerjee","email":"arjun.banerjee@email.com","phone":"+91-9820100010","risk_profile":"aggressive","channel_preference":"email","occupation":"Film Producer","city":"Mumbai","aum":30000000,"date_of_birth":"1975-04-10"},
    {"name":"Neha Gupta","email":"neha.gupta@email.com","phone":"+91-9820100011","risk_profile":"moderate","channel_preference":"email","occupation":"CA","city":"Pune","aum":6800000,"date_of_birth":"1984-08-14"},
    {"name":"Sanjay Iyer","email":"sanjay.iyer@email.com","phone":"+91-9820100012","risk_profile":"aggressive","channel_preference":"email","occupation":"IT Consultant","city":"Mumbai","aum":9500000,"date_of_birth":"1979-10-25"},
]

BONDS = [
    {"instrument_name":"SBI Bond Fund","instrument_type":"debt_fund","sector":"banking"},
    {"instrument_name":"ICICI Corp Bond","instrument_type":"bond","sector":"banking"},
    {"instrument_name":"Govt of India 10Y Bond","instrument_type":"government_bond","sector":"sovereign"},
    {"instrument_name":"HDFC Short Term Debt","instrument_type":"debt_fund","sector":"banking"},
]
EQUITIES = [
    {"instrument_name":"Reliance Industries","instrument_type":"equity","sector":"energy"},
    {"instrument_name":"TCS","instrument_type":"equity","sector":"IT"},
    {"instrument_name":"Infosys","instrument_type":"equity","sector":"IT"},
    {"instrument_name":"HDFC Bank","instrument_type":"equity","sector":"banking"},
    {"instrument_name":"Bharti Airtel","instrument_type":"equity","sector":"telecom"},
    {"instrument_name":"Adani Enterprises","instrument_type":"equity","sector":"infrastructure"},
    {"instrument_name":"Wipro","instrument_type":"equity","sector":"IT"},
    {"instrument_name":"Axis Bank","instrument_type":"equity","sector":"banking"},
]
REALESTATE = [
    {"instrument_name":"Godrej Properties","instrument_type":"equity","sector":"real_estate"},
    {"instrument_name":"DLF Ltd","instrument_type":"equity","sector":"real_estate"},
    {"instrument_name":"Embassy REIT","instrument_type":"reit","sector":"real_estate"},
]
MFS = [
    {"instrument_name":"Mirae Asset Large Cap","instrument_type":"mutual_fund","sector":"diversified"},
    {"instrument_name":"Parag Parikh Flexi Cap","instrument_type":"mutual_fund","sector":"diversified"},
    {"instrument_name":"Kotak IT Sector Fund","instrument_type":"mutual_fund","sector":"IT"},
    {"instrument_name":"Nippon India Banking Fund","instrument_type":"mutual_fund","sector":"banking"},
]

HOUSEHOLDS = [
    {"member_name":"Rohit Sharma","relationship":"spouse","occupation":"Architect"},
    {"member_name":"Aarav Sharma","relationship":"child","date_of_birth":"2012-06-15"},
    {"member_name":"Meera Patel","relationship":"spouse","occupation":"Homemaker"},
    {"member_name":"Ravi Patel","relationship":"child","occupation":"Student"},
    {"member_name":"Dr. Kiran Desai","relationship":"spouse","occupation":"Surgeon"},
    {"member_name":"Isha Desai","relationship":"child","date_of_birth":"2010-03-20"},
    {"member_name":"Sneha Mehta","relationship":"spouse","occupation":"Interior Designer"},
]

def _make_portfolio(client):
    aum, risk = client.get("aum",5000000), client.get("risk_profile","moderate")
    h = []
    def _add(pool, n, lo, hi):
        for item in random.sample(pool, min(n,len(pool))):
            v = round(random.uniform(lo,hi)*aum)
            h.append({**item, "current_value":v, "quantity":round(v/1000), "avg_cost":round(v*random.uniform(0.7,1.1))})
    if risk == "conservative":
        _add(BONDS,3,0.1,0.3); _add(MFS,2,0.05,0.15)
    elif risk == "aggressive":
        _add(EQUITIES,4,0.08,0.25); _add(REALESTATE,2,0.05,0.15); _add(MFS,2,0.05,0.1)
    else:
        _add(BONDS,2,0.08,0.2); _add(EQUITIES,3,0.05,0.15); _add(MFS,2,0.05,0.15)
    total = sum(x["current_value"] for x in h)
    for x in h:
        x["allocation_pct"] = round(x["current_value"]/total*100,1) if total else 0
    return h

async def seed():
    db = await get_db()
    print("Seeding ORINOX v2...")
    ids = []
    for c in CLIENTS:
        r = await db.upsert_client(c)
        ids.append(r["id"])
        print(f"  Client: {c['name']}")

    for i, cid in enumerate(ids):
        port = _make_portfolio(CLIENTS[i])
        for h in port:
            h["client_id"] = cid
            await db.upsert_portfolio(h)
        print(f"  Portfolio: {CLIENTS[i]['name']} — {len(port)} holdings")

    for i, m in enumerate(HOUSEHOLDS):
        if i < len(ids):
            m["client_id"] = ids[i]
            await db.add_household_member(m)

    subjects = ["Quarterly review","Tax planning","Fund recommendation","Market update","Birthday wishes","Risk follow-up"]
    for i, cid in enumerate(ids[:8]):
        for _ in range(random.randint(2,4)):
            await db.log_interaction({"client_id":cid,"interaction_type":random.choice(["call","email","meeting"]),
                "channel":"email","subject":random.choice(subjects),"summary":"Discussed portfolio and opportunities.",
                "direction":random.choice(["outbound","inbound"]),"logged_by":"vikram"})

    print(f"Done: {len(ids)} clients seeded.")

if __name__ == "__main__":
    asyncio.run(seed())

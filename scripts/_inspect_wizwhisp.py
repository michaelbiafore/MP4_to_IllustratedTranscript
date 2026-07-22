import sqlite3, json

db = r"C:\Users\biafo\AppData\Local\Packages\49657NowSmartStudio.WizScribe_agnvvc9c4qtza\LocalCache\Local\WizWhisp\TaskHistory.db"
c = sqlite3.connect(db)
cur = c.cursor()
cur.execute("SELECT ResultItemsJson FROM TaskHistory WHERE Id=25")
raw = cur.fetchone()[0]
data = json.loads(raw)
print("TYPE:", type(data))
if isinstance(data, list):
    print("COUNT:", len(data))
    print("FIRST ITEM:", json.dumps(data[0], indent=2)[:800])
    print("LAST ITEM:", json.dumps(data[-1], indent=2)[:800])
elif isinstance(data, dict):
    print("KEYS:", list(data.keys()))
    print(json.dumps(data, indent=2)[:1200])

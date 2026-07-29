"""
test_app.py
Automated tests for Lumé Sprint 1.
Run with: python test_app.py
These check that registration, login, profile saving and password
security all work as expected.
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists("lume.db"):
    os.remove("lume.db")

import app as flaskapp
flaskapp.app.config["TESTING"] = True
client = flaskapp.app.test_client()

results = []

r = client.get("/")
results.append(("home loads", r.status_code == 200))

r = client.post("/register", data={"email": "test@lume.com", "password": "lume123", "confirm": "lume123"}, follow_redirects=True)
results.append(("register then profile", r.status_code == 200 and b"My Skin Profile" in r.data))

r = client.post("/profile", data={"skin_type": "Oily", "age": "34", "concerns": "dark spots", "sensitivities": "fragrance", "climate": "Cool & humid"}, follow_redirects=True)
results.append(("save profile", b"has been saved" in r.data))

r = client.get("/logout", follow_redirects=True)
results.append(("logout", r.status_code == 200))

r = client.post("/login", data={"email": "test@lume.com", "password": "lume123"}, follow_redirects=True)
results.append(("login works", b"My Skin Profile" in r.data))

r = client.post("/login", data={"email": "test@lume.com", "password": "wrong"}, follow_redirects=True)
results.append(("bad login blocked", b"Wrong email or password" in r.data))

import database
u = database.get_user_by_email("test@lume.com")
results.append(("password is hashed", u["password_hash"] != "lume123" and len(u["password_hash"]) > 20))

print("\n=== TEST RESULTS ===")
allpass = all(ok for _, ok in results)
for name, ok in results:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
print("=== " + ("ALL PASSED" if allpass else "SOME FAILED") + " ===")

# Montgomery County, MD - Real Data Setup

How to search **real** Montgomery County property records.

## 🎯 Goal

Search for actual property records like:
- **8617 Grant St, Bethesda, MD 20817**
- Any other Montgomery County address

## 📋 Prerequisites

You need **free access** to Maryland Land Records system.

---

## Step 1: Register for MDLandRec Access

### **1.1 Visit the Registration Page**

Go to: **https://landrec.msa.maryland.gov**

### **1.2 Create an Account**

Click "Register" or "Create Account"

**You'll need:**
- ✉️ Valid email address
- 🔑 Strong password
- 📝 Basic contact information

### **1.3 Wait for Approval**

- ⏱️ **Approval time**: Usually 1-2 hours (business days)
- 📧 **You'll get an email** when approved
- 💵 **Cost**: FREE (no payment required!)

---

## Step 2: Test Your Credentials

### **2.1 Log in Manually**

Visit: https://landrec.msa.maryland.gov

1. Click "Login"
2. Enter your email and password
3. Verify you can access the system

### **2.2 Try a Manual Search**

1. Select "Montgomery" county
2. Search for "Grant St"
3. Verify you see results

If this works, you're ready!

---

## Step 3: Add Credentials to TitleChain

### **3.1 Open Your .env File**

```bash
nano /Users/harit/AI\ Projects/TitleChain/.env
```

### **3.2 Add These Lines**

```bash
# Montgomery County MD Credentials
MONTGOMERY_MD_EMAIL=your-actual-email@example.com
MONTGOMERY_MD_PASSWORD=your-actual-password
```

**⚠️ IMPORTANT:**
- Use the SAME email/password from MDLandRec
- No quotes needed
- Save the file (Ctrl+O, Enter, Ctrl+X)

### **3.3 Restart the Server**

```bash
# Stop the current server (Ctrl+C in the terminal where it's running)

# Start it again
cd /Users/harit/AI\ Projects/TitleChain/backend
source ../venv/bin/activate
python app.py
```

---

## Step 4: Search 8617 Grant St (REAL DATA)

### **4.1 Using Python**

```python
import requests
import json

response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "property_address": "8617 Grant St Bethesda MD 20817",
        "counties": [{"county": "Montgomery", "state": "MD"}],
        "years_back": 60,
        "credentials": {
            "montgomery_md": {
                "email": "your-email@example.com",  # Your MDLandRec email
                "password": "your-password"          # Your MDLandRec password
            }
        }
    }
)

result = response.json()
print(json.dumps(result, indent=2))

# Get full results
search_id = result['search_id']
details = requests.get(f"http://localhost:8000/agent/search/{search_id}")
print(json.dumps(details.json(), indent=2))
```

### **4.2 What You'll Get**

The agent will:

1. **Log into MDLandRec** using your credentials
2. **Search Montgomery County** for "8617 Grant St"
3. **Scrape the results** from the website
4. **Parse the data** into clean JSON
5. **Return all documents** found for that address

**Response includes:**
- All deeds (ownership history)
- All mortgages
- All liens
- Recording dates
- Book/page numbers
- Grantor/grantee names
- Sale prices

**Time:** ~3-10 seconds

---

## 📊 What Results Look Like

### **Successful Search:**

```json
{
  "search_id": "abc123...",
  "status": "completed",
  "counties_searched": 1,
  "counties_succeeded": 1,
  "total_documents": 12,
  "documents": [
    {
      "document_type": "deed",
      "recording_date": "2015-06-15T00:00:00",
      "grantor": ["Smith, John A", "Smith, Mary B"],
      "grantee": ["Johnson, Robert C"],
      "property_address": "8617 Grant St, Bethesda, MD",
      "consideration": 750000.0,
      "book": "45678",
      "page": "123",
      "instrument_number": "2015-0045678"
    },
    {
      "document_type": "mortgage",
      "recording_date": "2015-06-15T00:00:00",
      "grantor": ["Johnson, Robert C"],
      "grantee": ["Wells Fargo Bank"],
      "consideration": 600000.0,
      "book": "45678",
      "page": "130"
    },
    ...
  ]
}
```

This tells the story:
1. **2015:** John & Mary Smith sold to Robert Johnson for $750k
2. **2015:** Robert Johnson took out a $600k mortgage with Wells Fargo
3. (And so on...)

---

## 🔍 Alternative: Find the Parcel Number

If you want even more accurate results, get the **parcel number**:

### **Method 1: Montgomery County Property Search**

1. Visit: https://www.montgomerycountymd.gov/SDAT/
2. Search for "8617 Grant St"
3. Get the parcel number (format: XX-XXXXXXX)

### **Method 2: Maryland SDAT**

1. Visit: https://sdat.dat.maryland.gov/RealProperty/
2. Select "Montgomery County"
3. Enter "Grant St" and street number "8617"
4. Get parcel number from results

### **Then Search by Parcel:**

```python
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "parcel_number": "XX-XXXXXXX",  # From SDAT
        "counties": [{"county": "Montgomery", "state": "MD"}],
        "years_back": 60,
        "credentials": {
            "montgomery_md": {
                "email": "your-email@example.com",
                "password": "your-password"
            }
        }
    }
)
```

**Parcel search is:**
- ✅ More accurate
- ✅ Faster
- ✅ No fuzzy address matching needed

---

## ⚠️ Common Issues

### **Issue: "Authentication failed"**

**Causes:**
1. Account not approved yet (wait 1-2 hours)
2. Wrong email/password
3. Account expired (inactive for 90+ days)

**Solutions:**
1. Test login at https://landrec.msa.maryland.gov manually
2. Check `.env` file for typos
3. Re-register if account expired

### **Issue: "No documents found"**

**Possible reasons:**
1. Address doesn't exist in Montgomery County
2. Property too new (built after search window)
3. Address formatted differently in records

**Solutions:**
1. Try searching by parcel number instead
2. Try different address formats:
   - "8617 Grant St"
   - "8617 Grant Street"
   - "Grant St, Bethesda"
3. Expand `years_back` to 100

### **Issue: "Rate limit exceeded"**

**Cause:** Too many searches too quickly

**Solution:** Wait 5-10 minutes and try again

---

## 🚀 Quick Start Script

Save this as `test_montgomery.py`:

```python
#!/usr/bin/env python3
"""Test Montgomery County real data search"""

import requests
import json
import os

# Get credentials from environment (or hardcode for testing)
EMAIL = os.getenv("MONTGOMERY_MD_EMAIL", "your-email@example.com")
PASSWORD = os.getenv("MONTGOMERY_MD_PASSWORD", "your-password")

def search_montgomery(address):
    """Search Montgomery County for an address"""

    print(f"🔍 Searching: {address}")
    print(f"📧 Using account: {EMAIL}\n")

    # Start search
    response = requests.post(
        "http://localhost:8000/agent/search",
        json={
            "property_address": address,
            "counties": [{"county": "Montgomery", "state": "MD"}],
            "years_back": 60,
            "credentials": {
                "montgomery_md": {
                    "email": EMAIL,
                    "password": PASSWORD
                }
            }
        }
    )

    result = response.json()
    search_id = result.get('search_id')

    print(f"✅ Search Status: {result.get('status')}")
    print(f"📊 Documents Found: {result.get('total_documents')}\n")

    if result.get('total_documents', 0) > 0:
        # Get full results
        details = requests.get(
            f"http://localhost:8000/agent/search/{search_id}"
        )

        docs = details.json().get('documents', [])

        print("📄 DOCUMENTS:\n")
        for i, doc in enumerate(docs, 1):
            print(f"{i}. {doc['document_type'].upper()}")
            print(f"   Date: {doc.get('recording_date', 'N/A')}")
            print(f"   From: {', '.join(doc.get('grantor', []))}")
            print(f"   To: {', '.join(doc.get('grantee', []))}")
            if doc.get('consideration'):
                print(f"   Amount: ${doc['consideration']:,.0f}")
            print()

    return result

if __name__ == "__main__":
    # Test with Bethesda address
    search_montgomery("8617 Grant St Bethesda MD 20817")
```

**Run it:**
```bash
chmod +x test_montgomery.py
./test_montgomery.py
```

---

## 📚 Next Steps

1. ✅ **Register** at MDLandRec (do this now!)
2. ⏱️ **Wait** for approval (1-2 hours)
3. 🔑 **Add credentials** to `.env`
4. 🧪 **Test** with 8617 Grant St
5. 🚀 **Search** any Montgomery County property!

---

## 💡 Pro Tips

1. **Batch searches**: Search multiple addresses in one request
2. **Cache results**: 2nd search of same address is instant
3. **Save search IDs**: You can retrieve results later
4. **Use parcel numbers**: More accurate than addresses
5. **Check SDAT first**: Verify property exists before searching

---

**Once set up, you can search any Montgomery County property in 3-10 seconds!** 🚀

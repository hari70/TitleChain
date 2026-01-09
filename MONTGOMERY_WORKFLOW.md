# Montgomery County, MD - Complete Search Workflow

## Understanding Maryland's Two Systems

Montgomery County property records require **two different websites**:

### **1. SDAT (State Department of Assessments and Taxation)**
- **URL**: https://sdat.dat.maryland.gov/RealProperty/
- **Purpose**: Address → Parcel Number lookup, Owner information
- **Search By**: Address, Owner Name, Account Number
- **No Login Required**: Public access
- **What You Get**: Parcel numbers, current owner names, property details

### **2. MDLandRec (Maryland Land Records)**
- **URL**: https://landrec.msa.maryland.gov
- **Purpose**: Historical deed documents, mortgages, liens
- **Search By**: Owner Name (first/last), Organization Name, Book/Page
- **Requires Login**: Free account with approval (~1 hour)
- **What You Get**: Scanned deed images, recording dates, grantor/grantee info

---

## 🔄 Complete Search Workflow

To search by **property address** (like "8617 Grant St, Bethesda, MD 20817"):

### **Step 1: Use SDAT to Get Owner Name + Parcel**

1. Visit https://sdat.dat.maryland.gov/RealProperty/
2. Select "Montgomery" from county dropdown
3. Click "Search by Address"
4. Enter:
   - Street Number: `8617`
   - Street Name: `Grant`
5. Click "Search"

**What you'll get:**
- **Parcel Number** (e.g., "03-01234567")
- **Current Owner Name** (e.g., "Smith, John A")
- **Account Number**
- Property details (year built, square footage, etc.)

### **Step 2: Use MDLandRec with Owner Name**

1. Visit https://landrec.msa.maryland.gov
2. Log in with your credentials
3. Select "Montgomery County"
4. Choose "Search by Name"
5. Enter the **owner's last name** from SDAT (e.g., "Smith")
6. Optional: Add first name to narrow results

**What you'll get:**
- All deeds where "Smith" is grantor or grantee
- Mortgage documents
- Liens
- Historical ownership transfers
- Recording dates and book/page references

---

## 🤖 Automated Workflow (Future Enhancement)

To fully automate address searches, we need:

```
User Input: "8617 Grant St Bethesda MD"
       ↓
Step 1: SDAT Connector
       ↓
Extract: Parcel="03-01234567", Owner="Smith, John A"
       ↓
Step 2: MDLandRec Connector
       ↓
Search by: LastName="Smith"
       ↓
Filter by: Parcel="03-01234567" (from document data)
       ↓
Return: All relevant documents
```

---

## 📋 Current TitleChain Implementation

### **What Works Now:**

✅ **Search by Owner Name** on MDLandRec:
```python
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "current_owner": "Smith",  # Last name from SDAT
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

### **What Doesn't Work Yet:**

❌ **Direct Address Search** - returns empty results because MDLandRec doesn't support it
```python
# This won't work:
{"property_address": "8617 Grant St"}
```

### **Workaround Until SDAT Integration:**

**Manual 2-Step Process:**
1. Look up owner name on SDAT website manually
2. Search by that owner name in TitleChain

**Example:**
```python
# Step 1: Go to SDAT, find owner = "Smith, John A"

# Step 2: Search in TitleChain
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "current_owner": "Smith",
        "counties": [{"county": "Montgomery", "state": "MD"}],
        "years_back": 60
    }
)
```

---

## 🚀 Future Enhancement: SDAT Connector

To enable true address-based search, we need to add:

### **backend/agents/sdat_md.py**
```python
class SDATConnector:
    """Maryland SDAT (property assessment) connector"""

    async def lookup_by_address(self, address: str) -> PropertyInfo:
        """
        Search SDAT for property information.

        Returns:
            PropertyInfo with:
            - parcel_number
            - current_owner_name
            - account_number
            - property_details
        """
        # Scrape SDAT website
        # Parse results
        # Return structured data
```

### **Updated Search Flow:**
```python
class SearchAgent:
    async def search(self, request):
        if request.property_address:
            # NEW: Look up owner via SDAT
            sdat = SDATConnector()
            property_info = await sdat.lookup_by_address(request.property_address)

            # Use owner name for MDLandRec
            owner_name = property_info.current_owner_name
            request.current_owner = owner_name
            request.parcel_number = property_info.parcel_number

        # Continue with existing MDLandRec search
        results = await self._search_mdlandrec(request)
```

---

## 📊 Comparison: SDAT vs MDLandRec

| Feature | SDAT | MDLandRec |
|---------|------|-----------|
| **Search by Address** | ✅ Yes | ❌ No |
| **Search by Name** | ✅ Yes | ✅ Yes (Primary) |
| **Search by Parcel** | ✅ Yes | ⚠️ Limited |
| **Current Owner** | ✅ Yes | ❌ No |
| **Historical Deeds** | ❌ No | ✅ Yes |
| **Document Images** | ❌ No | ✅ Yes |
| **Mortgages/Liens** | ❌ No | ✅ Yes |
| **Login Required** | ❌ No | ✅ Yes |
| **API Available** | ❌ No | ❌ No |
| **Data Format** | HTML tables | HTML + embedded images |

---

## 🧪 Testing Guide

### **Test 1: Search by Owner Name (Works Now)**

```bash
curl -X POST http://localhost:8000/agent/search \
  -H "Content-Type: application/json" \
  -d '{
    "current_owner": "Smith",
    "counties": [{"county": "Montgomery", "state": "MD"}],
    "years_back": 60,
    "credentials": {
      "montgomery_md": {
        "email": "your-email@example.com",
        "password": "your-password"
      }
    }
  }'
```

### **Test 2: Address Search (Needs SDAT)**

**Current behavior:** Returns no results
**Future behavior:** Will auto-lookup owner via SDAT, then search MDLandRec

---

## 💡 Recommendations

### **For Immediate Use:**

1. **Manual SDAT Lookup**: Look up owner name on SDAT first
2. **Search by Name**: Use TitleChain with owner name
3. **Document**: Save the owner name with the parcel for future searches

### **For Production Deployment:**

1. **Add SDAT Connector**: Enable automatic address → owner lookup
2. **Cache SDAT Results**: Store parcel → owner mappings
3. **Parallel Search**: Query SDAT and MDLandRec simultaneously
4. **Link Results**: Match MDLandRec documents to SDAT parcels

### **Alternative Approach:**

Instead of real-time scraping, consider:
- **Bulk Data Purchase**: Maryland offers bulk land records data
- **API Services**: Third-party APIs like DataTree, CoreLogic
- **County Partnerships**: Direct data feed agreements

---

## 🎯 Summary

**Current State:**
- ✅ MDLandRec connector works for name-based searches
- ❌ Address search not supported (MDLandRec limitation)
- ⚠️ Manual SDAT lookup required for address → name conversion

**Next Priority:**
- Add SDAT connector for automatic address lookups
- Enable seamless address-based searching
- Link SDAT property info with MDLandRec documents

**Timeline:**
- SDAT connector: ~4-6 hours development
- Testing: ~2 hours
- Documentation: ~1 hour
- **Total**: ~1 day to enable full address search

---

Need help implementing the SDAT connector? Let me know!

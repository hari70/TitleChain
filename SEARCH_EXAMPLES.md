# TitleChain Search Examples

Complete guide to all the ways you can search for property records.

## 🔍 Search Methods

The Search Agent supports **4 different ways** to search:

1. ✅ **By Parcel Number** (Most accurate)
2. ✅ **By Property Address** (Most common)
3. ✅ **By Owner Name** (Find all properties owned by someone)
4. ✅ **By Document Reference** (Book/page or instrument number)

---

## 📋 Example 1: Search by Property Address

**Use when:** You know the street address

```python
import requests

response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "property_address": "123 Main Street",
        "counties": [{"county": "Montgomery", "state": "MD"}],
        "years_back": 60
    }
)

print(response.json())
```

**cURL version:**
```bash
curl -X POST http://localhost:8000/agent/search \
  -H "Content-Type: application/json" \
  -d '{
    "property_address": "123 Main Street",
    "counties": [{"county": "Montgomery", "state": "MD"}],
    "years_back": 60
  }'
```

**What happens:**
1. Agent searches Montgomery County for "123 Main Street"
2. Finds all documents for that address
3. Returns deeds, mortgages, liens, etc.

---

## 📋 Example 2: Search by Parcel Number

**Use when:** You have the tax parcel ID (most accurate!)

```python
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "parcel_number": "12-345-6789",
        "counties": [{"county": "Los Angeles", "state": "CA"}],
        "years_back": 60
    }
)
```

**Why use parcel number:**
- ✅ More accurate than address
- ✅ No confusion with similar addresses
- ✅ Every property has unique parcel ID

**Where to find parcel numbers:**
- County assessor website
- Property tax statements
- Title reports

---

## 📋 Example 3: Search by Owner Name

**Use when:** Finding all properties owned by someone

```python
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "current_owner": "John Smith",
        "counties": [
            {"county": "Montgomery", "state": "MD"},
            {"county": "Howard", "state": "MD"}
        ],
        "years_back": 30
    }
)
```

**What you get:**
- All properties where "John Smith" is listed as grantee
- Across multiple counties
- For the last 30 years

**Note:** Name matching is fuzzy, so "John Smith" will also find "John M. Smith", "Smith, John", etc.

---

## 📋 Example 4: Multi-County Search

**Use when:** Property might be in multiple counties

```python
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "property_address": "123 Main St",
        "counties": [
            {"county": "Montgomery", "state": "MD"},
            {"county": "Prince George's", "state": "MD"},
            {"county": "Howard", "state": "MD"}
        ],
        "years_back": 60
    }
)
```

**Benefits:**
- ✅ Searches 3 counties **in parallel** (~5 seconds total)
- ✅ Combines results automatically
- ✅ Shows which county each document came from

---

## 📋 Example 5: Comprehensive Search

**Use when:** You want **everything**

```python
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "parcel_number": "12-345-6789",
        "property_address": "123 Main Street",  # Belt & suspenders approach
        "current_owner": "Alice Smith",
        "counties": [{"county": "Montgomery", "state": "MD"}],
        "years_back": 60,
        "include_mortgages": True,
        "include_liens": True,
        "include_easements": True,
        "retrieve_images": False,  # Set to True to get PDF/images
        "max_documents": 1000
    }
)
```

**This searches for:**
- Parcel "12-345-6789" OR
- Address "123 Main Street" OR
- Owner "Alice Smith"

Returns **all matches** across all criteria.

---

## 📋 Example 6: Real Montgomery County Search

**Use when:** Testing with real data

**Prerequisites:**
1. Register at https://landrec.msa.maryland.gov
2. Get your email/password approved (~1 hour)
3. Add to `.env` file

```python
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "property_address": "REAL_ADDRESS_IN_MONTGOMERY_COUNTY",
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

**Time:** 3-10 seconds depending on document count

---

## 🎯 Search Parameter Reference

### **Required Parameters**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `counties` | Array | List of counties to search | `[{"county": "Montgomery", "state": "MD"}]` |

### **Search Criteria (At least one required)**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `parcel_number` | String | Property tax parcel ID | `"12-345-6789"` |
| `property_address` | String | Street address | `"123 Main St"` |
| `current_owner` | String | Owner name to search | `"John Smith"` |

### **Optional Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `years_back` | Integer | 60 | How many years of history |
| `include_mortgages` | Boolean | True | Include mortgage docs |
| `include_liens` | Boolean | True | Include lien docs |
| `include_easements` | Boolean | True | Include easements |
| `retrieve_images` | Boolean | False | Download PDF/images |
| `max_documents` | Integer | 1000 | Max results to return |

### **Credentials (Optional)**

Only needed for real county access:

```python
"credentials": {
    "montgomery_md": {
        "email": "user@example.com",
        "password": "password123"
    }
}
```

---

## 📊 Understanding the Response

### **Immediate Response**

When you POST to `/agent/search`:

```json
{
  "search_id": "abc123...",
  "status": "completed",
  "started_at": "2026-01-08T14:00:00Z",
  "completed_at": "2026-01-08T14:00:03Z",
  "counties_searched": 3,
  "counties_succeeded": 3,
  "counties_failed": 0,
  "total_documents": 15
}
```

### **Full Results**

GET `/agent/search/{search_id}`:

```json
{
  "search_id": "abc123...",
  "status": "completed",
  "total_documents": 15,
  "documents": [
    {
      "document_id": "mock-001",
      "county": "Montgomery",
      "state": "MD",
      "document_type": "deed",
      "recording_date": "2024-03-15T00:00:00",
      "grantor": ["John Doe", "Jane Doe"],
      "grantee": ["Alice Smith"],
      "consideration": 500000.0,
      "property_address": "123 Main St",
      "parcel_number": "12-345-6789"
    },
    ...
  ]
}
```

### **Document Types**

| Type | Meaning |
|------|---------|
| `deed` | Ownership transfer |
| `mortgage` | Loan secured by property |
| `lien` | Debt claim against property |
| `release` | Mortgage/lien paid off |
| `easement` | Right to use property |
| `plat` | Subdivision map |
| `judgment` | Court-ordered lien |

---

## 🚀 Advanced Examples

### **Example: Find All Properties Owned by Someone**

```python
# Find every property John Smith owns in Maryland
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "current_owner": "John Smith",
        "counties": [
            {"county": "Montgomery", "state": "MD"},
            {"county": "Prince George's", "state": "MD"},
            {"county": "Anne Arundel", "state": "MD"},
            {"county": "Baltimore", "state": "MD"}
        ],
        "years_back": 100,  # Full history
        "max_documents": 5000
    }
)

# This searches 4 counties in parallel!
```

### **Example: Chain of Title Research**

```python
# Get complete ownership history for a property
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "parcel_number": "12-345-6789",
        "counties": [{"county": "Montgomery", "state": "MD"}],
        "years_back": 60,  # Title insurance typically requires 60 years
        "include_mortgages": True,
        "include_liens": True,
        "include_easements": True
    }
)

# Agent will find:
# - All deeds (ownership transfers)
# - All mortgages (loans)
# - All liens (debts)
# - All easements (usage rights)
```

### **Example: Pre-Purchase Due Diligence**

```python
# Before buying a property, check everything
response = requests.post(
    "http://localhost:8000/agent/search",
    json={
        "property_address": "123 Main St, Rockville, MD",
        "current_owner": "Current Seller Name",  # Belt & suspenders
        "counties": [{"county": "Montgomery", "state": "MD"}],
        "years_back": 60,
        "include_mortgages": True,  # Check for unpaid loans
        "include_liens": True,      # Check for tax liens, mechanic liens
        "include_easements": True,  # Check for utility easements
        "retrieve_images": True     # Get actual documents
    }
)

# Review all documents before closing!
```

---

## ⚡ Performance Tips

### **Faster Searches**

1. **Use Parcel Number**: Most accurate, fastest lookup
2. **Limit Years**: `years_back: 30` instead of 60 if you don't need full history
3. **Skip Images**: Set `retrieve_images: False` unless you need PDFs
4. **Use Cache**: Run same search twice → 2nd is instant (cached)

### **Parallel Searches**

The agent automatically searches multiple counties in parallel:

```python
# This searches 5 counties simultaneously (not sequentially!)
"counties": [
    {"county": "Montgomery", "state": "MD"},
    {"county": "Howard", "state": "MD"},
    {"county": "Baltimore", "state": "MD"},
    {"county": "Anne Arundel", "state": "MD"},
    {"county": "Prince George's", "state": "MD"}
]
```

**Time:** ~5 seconds (not 25 seconds!)

---

## 🐛 Troubleshooting

### **"No documents found"**

**Possible reasons:**
1. Wrong county (check property location)
2. Typo in address/parcel number
3. Property too new (not in 60-year window)
4. County system temporarily down

**Solution:**
- Try different search criteria
- Expand `years_back`
- Check county website manually

### **"County not supported"**

**Solution:**
```bash
# Check which counties are available
curl http://localhost:8000/agent/counties
```

Currently implemented:
- ✅ Montgomery, MD (real data)
- ✅ Los Angeles, CA (mock data)
- ✅ Cook, IL (mock data)

### **"Authentication failed"**

**For Montgomery County:**
1. Verify credentials at https://landrec.msa.maryland.gov
2. Wait ~1 hour after registration
3. Check `.env` file has correct email/password

---

## 📚 Next Steps

1. **Try the examples above** - Start with mock searches
2. **Register for Montgomery County** - Get real data access
3. **Test parallel searches** - See the speed difference
4. **Review the results** - Understand what each document means

---

**Happy Searching!** 🔍

You can now search property records across multiple counties in seconds!

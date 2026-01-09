#!/usr/bin/env python3
"""
Test actual MDLandRec search workflow - Navigate properly through the site.
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

async def test_mdlandrec_navigation():
    """Test full navigation through MDLandRec."""

    email = os.getenv('MONTGOMERY_MD_EMAIL')
    password = os.getenv('MONTGOMERY_MD_PASSWORD')

    if not email or not password:
        print("❌ No credentials found in .env file")
        return

    print(f"🔐 Using email: {email}")
    print()

    BASE_URL = "https://landrec.msa.maryland.gov"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:

        # Step 1: Login
        print("🔑 Step 1: Logging in...")
        LOGIN_URL = f"{BASE_URL}/Account/Login"

        response = await client.get(LOGIN_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        csrf_token = token_input.get('value') if token_input else None

        login_data = {
            "Email": email,
            "Password": password,
            "RememberMe": "false"
        }
        if csrf_token:
            login_data["__RequestVerificationToken"] = csrf_token

        response = await client.post(LOGIN_URL, data=login_data)

        if "Invalid" in response.text or "incorrect" in response.text.lower():
            print("   ❌ Login failed")
            return

        print("   ✅ Login successful")
        print()

        # Step 2: Go to home/search page
        print("📄 Step 2: Loading search page...")
        SEARCH_PAGE_URL = f"{BASE_URL}/Pages/Search.aspx"

        response = await client.get(SEARCH_PAGE_URL)
        print(f"   Status: {response.status_code}")

        # Save the search page
        Path("debug_search_page.html").write_text(response.text)
        print("   💾 Saved to: debug_search_page.html")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for county selector
        print()
        print("🔍 Step 3: Analyzing search form...")

        # Find all select elements
        selects = soup.find_all('select')
        print(f"   Found {len(selects)} select dropdowns")
        for select in selects:
            name = select.get('name', 'unknown')
            id_attr = select.get('id', 'unknown')
            options = select.find_all('option')
            print(f"      - {name} (id={id_attr}): {len(options)} options")
            if 'county' in name.lower() or 'county' in id_attr.lower():
                print(f"        COUNTY SELECTOR: {[opt.text.strip() for opt in options[:5]]}")

        # Find text inputs
        inputs = soup.find_all('input', {'type': 'text'})
        print(f"   Found {len(inputs)} text inputs")
        for inp in inputs[:10]:
            name = inp.get('name', 'unknown')
            id_attr = inp.get('id', 'unknown')
            placeholder = inp.get('placeholder', '')
            print(f"      - {name} (id={id_attr}) placeholder='{placeholder}'")

        # Find submit buttons
        buttons = soup.find_all('input', {'type': 'submit'})
        print(f"   Found {len(buttons)} submit buttons")
        for btn in buttons[:5]:
            name = btn.get('name', 'unknown')
            value = btn.get('value', 'unknown')
            print(f"      - {name}: '{value}'")

        print()
        print("=" * 60)
        print("Open debug_search_page.html to see the full form structure")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_mdlandrec_navigation())

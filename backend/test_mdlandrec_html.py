#!/usr/bin/env python3
"""
Diagnostic script to inspect actual MDLandRec HTML structure.

This helps us understand how to parse the real search results.
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

async def test_mdlandrec_search():
    """Test authentication and search on MDLandRec."""

    email = os.getenv('MONTGOMERY_MD_EMAIL')
    password = os.getenv('MONTGOMERY_MD_PASSWORD')

    if not email or not password:
        print("❌ No credentials found in .env file")
        return

    print(f"🔐 Using email: {email}")
    print()

    BASE_URL = "https://landrec.msa.maryland.gov"
    LOGIN_URL = f"{BASE_URL}/Account/Login"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:

        # Step 1: Get login page
        print("📄 Step 1: Fetching login page...")
        try:
            response = await client.get(LOGIN_URL)
            print(f"   Status: {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for CSRF token
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            csrf_token = token_input.get('value') if token_input else None
            print(f"   CSRF Token: {'Found' if csrf_token else 'Not found'}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return

        # Step 2: Login
        print()
        print("🔑 Step 2: Submitting login...")

        login_data = {
            "Email": email,
            "Password": password,
            "RememberMe": "false"
        }

        if csrf_token:
            login_data["__RequestVerificationToken"] = csrf_token

        try:
            response = await client.post(LOGIN_URL, data=login_data)
            print(f"   Status: {response.status_code}")

            # Check for errors
            if "Invalid" in response.text or "incorrect" in response.text.lower():
                print("   ❌ Login failed: Invalid credentials")
                # Save HTML for inspection
                Path("debug_login_error.html").write_text(response.text)
                print("   💾 Saved response to: debug_login_error.html")
                return
            else:
                print("   ✅ Login successful")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return

        # Step 3: Search by name
        print()
        print("🔍 Step 3: Searching for 'THANGAVEL'...")

        SEARCH_URL = f"{BASE_URL}/Pages/Search.aspx"

        search_params = {
            "County": "Montgomery",
            "SearchType": "Name",
            "Name": "THANGAVEL"
        }

        try:
            response = await client.get(SEARCH_URL, params=search_params)
            print(f"   Status: {response.status_code}")
            print(f"   Response length: {len(response.text)} characters")

            # Save HTML for inspection
            output_file = "debug_search_results.html"
            Path(output_file).write_text(response.text)
            print(f"   💾 Saved HTML to: {output_file}")
            print()

            # Parse and show structure
            print("📊 HTML Structure Analysis:")
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for common result indicators
            print()
            print("   Looking for result containers...")

            # Try different selectors
            selectors = [
                ('table rows', 'tr'),
                ('result divs', 'div.result'),
                ('document links', 'a[href*="Document"]'),
                ('any tables', 'table'),
                ('forms', 'form'),
            ]

            for name, selector in selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"   ✅ Found {len(elements)} {name}")
                    if len(elements) <= 5:
                        for i, elem in enumerate(elements[:3], 1):
                            print(f"      {i}. {elem.name} - classes: {elem.get('class', 'none')}")
                else:
                    print(f"   ❌ No {name} found")

            # Show page title
            title = soup.find('title')
            if title:
                print()
                print(f"   📄 Page title: {title.text.strip()}")

            # Check for "no results" messages
            no_results_indicators = ['no results', 'no records', 'not found', '0 results']
            page_text_lower = response.text.lower()
            for indicator in no_results_indicators:
                if indicator in page_text_lower:
                    print(f"   ⚠️  Found '{indicator}' in page text")
                    break

            print()
            print("=" * 60)
            print("NEXT STEPS:")
            print("1. Open debug_search_results.html in your browser")
            print("2. Inspect the HTML structure of search results")
            print("3. Update montgomery_county_md.py _parse_search_results()")
            print("   with the correct selectors")
            print("=" * 60)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mdlandrec_search())

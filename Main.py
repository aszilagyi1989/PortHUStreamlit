import streamlit as st
from streamlit_option_menu import option_menu
import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import pandas as pd
import nest_asyncio
nest_asyncio.apply()
import sys
import subprocess
subprocess.run(["playwright", "install", "chromium"])

if sys.platform == 'win32':
  asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)

st.set_page_config(
  layout = 'wide',
  page_title = 'Budapesti programok keresése a port.hu weboldalról',
  page_icon = 'ikon.png',
  menu_items = {'Get help': 'mailto:sz.adam1989@gmail.com',
                'Report a bug': 'mailto:sz.adam1989@gmail.com',
                'About': 'This webapplication makes you able to scrape data from port.hu website with PlayWright.'}
)

st.title('Budapesti programok')

async def run_playwright():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless = True) # False
    context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
    page = await context.new_page() # browser.
    await page.goto("https://port.hu/programkereso/zene") # 
    # await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)
    # await page.get_by_role("button", name = "ELFOGADOM").click(force = True)
    # await page.get_by_role("button", name = "Értem!").click(force = True)
    # await page.get_by_role("link", name = "Koncert", exact = True).click(force = True)
    # # await page.wait_for_load_state("networkidle")
    # await page.wait_for_timeout(2000)
    await page.get_by_text("találat megjelenítése").click(force = True)
    await page.wait_for_timeout(2000)
    # await page.wait_for_load_state("networkidle")
    
    all_page_text = await page.locator("body").inner_text()
    # print(all_page_text)
    
    all_page_text = str(all_page_text).split("Címlapon")[0] 
    talalatok = str(all_page_text).split("Hozzám legközelebb")[0]
    lines = talalatok.splitlines()
    for line in lines:
      if line.endswith("találat megjelenítése"):
        result = int(line.split(" ")[0])
        # print(result)
        break
      
    koncertek = str(all_page_text).split("Hozzám legközelebb")[1]
    # print(koncertek)
    lines = koncertek.splitlines()
    koncert = False
    name = ""
    # print(lines)
    
    print("itt")
    for line in lines:
      print("itt")
      print(line)
      if koncert == True and line != name and line != "JEGY" and line != "Ringató":
        await page.get_by_role("link", name = line).nth(0).click(force = True)
        await page.wait_for_timeout(2000)
        all_page_text = await page.locator("body").inner_text()
        
        # print(all_page_text)
        koncertek = all_page_text
        break
        # all_page_text = all_page_text.split("Címlapon")[0]
        # all_page_text = all_page_text.split("MEGOSZTOM")[1]
        await page.go_back()

      if line == "KONCERT":
        koncert = True
      else:
        koncert = False
        
        
        # locator = page.get_by_role("link", name = line).nth(0)
        # await locator.wait_for(state = "attached")
        # async with page.expect_popup() as popup_info:
        #   await locator.wait_for(state = "visible")
        #   await locator.click(force = True)
        #   
        # popup_page = await popup_info.value
          
        # async with page.expect_popup() as popup_info:
        #   print(line)
        #   # peldanyszam = page1.get_by_role("link", name = line).count()
        #   name = line
        #   await page.get_by_role("link", name = line).nth(0).click(force = True)
        #   # print(page1_info.value)
        #   popup_page = await popup_info.value
        #   # await popup_page.wait_for_load_state("networkidle")
        #   await popup_page.wait_for_timeout(2000)
          # all_page_text = await popup_page.locator("body").inner_text()
          # all_page_text = all_page_text.split("Címlapon")[0] 
          # all_page_text = all_page_text.split("MEGOSZTOM")[1]
          # print(all_page_text) # LLM modell kell
       #  break


      # print(line)
    
    # content = await page.title()
    await browser.close()
    
    return koncertek # lines # koncertek # all_page_text # content

selected = option_menu(None, ['Koncertek'], menu_icon = 'cast', default_index = 0, orientation = 'horizontal')

if selected == 'Koncertek':
  st.write(sys.platform)
  result = asyncio.run(run_playwright())
  st.write(result)
  
  # page.get_by_role("button", name="2").click()
  # page.get_by_role("button").nth(5).click()
  # page.get_by_role("button").filter(has_text=re.compile(r"^$")).nth(5).click()

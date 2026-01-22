import streamlit as st
from streamlit_option_menu import option_menu
import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import pandas as pd
import nest_asyncio
nest_asyncio.apply()
import sys
# import os
# os.system("playwright install")
# import subprocess
# subprocess.run(["playwright", "install", "chromium"])

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
    browser = await p.chromium.launch(headless = False)
    page = await browser.new_page()
    await page.goto("https://port.hu")
    await page.wait_for_timeout(3000)
    content = await page.title()
    await browser.close()
    
    return content

selected = option_menu(None, ['Koncertek'], menu_icon = 'cast', default_index = 0, orientation = 'horizontal')

if selected == 'Koncertek':
  print(sys.platform)
  result = asyncio.run(run_playwright())
  st.write(result)

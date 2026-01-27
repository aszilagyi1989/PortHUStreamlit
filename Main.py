import streamlit as st
from streamlit_option_menu import option_menu
import asyncio
from playwright.async_api import Playwright, async_playwright, expect
import pandas as pd
import sys
import time
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional, List
from geopy.geocoders import Nominatim
import folium
# import nest_asyncio
# nest_asyncio.apply()
import subprocess
subprocess.run(["playwright", "install", "chromium"])

if sys.platform == 'win32':
  asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  open = False
elif sys.platform == 'linux':
  open = True

st.set_page_config(
  layout = 'wide',
  page_title = 'Budapesti programok keresése a port.hu weboldalról',
  page_icon = 'ikon.png',
  menu_items = {'Get help': 'mailto:sz.adam1989@gmail.com',
                'Report a bug': 'mailto:sz.adam1989@gmail.com',
                'About': 'This webapplication makes you able to scrape data from port.hu website with PlayWright.'}
)

if "df" not in st.session_state:
  st.session_state.df = pd.DataFrame(columns = ["Cím", "Dátum", "Helyszín", "Ár", "Leírás", "Link"])

model = ChatOpenAI(model = "gpt-5.2") # OPENAI_MODEL

st.title('Budapesti programok', anchor = False, help = None)

class Event(BaseModel):
  Cím: Optional[str] = Field(default = "Nincs információ", description = "The address of the event")
  Dátum: Optional[str] = Field(default = "Nincs információ", description = "The date of the event")
  Helyszín: Optional[str] = Field(default = "Nincs információ", description = "The location of the event")
  Ár: Optional[str] = Field(default = "Nincs információ", description = "The price of the event")
  Leírás: Optional[str] = Field(default = "Nincs információ", description = "The description of the event")
  Link: Optional[str] = Field(default = "Nincs információ", description = "The hyperlink of the event")

queries = [
      f"Address of the event",
      f"Date of the event",
      f"Location of the event",
      f"Price of the event",
      f"Description of the event",
      f"Link of the event",
]

def get_relevant_chunks(retriever, queries: List[str]) -> List[str]:
  retrieved_texts = []
  for query in queries:
    docs = retriever.invoke(query)
    retrieved_texts.extend([doc.page_content for doc in docs])
    
  return list(set(retrieved_texts))

def search(text):
  # st.write(text)
  doc = Document(page_content = text)

  text_splitter = RecursiveCharacterTextSplitter(chunk_size = 1000)
  splits = text_splitter.split_documents([doc])
  
  vectorstore = Chroma.from_documents(splits, embedding = OpenAIEmbeddings())
  retriever = vectorstore.as_retriever(search_type = "similarity")
  
  prompt = ChatPromptTemplate.from_messages(
      [
          (
              "system",
              "You are an expert extraction algorithm. "
              "Only extract relevant information from the text. "
              "If you do not know the value of an attribute asked to extract, "
              "return Nincs információ instead of None/NULL/Empty for the attribute's value.",
          ),
          ("human", text), # "{text}"
      ]
  )
  
  runnable = prompt | model.with_structured_output(schema = Event)
      
  relevant_chunks = get_relevant_chunks(retriever, queries)
  
  reduced_text = str(" ").join(relevant_chunks)
  result = runnable.invoke({"text": reduced_text})
  
  result_df = pd.DataFrame([result.model_dump()])
  # st.dataframe(result_df, hide_index = True) 
  element.add_rows(result_df)
  # return result
  

async def run_playwright():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless = open) # False
    context = await browser.new_context(
      user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    context.set_default_timeout(10000)
    
    page = await context.new_page() # browser.
    await page.goto("https://port.hu/programkereso/zene") # 
    await page.wait_for_timeout(1000)
    
    if sys.platform == 'linux':
      await page.get_by_role("button", name = "CONFIRM").click(force = True)
      await page.wait_for_timeout(1000)
      await page.click('button:has-text("OK")')
      await page.wait_for_timeout(1000)
      await page.get_by_role("button", name = "Értem!").click(force = True)
      await page.wait_for_timeout(1000)
      # await page.screenshot(path = "debug0.png")
      # st.image("debug0.png")
    
    if sys.platform == 'win32':
      await page.get_by_role("button", name = "ELFOGADOM").click(force = True)
      await page.wait_for_timeout(1000)
      await page.get_by_role("button", name = "Értem!").click(force = True)
      await page.wait_for_timeout(1000)
      # await page.get_by_role("link", name = "Koncert", exact = True).click(force = True)
    
    await page.get_by_text("találat megjelenítése").click(force = True)
    await page.wait_for_timeout(1000)
    
    all_page_text = await page.locator("body").inner_text()
    
    all_page_text = str(all_page_text).split("Címlapon")[0] 
    talalatok = str(all_page_text).split("Hozzám legközelebb")[0]
    lines = talalatok.splitlines()
    result = 0
    for line in lines:
      if line.endswith("találat megjelenítése"):
        result = int(line.split(" ")[0])
        break
      
    koncertek = str(all_page_text).split("Hozzám legközelebb")[1]
    lines = str(koncertek).splitlines()
    koncert = False
    name = ""
    
    for line in lines:
      
      if line == "JEGY":
        continue

      if koncert == True and line != name: # and line != "Ringató"
        
        # if "|" in line:
        #   line = str(line).split("|")[0]
        #   line = line[:-2]
        #   st.write(line)
        #   
        # if "/" in line:
        #   line = str(line).split("/")[0]
        #   line = line[:-2]
        #   st.write(line)
          
        name = line
        popup_page = None
        try:
          async with page.expect_popup() as popup_info:
            # peldanyszam = page1.get_by_role("link", name = line).count()
            await page.wait_for_timeout(1000)
            await page.get_by_role("link", name = line).nth(0).click(force = True)
        except Exception as e:
          # st.error(f"Hiba történt: {e}. A következő esemény betöltésénél: {line}")
          koncert = False
          continue
          
        popup_page = await popup_info.value
        await popup_page.wait_for_timeout(1000)
        try:
          data = await popup_page.locator("body").inner_text()
        except Exception as e:
          # st.error(f"Hiba történt: {e}. A következő esemény body-jánál: {line}")
          koncert = False
          if popup_page:
            await popup_page.close()
          # await popup_page.screenshot(path = "debug.png")
          # st.image("debug.png")
          continue
        
        try:
          data = str(data).split("Címlapon")[0]
          data = str(data).split("MEGOSZTOM")[1]
          # st.info(data)
          search(data) # findings = 
          # st.info(findings)
        except Exception as e:
          if popup_page:
            await popup_page.close()
          # data = await popup_page.locator("body").inner_text()
          # st.error(f"Hiba történt: {e}. A következő esemény szövegénél: {line}")
          # st.error(data)
          # await popup_page.screenshot(path = "debug2.png")
          # st.image("debug2.png")
      # break
      
        if popup_page:
          await popup_page.close()

      if line == "KONCERT":
        koncert = True
      else:
        koncert = False
      
      
      
    # content = await page.title()
    await browser.close()
    
    return ""

selected = option_menu(None, ['Koncertek'], menu_icon = 'cast', default_index = 0, orientation = 'horizontal')

if selected == 'Koncertek':
  # st.write(sys.platform)
  element = st.dataframe(st.session_state.df, hide_index = True)
  result = asyncio.run(run_playwright()) #  
  
  # page.get_by_role("button", name = "2").click()
  # page.get_by_text("Hirdetés átugrása").click()

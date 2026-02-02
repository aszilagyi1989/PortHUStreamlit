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
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import datetime
import math
# import nest_asyncio
# nest_asyncio.apply()
import subprocess
subprocess.run(["playwright", "install", "chromium"])

if sys.platform == 'win32':
  asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  open = False
  delay = 800
elif sys.platform == 'linux':
  open = True
  delay = 200

st.set_page_config(
  layout = 'wide',
  page_title = 'Budapesti programok keresése a port.hu weboldalról',
  page_icon = 'ikon.png',
  menu_items = {'Get help': 'mailto:sz.adam1989@gmail.com',
                'Report a bug': 'mailto:sz.adam1989@gmail.com',
                'About': 'This webapplication makes you able to scrape data from port.hu website with PlayWright.'}
)

if "df" not in st.session_state:
  st.session_state.df = pd.DataFrame(columns = ["Esemény", "Cím", "Dátum", "Helyszín", "Ár", "Link"]) # "Leírás",

model = ChatOpenAI(model = "gpt-5.2") # OPENAI_MODEL

st.title('Budapesti programok', anchor = False, help = None)

class Event(BaseModel):
  Cím: Optional[str] = Field(default = "Nincs információ", description = "The address of the event")
  Dátum: Optional[str] = Field(default = "Nincs információ", description = "The date of the event")
  Helyszín: Optional[str] = Field(default = "Nincs információ", description = "The location of the event")
  Ár: Optional[str] = Field(default = "Nincs információ", description = "The price of the event")
  # Leírás: Optional[str] = Field(default = "Nincs információ", description = "The description of the event")
  Link: Optional[str] = Field(default = "Nincs információ", description = "The hyperlink of the event")

queries = [
      f"Address of the event",
      f"Date of the event",
      f"Location of the event",
      f"Price of the event",
      # f"Description of the event",
      f"Link of the event",
]

def get_relevant_chunks(retriever, queries: List[str]) -> List[str]:
  retrieved_texts = []
  for query in queries:
    docs = retriever.invoke(query)
    retrieved_texts.extend([doc.page_content for doc in docs])
    
  return list(set(retrieved_texts))

def search(text, eventname):
  
  try:
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
                "return Nincs információ instead of None, NULL or Empty values for the attribute's value.",
            ),
            ("human", text), # "{text}"
        ]
    )
    
    runnable = prompt | model.with_structured_output(schema = Event)
        
    relevant_chunks = get_relevant_chunks(retriever, queries)
    
    reduced_text = str(" ").join(relevant_chunks)
    result = runnable.invoke({"text": reduced_text})
    
    result_df = pd.DataFrame([result.model_dump()])
    result_df.insert(0, 'Esemény', [eventname])
    element.add_rows(result_df.astype(str))
  except Exception as e:
    st.error(f"Hiba történt: {e}")
  
  try:
    if pd.isna(result_df['Cím'].to_numpy()) == False and result_df['Cím'].to_numpy() != "Nincs információ":
      location = geolocator.geocode(result_df['Cím'].to_numpy())

      if location:
        # st.write(f"Cím: {location.address}")
        # st.write(f"Szélesség: {location.latitude}, Hosszúság: {location.longitude}")
        folium.Marker(location = [location.latitude, location.longitude], popup = 'Esemény: {} <br> Helyszín: {} <br> Dátum: {}'.format(result_df['Esemény'].to_numpy(), result_df['Helyszín'].to_numpy(), result_df['Dátum'].to_numpy())).add_to(marker_cluster)
      else:
        wrong_address = str(result_df['Cím'].to_numpy()).replace("utca", "út")
        wrong_address = str(wrong_address).replace("Petőfi-híd budai hídfő", "")
        wrong_address = str(wrong_address).replace("F épület", "")
        if ";" in wrong_address:
          wrong_address = str(wrong_address).split(";")[0]
        if "és" in wrong_address:
          wrong_address = str(wrong_address).split("és")[0]
        location = geolocator.geocode(wrong_address)
        if location:
          folium.Marker(location = [location.latitude, location.longitude], popup = 'Esemény: {} <br> Helyszín: {} <br> Dátum: {}'.format(result_df['Esemény'].to_numpy(), result_df['Helyszín'].to_numpy(), result_df['Dátum'].to_numpy())).add_to(marker_cluster)
        else:
          st.error(f"Nem találtam a megadott címet javítva se: {wrong_address}")
  except Exception as e:
    st.error(e)

  
async def run_playwright():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless = open) # False
    context = await browser.new_context(
      user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    context.set_default_timeout(10000)
    
    page = await context.new_page() # browser.
    
    if jumpword == "KONCERT":
      await page.goto("https://port.hu/programkereso/zene")
    elif jumpword == "FESZTIVÁL":
      await page.goto("https://port.hu/programkereso/fesztival")
    elif jumpword == "KIÁLLÍTÁS":
      await page.goto("https://port.hu/programkereso/kiallitas")
    elif jumpword == "EGYÉB":
      await page.goto("https://port.hu/programkereso/egyeb")
    await page.wait_for_timeout(delay)
    
    if sys.platform == 'linux':
      await page.get_by_role("button", name = "CONFIRM").click(force = True)
      await page.wait_for_timeout(delay)
      await page.click('button:has-text("OK")')
      await page.wait_for_timeout(delay)
      await page.get_by_role("button", name = "Értem!").click(force = True)
      await page.wait_for_timeout(delay)
      # await page.screenshot(path = "debug0.png")
      # st.image("debug0.png")
    
    if sys.platform == 'win32':
      await page.get_by_role("button", name = "ELFOGADOM").click(force = True)
      await page.wait_for_timeout(delay)
      await page.get_by_role("button", name = "Értem!").click(force = True)
      await page.wait_for_timeout(delay)
      # await page.get_by_role("link", name = "Koncert", exact = True).click(force = True)
      
    if today != start_date or today != end_date:

      await page.locator("#date").select_option("custom")
      await page.wait_for_timeout(delay)
      
      await page.locator("#events_from").click()
      await page.locator("#events_from").fill(start_date.isoformat())
      await page.wait_for_timeout(delay)
  
      await page.locator("#events_until").click()
      await page.locator("#events_until").fill(end_date.isoformat())
      await page.wait_for_timeout(delay)
      
      if jumpword == "KONCERT":
        await page.get_by_text("Mit? Koncert Koncert Fesztivál Kiállítás Egyéb Mikor? Ma Holnap A héten A hétvé").click()
      elif jumpword == "FESZTIVÁL":
        await page.get_by_text("Mit? Fesztivál Koncert Fesztivál Kiállítás Egyéb Mikor? Ma Holnap A héten A hé").click()
      elif jumpword == "KIÁLLÍTÁS":
        await page.get_by_text("Mit? Kiállítás Koncert Fesztivál Kiállítás Egyéb Mikor? Ma Holnap A héten A hé").click()
      elif jumpword == "EGYÉB":
        await page.get_by_text("Mit? Egyéb Koncert Fesztivál Kiállítás Egyéb Mikor? Ma Holnap A héten A hétvégé").click()
      await page.wait_for_timeout(delay)

    await page.get_by_text("találat megjelenítése").click(force = True)
    await page.wait_for_timeout(delay * 4)
    
    all_page_text = await page.locator("body").inner_text()
    
    all_page_text = str(all_page_text).split("Címlapon")[0] 
    talalatok = str(all_page_text).split("Hozzám legközelebb")[0]
    lines = talalatok.splitlines()
    pageNumbers = 0
    for line in lines:
      if line.endswith("találat megjelenítése"):
        pageNumbers = int(line.split(" ")[0])
        pageNumbers = math.ceil(pageNumbers / 20)
        break
      
    koncertek = str(all_page_text).split("Hozzám legközelebb")[1]
    lines = str(koncertek).splitlines()
    koncert = False
    # name = ""
    
    for pageNumber in range(pageNumbers):
      # st.info(pageNumbers)
      # st.info(pageNumber)
      # st.info(str(pageNumber + 1))
      
      if pageNumber > 0:
        await page.get_by_role("button", name = str(pageNumber + 1)).click()
        await page.wait_for_timeout(delay)
        # await page.screenshot(path = "debug0.png")
        # st.image("debug0.png")
        
        all_page_text = await page.locator("body").inner_text()
        await page.wait_for_timeout(delay)
        
        all_page_text = str(all_page_text).split("Címlapon")[0]
        koncertek = str(all_page_text).split("Hozzám legközelebb")[1]
        lines = str(koncertek).splitlines()
    
      for line in lines:
        
        if line == "JEGY":
          continue
  
        if koncert == True and line not in lista:
          
          lista.append(line)
          eventNumbers = await page.get_by_role("link", name = line).count()
          for eventNumber in range(eventNumbers):
            popup_page = None
            try:
              async with page.expect_popup() as popup_info:
                await page.wait_for_timeout(delay)
                await page.get_by_role("link", name = line).nth(eventNumber).click(force = True)
            except Exception as e:
              # st.error(f"Hiba történt: {e}. A következő esemény betöltésénél: {line}")
              koncert = False
              continue
              
            popup_page = await popup_info.value
            await popup_page.wait_for_timeout(delay)
            try:
              data = await popup_page.locator("body").inner_text()
            except Exception as e:
              # st.error(f"Hiba történt: {e}. A következő esemény body-jánál: {line}")
              koncert = False
              if popup_page:
                await popup_page.close()
              continue
            
            try:
              data = str(data).split("Címlapon")[0]
              data = str(data).split("MEGOSZTOM")[1]
              search(data, line)
            except Exception as e:
              if popup_page:
                await popup_page.close()
          
            if popup_page:
              await popup_page.close()
  
        if line == jumpword: # "KONCERT"
          koncert = True
        else:
          koncert = False
      
    await browser.close()

geolocator = Nominatim(user_agent = "askaiwithpy", timeout = 10)

today = datetime.datetime.now().date()

lista = []

DateRange = st.date_input(label = 'Időszak kiválasztása', value = (datetime.date(today.year, today.month, today.day), datetime.date(today.year, today.month, today.day)), min_value = datetime.date(today.year, today.month, today.day), max_value = datetime.date(today.year + 2, today.month, today.day), format = 'YYYY-MM-DD', key = "my_date")

selected = option_menu(None, ['Koncertek', 'Fesztiválok', 'Kiállítások', 'Egyéb események'], menu_icon = 'cast', default_index = 0, orientation = 'horizontal')

if selected == 'Koncertek':
  
  jumpword = "KONCERT"
  if st.button("Keresés"):
    
    try:
      start_date = DateRange[0]
      end_date = DateRange[1]
    except Exception as e:
      st.error(f"Hiba történt: {e}")
  
    element = st.dataframe(st.session_state.df, hide_index = True)
    
    map = folium.Map(location = [47.4983, 19.0408], zoom_start = 11)
    marker_cluster = MarkerCluster().add_to(map)
    
    # st_folium(map, height = 500, width = 700) # width = 700
    asyncio.run(run_playwright())
    st.components.v1.html(folium.Figure().add_child(map).render(), height = 500)

elif selected == 'Fesztiválok':
  
  jumpword = "FESZTIVÁL"
  if st.button("Keresés"):
    
    try:
      start_date = DateRange[0]
      end_date = DateRange[1]
    except Exception as e:
      st.error(f"Hiba történt: {e}")
  
    element = st.dataframe(st.session_state.df, hide_index = True)
    
    map = folium.Map(location = [47.4983, 19.0408], zoom_start = 11)
    marker_cluster = MarkerCluster().add_to(map)
    
    # st_folium(map, height = 500, width = 700) # width = 700
    asyncio.run(run_playwright())
    st.components.v1.html(folium.Figure().add_child(map).render(), height = 500)
    
elif selected == 'Kiállítások':
  
  jumpword = "KIÁLLÍTÁS"
  if st.button("Keresés"):
    
    try:
      start_date = DateRange[0]
      end_date = DateRange[1]
    except Exception as e:
      st.error(f"Hiba történt: {e}")
  
    element = st.dataframe(st.session_state.df, hide_index = True)
    
    map = folium.Map(location = [47.4983, 19.0408], zoom_start = 11)
    marker_cluster = MarkerCluster().add_to(map)
    
    # st_folium(map, height = 500, width = 700) # width = 700
    asyncio.run(run_playwright())
    st.components.v1.html(folium.Figure().add_child(map).render(), height = 500)
    
elif selected == 'Egyéb események':
  
  jumpword = "EGYÉB"
  if st.button("Keresés"):
    
    try:
      start_date = DateRange[0]
      end_date = DateRange[1]
    except Exception as e:
      st.error(f"Hiba történt: {e}")
  
    element = st.dataframe(st.session_state.df, hide_index = True)
    
    map = folium.Map(location = [47.4983, 19.0408], zoom_start = 11)
    marker_cluster = MarkerCluster().add_to(map)
    
    # st_folium(map, height = 500, width = 700) # width = 700
    asyncio.run(run_playwright())
    st.components.v1.html(folium.Figure().add_child(map).render(), height = 500)
  
  # page.get_by_text("Hirdetés átugrása").click()


# 1123 Budapest, XII. kerület, Jagelló utca 1-3.
# 1113 Budapest, XI. kerület, Henryk Sławik rakpart, Petőfi-híd budai hídfő
# 1113 Budapest, XI. kerület, Henryk Sławik rakpart Petőfi-híd budai hídfő

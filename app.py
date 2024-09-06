import os
import shutil
import pandas as pd
import streamlit as st
from utils import get_transcript, mp4_to_mp3, json_to_dataframe, process_deck


st.title("Movie Cutter")

movie_name = st.text_input("Movie Name")

col1, col2 = st.columns(2)
if col1.button("Transcribe"):
    with st.status("Transcribing...", expanded=True):
        mp4_to_mp3(movie_name)
        st.write("Video converted to audio")
        get_transcript(movie_name)
        st.write("Transcript generated")
        json_to_dataframe(movie_name)
        st.write("Dataframe created")

data_path = f"data/created/{movie_name}_data.xlsx"

if os.path.exists(data_path):
    with open(data_path, "rb") as f:
        col2.download_button(
            label="Download Data",
            data=f.read(),
            file_name=data_path.split("/")[-1],
            mime="application/octet-stream",
        )
else:
    col2.write("No data found to download, please transcribe first")


file = st.file_uploader("Choose a file", type="xlsx")
if st.button("Submit"):
    records = pd.read_excel(file).to_dict("records")
    decks = [records[i * 10 : (i + 1) * 10] for i in range(len(records) // 10 + 1)]

    new_decks = []
    if os.path.exists(f"data/out/{movie_name}"):
        shutil.rmtree(f"data/out/{movie_name}")
    os.mkdir(f"data/out/{movie_name}")
    for i, deck in enumerate(decks):
        new_deck = process_deck(deck, i, movie_name)
        new_decks.extend(new_deck)

    st.dataframe(pd.DataFrame(new_decks))

import os
import streamlit as st
from utils import get_transcript, mp4_to_mp3, json_to_dataframe, process_movie


st.set_page_config(page_title="Movie Clipper", page_icon=":movie_camera:")
st.title("Movie Clipper")

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
    df = process_movie(movie_name, file)
    st.dataframe(df)

    final_table_path = f"data/out/{movie_name}_final_table.xlsx"
    
    with open(final_table_path, "rb") as f:
        st.download_button(
            label="Download Data",
            data=f.read(),
            file_name=final_table_path.split("/")[-1],
            mime="application/octet-stream",
        )

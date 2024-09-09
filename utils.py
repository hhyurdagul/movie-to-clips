import os
import json
import shutil
import subprocess
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def seconds_to_hms(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def hms_to_seconds(hms):
    if isinstance(hms, float):
        return float("nan")
    hours, minutes, seconds = hms.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

def create_translation(text_block):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a translator that translates English text into Turkish.",
            },
            {
                "role": "user",
                "content": f"Translate the following English text into Turkish, keeping the context I want new lines exactly the same as before. \n\n{text_block}",
            },
        ],
    )

    full_translation = completion.choices[0].message.content
    if full_translation:
        return [i.strip() for i in full_translation.strip().split("\n")]
    else:
        return [""]


def cut_video(input_path, output_path, start_time, end_time=None):
    if not (end_time is None and end_time == float("nan")):
        commands = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start_time),
            "-i",
            input_path,
            "-c:v",
            "libx264",
            "-c:a",
            "copy",
            output_path,
        ]
    else:
        commands = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start_time),
            "-to",
            str(end_time),
            "-i",
            input_path,
            "-c:v",
            "libx264",
            "-c:a",
            "copy",
            output_path,
        ]

    subprocess.run(commands)
    return True


def mp4_to_mp3(movie_name):
    input_file = f"data/input/{movie_name}.mp4"
    output_file = f"data/created/{movie_name}.mp3"
    if os.path.exists(output_file):
        return
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-vn",
            "-q:a",
            "0",
            output_file,
        ]
    )


def get_transcript(movie_name):
    audio_path = f"data/created/{movie_name}.mp3"
    transcript_path = f"data/created/{movie_name}_transcript.json"
    if os.path.exists(transcript_path):
        return

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            language="en",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

        with open(transcript_path, "w") as f:
            json.dump(transcript.to_dict(), f)


def json_to_dataframe(movie_name):
    transcript_path = f"data/created/{movie_name}_transcript.json"
    data_path = f"data/created/{movie_name}_data.xlsx"
    if os.path.exists(data_path):
        return
    with open(transcript_path) as f:
        data = json.load(f)

    df = pd.DataFrame(
        [
            {
                "text": segment["text"].strip(),
                "start": seconds_to_hms(round(segment["start"])),
                "end": seconds_to_hms(round(segment["end"])),
                "duration_start": seconds_to_hms(round(segment["start"])),
                "duration_end": seconds_to_hms(round(segment["end"])),
            }
            for segment in data["segments"]
        ]
    )
    df["end"] = df.shift(-1)["start"]
    df.to_excel(data_path, index=False)


def create_clips_from_deck(deck, deck_number, movie_name):
    movie_path = f"data/input/{movie_name}.mp4"
    deck_dir = f"data/out/{movie_name}/Deste {deck_number+1}"
    part_dir = f"{deck_dir}/Partlar {deck_number * 10 + 1}-{deck_number * 10 + 10}"

    os.mkdir(deck_dir)
    os.mkdir(part_dir)

    # Deck Clip
    cut_video(
        input_path=movie_path,
        output_path=f"{deck_dir}/{movie_name}_D{deck_number+1}.mp4",
        start_time=deck[0]["start"],
        end_time=deck[-1]["end"],
    )

    for i, part in enumerate(deck):
        part_clip_path = f"{part_dir}/{movie_name}_{i+1}.mp4"
        cut_video(
            input_path=movie_path,
            output_path=part_clip_path,
            start_time=part["start"],
            end_time=part["end"],
        )

def create_data_from_deck(deck, deck_number, movie_name):
    return [
        {
            "DeckNo": deck_number + 1,
            "PartNo": i + 1,
            "Order": i + 1,
            "StartTime": seconds_to_hms(part["duration_start"] - deck[0]["duration_start"]),
            "EndTime": seconds_to_hms(part["duration_end"] - deck[0]["duration_start"]),
            "SourceLanguage": "EN",
            "TR": "",
            "EN": part["text"].strip(),
            "FileNameDeste": f"{movie_name}_D{deck_number+1}.mp4" if i == 0 else "",
            "FileNamePart": f"{movie_name}_{i+1}.mp4",
        }
        for i, part in enumerate(deck)
    ]


def process_movie(movie_name, data_path):
    raw_records = pd.read_excel(data_path)
    print(raw_records)
    raw_records["start"] = raw_records["start"].apply(lambda x: hms_to_seconds(x))
    raw_records["end"] = raw_records["end"].apply(lambda x: hms_to_seconds(x))
    raw_records["duration_start"] = raw_records["duration_start"].apply(lambda x: hms_to_seconds(x))
    raw_records["duration_end"] = raw_records["duration_end"].apply(lambda x: hms_to_seconds(x))

    records = raw_records.to_dict("records")
    decks = [records[i * 10 : (i + 1) * 10] for i in range(len(records) // 10 + 1)]
    if os.path.exists(f"data/out/{movie_name}"):
        shutil.rmtree(f"data/out/{movie_name}")
    os.mkdir(f"data/out/{movie_name}")

    new_decks = []
    for i, deck in enumerate(decks):
        create_clips_from_deck(deck, i, movie_name)
        new_deck = create_data_from_deck(deck, i, movie_name)
        new_decks.extend(new_deck)

    df = pd.DataFrame(new_decks)
    translation = []
    try_count = 0
    while len(translation) != len(df):
        translation = create_translation(df["EN"].str.cat(sep="\n"))
        if try_count > 10:
            translation = [""] * len(df)
            break
        try_count += 1

    df["TR"] = translation

    df.to_excel(f"data/out/{movie_name}_final_table.xlsx")

    return df

if __name__ == "__main__":
    pass
    # mp4_to_mp3("Paterson")
    # transcript = get_transcript("Paterson")
    # print(transcript)

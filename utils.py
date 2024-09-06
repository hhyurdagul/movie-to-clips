import os
import json
import subprocess
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def cut_video(input_path, output_path, start_time, end_time=None):
    if not end_time:
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
    return True


def get_transcript(movie_name):
    audio_path = f"data/created/{movie_name}.mp3"
    transcript_path = f"data/created/{movie_name}_transcript.json"

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

    return True


def json_to_dataframe(movie_name):
    transcript_path = f"data/created/{movie_name}_transcript.json"
    data_path = f"data/created/{movie_name}_data.xlsx"
    with open(transcript_path) as f:
        data = json.load(f)

    df = pd.DataFrame(
        [
            {
                "text": segment["text"].strip(),
                "start": round(segment["start"], 1),
                "end": round(segment["end"], 1),
                "duration_start": round(segment["start"], 1),
                "duration_end": round(segment["end"], 1),
            }
            for segment in data["segments"]
        ]
    )
    df["end"] = df.shift(-1)["start"]
    df.to_excel(data_path, index=False)
    return True


def cut_deck(movie_name, deck_number, deck_start, deck_end):
    deck_path = f"data/out/{movie_name}/Deste {deck_number+1}"
    cut_video(
        input_path=f"data/input/{movie_name}.mp4",
        output_path=f"{deck_path}/{movie_name}_D{deck_number+1}.mp4",
        start_time=deck_start,
        end_time=deck_end,
    )


def cut_deck_part(movie_name, dir_path, part_number, start_time, end_time=None):
    input_path = f"data/input/{movie_name}.mp4"
    output_path = f"{dir_path}/{movie_name}_{part_number+1}.mp4"
    cut_video(
        input_path=input_path,
        output_path=output_path,
        start_time=start_time,
        end_time=end_time,
    )


def process_deck(deck, deck_number, movie_name):
    new_deck = []
    os.mkdir(f"data/out/{movie_name}/Deste {deck_number+1}")

    deck_path = f"data/out/{movie_name}/Deste {deck_number+1}"
    dir_name = f"Partlar {deck_number * 10 + 1}-{deck_number * 10 + 10}"
    dir_path = f"{deck_path}/{dir_name}"
    os.mkdir(dir_path)

    cut_deck(movie_name, deck_number, deck[0]["start"], deck[-1]["end"])
    for i, part in enumerate(deck):
        obj = {
            "DeckNo": deck_number + 1,
            "PartNo": i + 1,
            "Order": i + 1,
            "StartTime": part["duration_start"] - deck[0]["duration_start"],
            "EndTime": part["duration_end"] - deck[0]["duration_start"],
            "SourceLanguage": "EN",
            "EN": part["text"].strip(),
            "FileNameDeste": f"{movie_name}_D{deck_number+1}.mp4" if i == 0 else "",
            "FileNamePart": f"{movie_name}_{i+1}.mp4",
        }

        cut_deck_part(movie_name, dir_path, i, part["start"], part["end"])

        new_deck.append(obj)

    return new_deck


if __name__ == "__main__":
    mp4_to_mp3("Paterson")
    transcript = get_transcript("Paterson")
    print(transcript)

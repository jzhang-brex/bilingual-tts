import argparse
import json
import tempfile
from gtts import gTTS
from pydub import AudioSegment
from tqdm import tqdm
import pydub
import os
import pysrt
import deepl

def fake_translate_func(text, target_lang):
    return "Hello world"

def create_audio_from_audio(
    input_audio,
    subtitle_file,
    output_file,
    transition_sound,
    repeat_count,
    tr_lang,
    verbose,
    translate_func,
    interval=500,
):
    # Load the input audio file using AudioSegment.from_file
    input_audio = AudioSegment.from_file(input_audio)
    print("Loaded input audio")

    # Load the subtitle file and parse it into a list of sentences
    subtitle_data = pysrt.open(subtitle_file)
    sentences = [subtitle.text for subtitle in subtitle_data]

    if verbose:
        for i, sentence in enumerate(sentences):
            print(f"{i:03d} {sentence}")

    # Create a temporary directory to store the audio segments
    temp_dir = tempfile.mkdtemp()

    # Create an empty list to store the audio segments
    audio_segments = []

    # Iterate over the sentences in the subtitle file
    for subtitle in tqdm(subtitle_data, desc='Processing sentences'):
        # Extract the start and end times from the subtitle
        start_time = subtitle.start.ordinal / 1000  # Convert from milliseconds to seconds
        end_time = subtitle.end.ordinal / 1000  # Convert from milliseconds to seconds

        # Extract the corresponding audio segment from the input audio
        audio_segment = input_audio[start_time * 1000:end_time * 1000]  # Convert from seconds to milliseconds

        # Repeat the audio segment three times with a silent interval in between
        repeated_audio_segment = audio_segment + AudioSegment.silent(duration=1000)  # 1 second silent interval
        repeated_audio_segment = repeated_audio_segment * 3

        # Translate the subtitle text using the provided translate function
        translation = translate_func(subtitle.text, target_lang=tr_lang)

        # Convert the translation into speech using gTTS
        # Convert the TextResult object to a string
        tts = gTTS(text=str(translation), lang=tr_lang)

        # Save the translated speech to a temporary file
        tts_file = os.path.join(temp_dir, f'{subtitle.text}.mp3')
        tts.save(tts_file)

        # Load the translated speech as an audio segment
        tts_audio_segment = AudioSegment.from_file(tts_file)

        # Append the TTS translation to the repeated audio segments with a silent interval
        repeated_audio_segment += AudioSegment.silent(duration=interval) + tts_audio_segment

        # Append the original extracted audio segment one more time with a silent interval
        repeated_audio_segment += AudioSegment.silent(duration=interval) + audio_segment

        # Append the repeated audio segment to the list of audio segments
        audio_segments.append(repeated_audio_segment)

    # Load the transition sound
    transition_sound = AudioSegment.from_file(transition_sound)

    # Concatenate the audio segments into a single audio file
    final_audio = pydub.AudioSegment.empty()
    for audio_segment in audio_segments:
        # Append the transition sound to each audio segment
        final_audio += audio_segment + transition_sound

    # Save the final audio to the output file
    final_audio.export(output_file, format='mp3')

def fromaudio_main(args):
    print("Generating bilingual TTS from audio ...")

    if 'DEEPL_API_KEY' not in os.environ:
        print("Error: The DEEPL_API_KEY environment variable is not set. Please set it to your DeepL API key.")
        exit(1)

    if args.tr_strategy == "deepl":
        translator = deepl.Translator(os.environ['DEEPL_API_KEY'])
        translate_func = translator.translate_text
    else:
        translate_func = fake_translate_func

    # If output file is not provided, derive it from the input audio file
    if args.output_file is None:
        args.output_file = args.input_audio.rsplit('.', 1)[0] + '.mp3'

    create_audio_from_audio(
        args.input_audio,
        args.subtitle_file,
        args.output_file,
        args.transition_sound,
        args.repeat_count,
        args.tr_lang,
        args.verbose,
        translate_func=translate_func,
    )

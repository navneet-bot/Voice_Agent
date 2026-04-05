"""
Manual Test: Transcribe any local audio file.
Usage: python3 check_voice.py <path_to_audio_file.wav>
"""

import sys
import os
from stt import transcribe_audio

def main():
    # 1. Grab file path from command line
    if len(sys.argv) < 2:
        print("\n❌ Error: No file provided.")
        print("Usage: python3 check_voice.py <path_to_audio_file>\n")
        return

    file_path = sys.argv[1]
    
    # 2. Basic validation
    if not os.path.exists(file_path):
        print(f"\n❌ Error: File '{file_path}' not found.\n")
        return

    # 3. Read and Transcribe
    print(f"\n[1/2] Reading '{file_path}' ...")
    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
            
        print("[2/2] Transcribing using Whisper 'small' model ...")
        text = transcribe_audio(audio_bytes)

        # 4. Show Result
        print("\n" + "=" * 40)
        print(f"TRANSCRIPTION: \"{text}\"")
        print("=" * 40 + "\n")
        
        if not text:
            print("ℹ️  Note: Transcription was empty. This usually means silence,")
            print("   non-speech audio, or background noise was filtered out.\n")

    except Exception as e:
        print(f"\n❌ An error occurred during transcription: {e}\n")

if __name__ == "__main__":
    main()

import pyaudio
import sys

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

p = pyaudio.PyAudio()

print(f"[TEST] Testing Microphone at {RATE}Hz...")
default_in = p.get_default_input_device_info()
print(f"Using: {default_in['name']} (Index {default_in['index']})")

try:
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=default_in['index'])
    
    print("[SUCCESS] Stream opened successfully! Listening for 3 seconds...")
    frames = []
    
    for i in range(0, int(RATE / CHUNK * 3)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        if i % 10 == 0:
            print(f"Captured block {i}...")

    print("[SUCCESS] Successfully captured audio!")
    
    stream.stop_stream()
    stream.close()
    
except Exception as e:
    print(f"[ERROR] Failed to open/read from microphone: {e}")

p.terminate()

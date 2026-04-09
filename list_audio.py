import pyaudio
p = pyaudio.PyAudio()
print("\n--- Available Audio Devices ---")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"Index {i}: {info.get('name')} (Inputs: {info.get('maxInputChannels')}, Outputs: {info.get('maxOutputChannels')})")
p.terminate()

Thai Chameleon Book - Microsoft TTS Fix
Replace the repository's app.py and requirements.txt with these two files.
This version uses Microsoft Edge TTS only, with retries, chunking, clear failure messages, and MP3 download.
For long texts, it downloads separate MP3 parts as a ZIP, not a misleading concatenated MP3.
It does not solve upstream Microsoft/edge-tts service blocking or network outages.

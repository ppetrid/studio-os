# studio-os

## Run the api server

`uvicorn api.app:app --reload`

To run with mock midi inputs / outputs

`STUDIO_MIDI_BACKEND=mock uvicorn api.app:app --reload`

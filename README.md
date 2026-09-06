# studio-os

## Run the development server

### Python

```shell
uvicorn api.app:app --reload
```

To run with mock midi inputs / outputs

```shell
STUDIO_MIDI_BACKEND=mock uvicorn api.app:app --reload
```

### UI

```shell
cd frontent
npm run dev
```

Navigate to http://localhost:5173/

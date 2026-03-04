# 🎧 My Spotify Wrapped - Streamlit App

An interactive "Spotify Wrapped" app built with Streamlit, showcasing your listening data from Spotify's Extended Streaming History export.

## Features

- **Overview Page**: Total hours, plays, top artists/tracks, genre distribution, time-of-day patterns, platform stats
- **Explore Page**: Search artists, view their top tracks, see listening timeline
- **For You Page**: Personalized recommendations based on your listening patterns

## Local Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the app**:
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Data Required

Place your Spotify data in the same directory as `app.py`:
- `Spotify Extended Streaming History/` - folder with JSON files
- `master_music_library.csv` - Kaggle music library for genre enrichment

## Deploying to Streamlit Cloud

1. Push this code to a GitHub repository
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Connect your GitHub and deploy
4. Add your Spotify data files to the repo (or use Streamlit secrets for large files)

## Project Structure

```
spotify_wrapped/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## What This Demonstrates

- Data engineering (JSON parsing, feature engineering)
- Data visualization (Plotly charts)
- Building interactive web apps
- End-to-end data projects

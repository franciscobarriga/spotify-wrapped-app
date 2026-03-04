# Streamlit Spotify Wrapped App
# Requirements: streamlit, pandas, plotly

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import glob
import json
import hashlib

# Page config
st.set_page_config(
    page_title="My Spotify Wrapped",
    page_icon="🎧",
    layout="wide"
)

@st.cache_data
def load_data():
    """Load and process Spotify streaming history"""

    all_data = []

    # Read all JSON files
    spotify_dir = "Spotify Extended Streaming History"
    for f in sorted(glob.glob(f"{spotify_dir}/Streaming_History_Audio_*.json")):
        with open(f) as file:
            content = file.read()
            for obj in content.split(']['):
                try:
                    if not obj.startswith('['):
                        obj = '[' + obj
                    if not obj.endswith(']'):
                        obj = obj + ']'
                    data = json.loads(obj)
                    all_data.extend(data)
                except:
                    pass

    df = pd.DataFrame(all_data)

    # Parse timestamp
    df['ts'] = pd.to_datetime(df['ts'])
    df['year'] = df['ts'].dt.year
    df['month'] = df['ts'].dt.month
    df['hour'] = df['ts'].dt.hour
    df['day_of_week'] = df['ts'].dt.dayofweek
    df['date'] = df['ts'].dt.date
    df['year_month'] = df['ts'].dt.to_period('M')

    # Time of day
    def get_time_bucket(hour):
        if 5 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 17:
            return 'Afternoon'
        elif 17 <= hour < 21:
            return 'Evening'
        else:
            return 'Night'

    df['time_bucket'] = df['hour'].apply(get_time_bucket)
    df['is_weekend'] = df['day_of_week'].isin([5, 6])

    # Platform
    df['is_mobile'] = df['platform'].str.contains('iOS|Android', case=False, na=False)
    df['is_desktop'] = df['platform'].str.contains('Mac|Windows|Linux', case=False, na=False)

    # Minutes played
    df['minutes_played'] = df['ms_played'] / 1000 / 60

    # Completion ratio
    df['completion_ratio'] = df['ms_played'] / 180000  # Assuming 3 min avg song

    # Clean track/artist names
    df['track_name'] = df['master_metadata_track_name'].fillna('Unknown')
    df['artist_name'] = df['master_metadata_album_artist_name'].fillna('Unknown')
    df['album_name'] = df['master_metadata_album_album_name'].fillna('Unknown')

    return df

@st.cache_data
def load_music_library():
    """Load Kaggle music library for genre/enrichment"""
    return pd.read_csv("master_music_library.csv")

@st.cache_data
def get_genre_data(df, library_df):
    """Match streaming history with genre data"""

    # Create match keys
    df['match_key'] = (df['artist_name'].str.lower().str.strip() + '||' +
                       df['track_name'].str.lower().str.strip())

    library_df['match_key'] = (library_df['artist_name'].str.lower().str.strip() + '||' +
                               library_df['track_name'].str.lower().str.strip())

    # Keep unique tracks per artist for matching
    library_unique = library_df.drop_duplicates(subset=['match_key'])

    # Merge
    merged = df.merge(library_unique[['match_key', 'genre', 'danceability', 'energy',
                                       'tempo', 'valence', 'acousticness', 'popularity']],
                      on='match_key', how='left')

    return merged

# Main app
st.title("🎧 My Spotify Wrapped")

# Sidebar for navigation
page = st.sidebar.radio("Go to", ["Overview", "Explore", "For You"])

# Load data
with st.spinner("Loading your listening data..."):
    df = load_data()
    library_df = load_music_library()
    df_enriched = get_genre_data(df, library_df)

if page == "Overview":
    st.header("📊 Your Listening Overview")

    # KPIs
    total_hours = df['minutes_played'].sum() / 60
    total_plays = len(df)
    unique_artists = df['artist_name'].nunique()
    unique_tracks = df['track_name'].nunique()
    date_range = f"{df['date'].min()} to {df['date'].max()}"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Hours", f"{total_hours:,.0f}")
    col2.metric("Total Plays", f"{total_plays:,}")
    col3.metric("Unique Artists", f"{unique_artists:,}")
    col4.metric("Unique Tracks", f"{unique_tracks:,}")

    st.caption(f"📅 Listening history: {date_range}")

    # Charts
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Hours by Year")
        hours_by_year = df.groupby('year')['minutes_played'].sum() / 60
        fig_year = px.bar(
            x=hours_by_year.index,
            y=hours_by_year.values,
            labels={'x': 'Year', 'y': 'Hours'},
            color=hours_by_year.values,
            color_continuous_scale='viridis'
        )
        fig_year.update_layout(showlegend=False)
        st.plotly_chart(fig_year, use_container_width=True)

    with col2:
        st.subheader("Time of Day")
        time_counts = df['time_bucket'].value_counts()
        time_order = ['Morning', 'Afternoon', 'Evening', 'Night']
        time_counts = time_counts.reindex(time_order)
        fig_time = px.pie(
            values=time_counts.values,
            names=time_counts.index,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_time.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_time, use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Top 10 Artists")
        top_artists = df['artist_name'].value_counts().head(10)
        fig_artists = px.bar(
            y=top_artists.index[::-1],
            x=top_artists.values[::-1],
            orientation='h',
            labels={'x': 'Plays', 'y': 'Artist'},
            color=top_artists.values[::-1],
            color_continuous_scale='blues'
        )
        fig_artists.update_layout(showlegend=False)
        st.plotly_chart(fig_artists, use_container_width=True)

    with col2:
        st.subheader("🎵 Top 10 Tracks")
        top_tracks = df.groupby(['track_name', 'artist_name']).size().reset_index(name='plays')
        top_tracks = top_tracks.sort_values('plays', ascending=False).head(10)
        top_tracks['label'] = top_tracks['track_name'] + '\nby ' + top_tracks['artist_name']

        fig_tracks = px.bar(
            y=top_tracks['label'].iloc[::-1],
            x=top_tracks['plays'].iloc[::-1],
            orientation='h',
            labels={'x': 'Plays', 'y': 'Track'},
            color=top_tracks['plays'].iloc[::-1],
            color_continuous_scale='greens'
        )
        fig_tracks.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_tracks, use_container_width=True)

    st.divider()

    # Genre distribution (from enriched data)
    st.subheader("🎸 Genre Distribution")

    col1, col2 = st.columns(2)

    with col1:
        genre_plays = df_enriched[df_enriched['genre'].notna()].groupby('genre')['minutes_played'].sum()
        genre_plays = genre_plays.sort_values(ascending=False).head(10)
        fig_genre = px.bar(
            y=genre_plays.index[::-1],
            x=genre_plays.values[::-1],
            orientation='h',
            labels={'x': 'Minutes', 'y': 'Genre'},
            color=genre_plays.values[::-1],
            color_continuous_scale='oranges'
        )
        fig_genre.update_layout(showlegend=False)
        st.plotly_chart(fig_genre, use_container_width=True)

    with col2:
        # Audio features radar
        audio_features = ['danceability', 'energy', 'valence', 'acousticness']
        avg_features = df_enriched[audio_features].mean()

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=avg_features.values,
            theta=audio_features,
            fill='toself',
            name='Average'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()

    # Platform & weekend stats
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📱 Platform")
        platform_data = df.groupby(df['is_mobile'].map({True: 'Mobile', False: 'Desktop'}))['minutes_played'].sum()
        fig_platform = px.pie(
            values=platform_data.values,
            names=platform_data.index,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_platform.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_platform, use_container_width=True)

    with col2:
        st.subheader("📅 Weekend vs Weekday")
        weekend_data = df.groupby(df['is_weekend'].map({True: 'Weekend', False: 'Weekday'}))['minutes_played'].sum()
        fig_weekend = px.bar(
            x=weekend_data.index,
            y=weekend_data.values,
            color=weekend_data.index,
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        fig_weekend.update_layout(showlegend=False, yaxis_title="Minutes")
        st.plotly_chart(fig_weekend, use_container_width=True)


elif page == "Explore":
    st.header("🔍 Explore Your Music")

    # Search for artist
    search_artist = st.text_input("Search for an artist", "")

    if search_artist:
        # Filter artists
        matching_artists = df[df['artist_name'].str.contains(search_artist, case=False, na=False)]['artist_name'].unique()

        if len(matching_artists) > 0:
            selected_artist = st.selectbox("Select artist", matching_artists)

            # Artist stats
            artist_df = df[df['artist_name'] == selected_artist]

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Plays", len(artist_df))
            col2.metric("Total Hours", f"{artist_df['minutes_played'].sum() / 60:.1f}")
            col3.metric("Unique Tracks", artist_df['track_name'].nunique())

            st.divider()

            # Top tracks by this artist
            st.subheader(f"🎵 Top Tracks by {selected_artist}")
            artist_tracks = artist_df.groupby('track_name').agg({
                'minutes_played': 'sum',
                'ts': 'count'
            }).rename(columns={'ts': 'plays', 'minutes_played': 'total_minutes'})
            artist_tracks = artist_tracks.sort_values('plays', ascending=False).head(10)

            st.dataframe(
                artist_tracks.reset_index().rename(columns={
                    'track_name': 'Track',
                    'plays': 'Plays',
                    'total_minutes': 'Minutes'
                }),
                hide_index=True,
                use_container_width=True
            )

            # Listening timeline
            st.subheader("📈 Listening Over Time")
            monthly = artist_df.groupby(artist_df['ts'].dt.to_period('M'))['minutes_played'].sum()
            fig_monthly = px.line(
                x=[str(x) for x in monthly.index],
                y=monthly.values,
                labels={'x': 'Month', 'y': 'Minutes'}
            )
            fig_monthly.update_traces(line_color='#1DB954')
            st.plotly_chart(fig_monthly, use_container_width=True)

        else:
            st.warning("No artists found matching your search.")


elif page == "For You":
    st.header("💡 Personalized Recommendations")

    st.markdown("""
    Based on your listening patterns, here are some recommendations:
    """)

    # Get top genres and artists for recommendations
    top_genres = df_enriched[df_enriched['genre'].notna()].groupby('genre')['minutes_played'].sum().sort_values(ascending=False).head(5)
    top_artists_list = df['artist_name'].value_counts().head(10).index.tolist()

    # Recommendation types
    rec_type = st.selectbox(
        "Choose recommendation type",
        ["Rediscover Old Favorites", "Similar Artists", "New Discoveries",
         "Session Buddies", "Weekend Vibes", "Night Owl Picks"]
    )

    if rec_type == "Rediscover Old Favorites":
        st.subheader("🔄 Rediscover Old Favorites")
        st.markdown("Tracks you loved but haven't listened to recently.")

        # Get tracks from 2014-2018 that were popular
        old_tracks = df[(df['year'] >= 2014) & (df['year'] <= 2018)]
        old_favorites = old_tracks.groupby(['track_name', 'artist_name']).size().sort_values(ascending=False).head(10)

        for i, ((track, artist), plays) in enumerate(old_favorites.items(), 1):
            st.write(f"{i}. **{track}** - {artist} ({plays} plays)")

    elif rec_type == "Similar Artists":
        st.subheader("🎤 Similar Artists")
        st.markdown("Artists similar to your top favorites.")

        # Simple similarity based on co-occurrence
        similar = {}
        for artist in top_artists_list[:5]:
            # Find other artists commonly listened together
            artist_listeners = df[df['artist_name'] == artist]['track_name'].unique()
            co_listeners = df[df['track_name'].isin(artist_listeners)]['artist_name'].value_counts()
            for other_artist, count in co_listeners.items():
                if other_artist != artist:
                    similar[(artist, other_artist)] = similar.get((artist, other_artist), 0) + count

        # Show top similar
        similar_sorted = sorted(similar.items(), key=lambda x: x[1], reverse=True)[:10]

        for (original, similar_artist), count in similar_sorted:
            st.write(f"→ If you like **{original}**, try: **{similar_artist}**")

    elif rec_type == "New Discoveries":
        st.subheader("🆕 New Discoveries")
        st.markdown("Artists you've barely explored but might love.")

        # Artists with few plays but high engagement potential (popular in library)
        artist_plays = df['artist_name'].value_counts()
        library_popular = library_df.groupby('artist_name')['popularity'].mean().sort_values(ascending=False)

        # Find artists you listen to less but are popular
        recommendations = []
        for artist in library_popular.head(100).index:
            if artist.lower() not in [a.lower() for a in df['artist_name'].unique()]:
                recommendations.append(artist)
            if len(recommendations) >= 10:
                break

        for i, artist in enumerate(recommendations, 1):
            st.write(f"{i}. **{artist}** (popularity: {library_popular[artist]:.0f})")

    elif rec_type == "Session Buddies":
        st.subheader("👥 Session Buddies")
        st.markdown("Perfect for long listening sessions.")

        # Long tracks (>5 min) from your top artists
        long_plays = df[df['ms_played'] > 5 * 60 * 1000]
        session_tracks = long_plays.groupby(['track_name', 'artist_name']).size().sort_values(ascending=False).head(10)

        for i, ((track, artist), plays) in enumerate(session_tracks.items(), 1):
            st.write(f"{i}. **{track}** - {artist}")

    elif rec_type == "Weekend Vibes":
        st.subheader("🎉 Weekend Vibes")
        st.markdown("Perfect for your weekend listening.")

        weekend_df = df[df['is_weekend']]
        weekend_genres = df_enriched[df_enriched['genre'].notna() & df_enriched['date'].isin(weekend_df['date'])]
        weekend_top = weekend_genres.groupby('genre')['minutes_played'].sum().sort_values(ascending=False).head(5)

        st.write("Your top weekend genres:")
        for genre, mins in weekend_top.items():
            st.write(f"- **{genre}**: {mins:.0f} minutes")

        st.write("\nTop weekend tracks:")
        weekend_tracks = weekend_df.groupby(['track_name', 'artist_name']).size().sort_values(ascending=False).head(5)
        for i, ((track, artist), plays) in enumerate(weekend_tracks.items(), 1):
            st.write(f"{i}. **{track}** - {artist} ({plays} plays)")

    elif rec_type == "Night Owl Picks":
        st.subheader("🦉 Night Owl Picks")
        st.markdown("Your late-night favorites.")

        night_df = df[df['time_bucket'] == 'Night']
        night_tracks = night_df.groupby(['track_name', 'artist_name']).size().sort_values(ascending=False).head(10)

        for i, ((track, artist), plays) in enumerate(night_tracks.items(), 1):
            st.write(f"{i}. **{track}** - {artist}")

    st.divider()

    # Mood filters
    st.subheader("🎛️ Filter by Mood")

    mood = st.select_slider(
        "Choose your mood",
        options=["Chill", "Neutral", "Energetic"]
    )

    if mood == "Chill":
        chill_tracks = df_enriched[df_enriched['energy'] < 0.4].nlargest(10, 'valence')
        st.write("**Chill recommendations:**")
        for _, row in chill_tracks.iterrows():
            st.write(f"- {row['track_name']} - {row['artist_name']}")
    elif mood == "Energetic":
        energy_tracks = df_enriched[df_enriched['energy'] > 0.7].nlargest(10, 'danceability')
        st.write("**High energy recommendations:**")
        for _, row in energy_tracks.iterrows():
            st.write(f"- {row['track_name']} - {row['artist_name']}")
    else:
        st.write("Balanced recommendations based on your overall listening.")

# Footer
st.markdown("---")
st.caption("🎧 Built with Streamlit • Data from Spotify Extended Streaming History")

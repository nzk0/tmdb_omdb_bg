# TMDB Movie Poster Generator

A modern Python script that generates beautiful movie and TV show posters using data from The Movie Database (TMDB) and OMDB APIs. Creates high-quality poster images with backdrop images, logos, cast information, ratings, and more.

## 🎬 Features

- **Multiple Content Sources**: Fetches from trending, popular, now playing, and top-rated movies/TV shows
- **Rich Poster Design**: Combines backdrop images with logos, cast, crew, ratings, and plot summaries
- **Multiple Rating Sources**: 
  - Rotten Tomatoes scores with Fresh/Rotten/Certified Fresh icons
  - Metacritic scores
  - TMDB scores as fallback
- **Smart Logo Handling**: Automatically downloads and resizes official logos, with text fallback
- **Customizable Filtering**: Exclude content by country, genre, or keywords
- **Fuzzy Matching**: Intelligent title matching for better rating accuracy
- **High-Quality Output**: Optimized JPEG images ready for Android TV, other TV operating systems, and various media applications

## 🖼️ Sample Output

![Seven_Samurai](https://github.com/user-attachments/assets/cbaf6eb6-efe6-4763-8ace-a5f0801c5666)
![Parasite](https://github.com/user-attachments/assets/4ed7e18b-74d1-44b2-a810-83d163410567)
![The_Sopranos](https://github.com/user-attachments/assets/48b0fe12-699f-4d24-bd0e-9b8d200170e7)
![The_Dark_Knight](https://github.com/user-attachments/assets/25aa9bcf-5e8d-4316-b343-fce5b9b6ee1b)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nzk0/tmdb-poster-generator.git
   cd tmdb-poster-generator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get API Keys**
   - **TMDB API Key**: Sign up at [TMDB](https://www.themoviedb.org/settings/api) and get your API key
   - **OMDB API Key**: Get a free key at [OMDB API](http://www.omdbapi.com/apikey.aspx)

4. **Configure API Keys**
   
   Edit `TMDB8.py` and replace the placeholder values:
   ```python
   API_KEY = "YOUR_TMDB_API_KEY_HERE"
   OMDB_API_KEY = "YOUR_OMDB_API_KEY_HERE"
   ```

5. **Add Required Images**
   
   Place these image files in the same directory as the script:
   - `bckg.png` - Background template
   - `overlay.png` - Overlay template  
   - `tmdblogo.png` - TMDB logo
   - `fresh_tomato.png` - Fresh Rotten Tomatoes icon
   - `rotten_tomato.png` - Rotten Tomatoes icon
   - `Certified_Fresh_2018.png` - Certified Fresh icon
   - `Metacritic_M.png` - Metacritic logo
   - `1f3ad.png` - Performing arts emoji (for cast)
   - `1f3ac.png` - Clapper board emoji (for director)

## 🎯 Usage

Run the script:
```bash
python TMDB8.py
```

The script will:
1. Fetch trending and popular movies/TV shows from TMDB
2. Filter content based on your preferences
3. Download backdrop images and logos
4. Fetch ratings from multiple sources
5. Generate poster images in the `tmdb_backgrounds/` folder

## ⚙️ Customization

### Content Filtering

Customize the exclusion filters at the top of the script:

```python
# Exclude specific countries (e.g., ["cn", "kr", "in"])
EXCLUDED_COUNTRIES = []

# Exclude specific genres (e.g., ["Talk", "Documentary", "News"])
EXCLUDED_GENRES = []

# Exclude content with specific keywords (e.g., ["adult", "animation"])
EXCLUDED_KEYWORDS = []
```

### Advanced Filtering

The `_should_exclude` method contains commented examples for:
- **Language-based filtering**: Exclude content in specific languages
- **Title keyword filtering**: Exclude content with certain words in titles
- **Talk show filtering**: Filter out late night and talk shows
- **Animation filtering**: Allow Western animation while excluding anime

Uncomment and modify these sections as needed:

```python
# Example: Exclude Hindi, Tamil, Telugu content
# indian_languages = ["hi", "ta", "te", "kn", "ml", "bn", "gu", "mr", "pa", "or", "as", "ur"]
# if original_language in indian_languages:
#     return True
```

### Output Configuration

Modify these settings in the script:
- `OUTPUT_DIR`: Change output folder name
- Image quality and format settings in `_create_poster` method
- Font sizes and positioning in `_add_content` method

## 📁 Output

Generated posters are saved as high-quality JPEG files in the `tmdb_backgrounds/` folder with optimizations for:
- Android TV backgrounds
- Other TV operating systems
- Media server applications
- Digital displays and kiosks

## 🛠️ Requirements

- Python 3.7+
- aiohttp >= 3.8.0
- Pillow >= 9.0.0

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source. Please check the license file for details.

## 🙏 Credits

- **Original Script**: [adelatour11/androidtvbackground](https://github.com/adelatour11/androidtvbackground)
- **Modified Version**: [nzk0](https://github.com/nzk0)
- **APIs Used**: 
  - [The Movie Database (TMDB)](https://www.themoviedb.org/)
  - [OMDB API](http://www.omdbapi.com/)

## ⚠️ Disclaimer

This project is for educational and personal use. Make sure to comply with the terms of service of TMDB and OMDB APIs. The generated posters are for personal use and should respect copyright laws.

## 🐛 Troubleshooting

### Common Issues

1. **"Please set your API key"**: Make sure you've replaced the placeholder API keys with your actual keys

2. **Missing image files**: Ensure all required PNG files are in the script directory

3. **No posters generated**: Check that your filters aren't too restrictive and that the APIs are accessible

4. **Poor image quality**: Verify that backdrop and logo images are available for the selected content

### Debug Output

The script provides detailed console output showing:
- API fetch progress
- Filtering decisions
- Rating source information
- Image processing status
- Error messages with specific details

For additional help, please open an issue on GitHub.

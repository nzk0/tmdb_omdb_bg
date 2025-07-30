# =============================================================================
# Modern TMDB Movie/TV Poster Generator - Version: 1.0.0
# =============================================================================
#Based on the original script by https://github.com/adelatour11/androidtvbackground
#Modified by https://github.com/nzk0

import asyncio
import os
import shutil
import textwrap
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import difflib

import aiohttp
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# CONFIGURATION - UPDATE YOUR API KEYS HERE
# =============================================================================
# Get your TMDB API key from: https://www.themoviedb.org/settings/api
API_KEY = "YOUR_TMDB_API_KEY_HERE"

# Get your OMDB API key from: http://www.omdbapi.com/apikey.aspx
OMDB_API_KEY = "YOUR_OMDB_API_KEY_HERE"

BASE_URL = "https://api.themoviedb.org/3/"
OMDB_URL = "http://www.omdbapi.com/"
IMAGE_BASE = "https://image.tmdb.org/t/p/original"
FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Light.ttf"
OUTPUT_DIR = "tmdb_backgrounds"

# Exclusion filters - customize these to your preferences
# Examples: ["cn", "kr", "in"] to exclude Chinese, Korean, Indian content
EXCLUDED_COUNTRIES = []

# Examples: ["Talk", "Documentary", "News"] to exclude talk shows, documentaries, news
EXCLUDED_GENRES = []

# Examples: ["adult", "animation"] to exclude adult content and animation
EXCLUDED_KEYWORDS = []

# =============================================================================
# MAIN CLASS
# =============================================================================

class TMDBPosterGenerator:
    def __init__(self):
        # Validate API keys
        if API_KEY == "YOUR_TMDB_API_KEY_HERE" or not API_KEY:
            raise ValueError("Please set your TMDB API key in the API_KEY variable")
        if OMDB_API_KEY == "YOUR_OMDB_API_KEY_HERE" or not OMDB_API_KEY:
            raise ValueError("Please set your OMDB API key in the OMDB_API_KEY variable")
            
        self.headers = {"accept": "application/json", "Authorization": f"Bearer {API_KEY}"}
        self.font_cache = {}
        self.output_dir = Path(OUTPUT_DIR)
        
        # Clean and create output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run(self):
        """Main entry point"""
        print("🎬 Starting TMDB poster generation...")
        
        async with aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(30)) as session:
            self.session = session
            
            # Fetch genres and multiple trending/popular endpoints concurrently
            results = await asyncio.gather(
                # Genre lists
                self._api_get("genre/movie/list?language=en-US"),
                self._api_get("genre/tv/list?language=en-US"),
                
                # Movie endpoints - more variety and current content
                self._api_get("trending/movie/day?language=en-US"),      # Daily trending (most current)
                self._api_get("trending/movie/week?language=en-US"),     # Weekly trending (original)
                self._api_get("movie/popular?language=en-US"),           # Popular movies
                self._api_get("movie/now_playing?language=en-US"),       # Current cinema releases
                self._api_get("movie/top_rated?language=en-US"),         # Highly rated movies
                
                # TV endpoints - more variety and current content
                self._api_get("trending/tv/day?language=en-US"),         # Daily trending TV
                self._api_get("trending/tv/week?language=en-US"),        # Weekly trending TV (original)
                self._api_get("tv/popular?language=en-US"),              # Popular TV shows
                self._api_get("tv/on_the_air?language=en-US"),           # Currently airing
                self._api_get("tv/top_rated?language=en-US")             # Highly rated TV
            )
            
            movie_genres = {g["id"]: g["name"] for g in results[0].get("genres", [])}
            tv_genres = {g["id"]: g["name"] for g in results[1].get("genres", [])}
            
            # Combine all movie sources
            all_movies = []
            movie_sources = [
                ("Daily Trending Movies", results[2].get("results", [])),
                ("Weekly Trending Movies", results[3].get("results", [])),
                ("Popular Movies", results[4].get("results", [])),
                ("Now Playing Movies", results[5].get("results", [])),
                ("Top Rated Movies", results[6].get("results", []))
            ]
            
            for source_name, movies in movie_sources:
                print(f"📊 {source_name}: {len(movies)} items")
                all_movies.extend(movies)
            
            # Combine all TV sources
            all_tv = []
            tv_sources = [
                ("Daily Trending TV", results[7].get("results", [])),
                ("Weekly Trending TV", results[8].get("results", [])),
                ("Popular TV", results[9].get("results", [])),
                ("On The Air TV", results[10].get("results", [])),
                ("Top Rated TV", results[11].get("results", []))
            ]
            
            for source_name, tv_shows in tv_sources:
                print(f"📺 {source_name}: {len(tv_shows)} items")
                all_tv.extend(tv_shows)
            
            # Remove duplicates based on ID
            unique_movies = self._remove_duplicates(all_movies)
            unique_tv = self._remove_duplicates(all_tv)
            
            print(f"🎬 Total unique movies: {len(unique_movies)}")
            print(f"📺 Total unique TV shows: {len(unique_tv)}")
            
            # Process movies and TV shows
            await asyncio.gather(
                self._process_items(unique_movies, movie_genres, True),
                self._process_items(unique_tv, tv_genres, False)
            )
        
        print("✅ Poster generation completed!")

    def _remove_duplicates(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate items based on ID, keeping the first occurrence"""
        seen_ids = set()
        unique_items = []
        
        for item in items:
            item_id = item.get("id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_items.append(item)
        
        return unique_items

    async def _api_get(self, endpoint: str) -> Dict:
        """Make API request"""
        try:
            async with self.session.get(f"{BASE_URL}{endpoint}") as response:
                return await response.json()
        except Exception as e:
            print(f"❌ API error for {endpoint}: {e}")
            return {}

    async def _process_items(self, items: List[Dict], genres: Dict[int, str], is_movie: bool):
        """Process movies or TV shows"""
        media_type = "movie" if is_movie else "tv"
        name_key = "title" if is_movie else "name"
        
        for item in items:
            try:
                # Quick validation
                if (item.get("vote_average", 0) == 0 or 
                    not item.get("overview", "").strip() or
                    self._should_exclude(item, genres)):
                    continue
                
                # Check for backdrop (required)
                if not item.get("backdrop_path"):
                    print(f"⚠️  Skipping {item.get(name_key, 'Unknown')}: No backdrop image available")
                    continue
                
                # Check for logo (required)
                logo_path = await self._get_logo(media_type, item["id"])
                if not logo_path:
                    print(f"⚠️  Skipping {item.get(name_key, 'Unknown')}: No logo available")
                    continue
                
                # Get details and credits (both required)
                details, credits = await asyncio.gather(
                    self._api_get(f"{media_type}/{item['id']}?language=en-US"),
                    self._api_get(f"{media_type}/{item['id']}/credits")
                )
                
                # Validate details
                if not details or not details.get("id"):
                    print(f"⚠️  Skipping {item.get(name_key, 'Unknown')}: Could not fetch details")
                    continue
                
                # Validate credits
                if not credits or (not credits.get("cast") and not credits.get("crew")):
                    print(f"⚠️  Skipping {item.get(name_key, 'Unknown')}: No cast or crew information available")
                    continue
                
                # Check for minimum cast (at least 1 actor)
                if not credits.get("cast") or len(credits.get("cast", [])) == 0:
                    print(f"⚠️  Skipping {item.get(name_key, 'Unknown')}: No cast information available")
                    continue
                
                await self._create_poster(item, details, credits, genres, is_movie)
                
            except Exception as e:
                print(f"❌ Error processing {item.get(name_key, 'Unknown')}: {e}")
                continue

    async def _get_ratings(self, item: Dict, details: Dict) -> Dict:
        """Get both Rotten Tomatoes and Metacritic ratings from OMDB API with fuzzy matching fallback"""
        # First try: Use IMDB ID (most reliable)
        imdb_id = details.get("imdb_id")
        if imdb_id:
            ratings = await self._fetch_omdb_ratings({"i": imdb_id})
            if ratings["rt_score"] is not None or ratings["metacritic_score"] is not None:
                return ratings
        
        # Second try: Fuzzy name matching if IMDB ID fails
        title = item.get("title") or item.get("name", "")
        year = (item.get('release_date') or item.get('first_air_date', ''))[:4]
        
        if title and year:
            print(f"⚠️  IMDB ID matching failed for '{title}', trying fuzzy name matching...")
            
            # Try exact title first
            ratings = await self._fetch_omdb_ratings({"t": title, "y": year})
            if ratings["rt_score"] is not None or ratings["metacritic_score"] is not None:
                print(f"✅ Found ratings using exact title match")
                return ratings
            
            # Try fuzzy matching by searching and finding best match
            search_results = await self._search_omdb_fuzzy(title, year)
            if search_results:
                best_match = search_results[0]  # Take the best match
                ratings = await self._fetch_omdb_ratings({"i": best_match["imdbID"]})
                if ratings["rt_score"] is not None or ratings["metacritic_score"] is not None:
                    print(f"✅ Found ratings using fuzzy match: '{best_match['Title']}' ({best_match['Year']})")
                    return ratings
        
        print(f"⚠️  No OMDB ratings found for '{title}' ({year})")
        return {"rt_score": None, "certified_fresh": False, "metacritic_score": None}

    async def _search_omdb_fuzzy(self, title: str, year: str) -> List[Dict]:
        """Search OMDB and find similar titles using fuzzy matching"""
        try:
            # Search OMDB for similar titles
            params = {
                "s": title,
                "y": year,
                "apikey": OMDB_API_KEY
            }
            
            async with self.session.get(OMDB_URL, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                if data.get("Response") != "True" or "Search" not in data:
                    return []
                
                search_results = data["Search"]
                
                # Calculate similarity scores and sort by best match
                scored_results = []
                for result in search_results:
                    omdb_title = result.get("Title", "")
                    # Use difflib for fuzzy string matching
                    similarity = difflib.SequenceMatcher(None, title.lower(), omdb_title.lower()).ratio()
                    
                    # Boost score if year matches exactly
                    if result.get("Year") == year:
                        similarity += 0.1
                    
                    # Only consider results with reasonable similarity (80%+)
                    if similarity >= 0.8:
                        scored_results.append({
                            "similarity": similarity,
                            "imdbID": result.get("imdbID"),
                            "Title": omdb_title,
                            "Year": result.get("Year")
                        })
                
                # Sort by similarity score (highest first)
                scored_results.sort(key=lambda x: x["similarity"], reverse=True)
                return scored_results
                
        except Exception as e:
            print(f"⚠️  OMDB search failed: {e}")
            return []

    async def _fetch_omdb_ratings(self, params: Dict) -> Dict:
        """Fetch ratings from OMDB API with given parameters"""
        try:
            # Add API key to params
            params["apikey"] = OMDB_API_KEY
            params["plot"] = "short"
            
            async with self.session.get(OMDB_URL, params=params) as response:
                if response.status != 200:
                    return {"rt_score": None, "certified_fresh": False, "metacritic_score": None}
                
                data = await response.json()
                
                if data.get("Response") != "True":
                    return {"rt_score": None, "certified_fresh": False, "metacritic_score": None}
                
                # Extract both RT and Metacritic scores from the same response
                ratings = data.get("Ratings", [])
                rt_score = None
                metacritic_score = None
                
                for rating in ratings:
                    source = rating.get("Source", "")
                    value = rating.get("Value", "")
                    
                    if source == "Rotten Tomatoes" and "%" in value:
                        try:
                            rt_score = int(value.replace("%", ""))
                        except ValueError:
                            continue
                    elif source == "Metacritic" and "/" in value:
                        try:
                            # Convert from X/100 to percentage
                            score_part = value.split("/")[0]
                            metacritic_score = int(score_part)
                        except ValueError:
                            continue
                
                # Determine if Certified Fresh (75%+ RT score)
                certified_fresh = rt_score is not None and rt_score >= 75
                
                return {
                    "rt_score": rt_score,
                    "certified_fresh": certified_fresh,
                    "metacritic_score": metacritic_score
                }
                
        except Exception as e:
            print(f"⚠️  OMDB API request failed: {e}")
            return {"rt_score": None, "certified_fresh": False, "metacritic_score": None}

    def _should_exclude(self, item: Dict, genres: Dict[int, str]) -> bool:
        """Check if item should be excluded based on configured filters"""
        # Get country
        origin = item.get("origin_country", "")
        country = (origin[0] if isinstance(origin, list) and origin else origin).lower()
        
        # Get genres
        item_genres = [genres.get(gid, "") for gid in item.get("genre_ids", [])]
        
        # Get original language
        original_language = item.get("original_language", "").lower()
        
        # Get title for keyword filtering
        title = (item.get("title") or item.get("name", "")).lower()
        
        # Check for excluded countries
        # Example: Exclude Chinese, Korean, Indian content
        if country in EXCLUDED_COUNTRIES:
            return True
        
        # Language-based filtering (customize as needed)
        # Example: Exclude Hindi, Tamil, Telugu, or other specific languages
        # indian_languages = ["hi", "ta", "te", "kn", "ml", "bn", "gu", "mr", "pa", "or", "as", "ur"]
        # if original_language in indian_languages:
        #     return True
        
        # Title-based keyword filtering (customize as needed)
        # Example: Exclude content with specific keywords in the title
        # bollywood_keywords = ["bollywood", "hindi", "tamil", "telugu", "kannada", "malayalam", "bengali"]
        # if any(keyword in title for keyword in bollywood_keywords):
        #     return True
        
        # Talk show filtering by title keywords (customize as needed)
        # Example: Filter out talk shows and late night shows
        # talk_show_keywords = [
        #     "tonight show", "late show", "late night", "daily show", "talk show",
        #     "with stephen", "with jimmy", "with trevor", "with john", "with bill",
        #     "real time", "last week tonight", "saturday night live", "snl",
        #     "the view", "the talk", "good morning", "morning show", "today show",
        #     "meet the press", "face the nation", "this week", "state of the union",
        #     "tucker carlson", "sean hannity", "rachel maddow", "anderson cooper",
        #     "bill maher", "conan", "ellen", "oprah", "dr. phil", "jerry springer"
        # ]
        # if any(keyword in title for keyword in talk_show_keywords):
        #     return True
        
        # Animation filtering (customize as needed)
        # Example: Allow Western animation but exclude Asian animation (anime)
        # if "Animation" in item_genres:
        #     western_countries = ["us", "ca", "gb", "au", "nz", "ie", "fr", "de", "es", "it", "nl", "be", "dk", "se", "no", "fi"]
        #     asian_countries = ["jp", "kr", "cn", "tw", "hk", "th", "sg", "my", "id", "ph", "vn", "in", "pk", "bd", "lk", "mm", "kh", "la", "mn", "uz", "kz", "kg", "tj", "tm", "af"]
        #     
        #     if country in asian_countries:
        #         return True  # Exclude Asian animation
        #     elif country in western_countries:
        #         pass  # Allow Western animation
        #     else:
        #         return True  # Exclude unknown origin animation
        
        # Check excluded genres from configuration
        if any(g in EXCLUDED_GENRES for g in item_genres):
            return True
        
        # Check excluded keywords in title
        if any(keyword in title for keyword in EXCLUDED_KEYWORDS):
            return True
        
        return False

    async def _get_logo(self, media_type: str, media_id: int) -> Optional[str]:
        """Get logo path"""
        data = await self._api_get(f"{media_type}/{media_id}/images?language=en")
        for logo in data.get("logos", []):
            if logo.get("iso_639_1") == "en" and logo.get("file_path", "").endswith(".png"):
                return logo["file_path"]
        return None

    async def _create_poster(self, item: Dict, details: Dict, credits: Dict, genres: Dict[int, str], is_movie: bool):
        """Create the poster image"""
        backdrop_path = item.get("backdrop_path")
        if not backdrop_path:
            return
        
        try:
            # Download backdrop with error handling
            backdrop_url = f"{IMAGE_BASE}{backdrop_path}"
            async with self.session.get(backdrop_url) as response:
                if response.status != 200:
                    print(f"❌ Failed to download backdrop: HTTP {response.status}")
                    return
                backdrop_data = await response.read()
                if not backdrop_data:
                    print(f"❌ Empty backdrop data received")
                    return
            
            # Load required local images with error handling
            script_dir = Path(__file__).parent
            required_files = {
                "background": "bckg.png",
                "overlay": "overlay.png", 
                "tmdb_logo": "tmdblogo.png"
            }
            
            loaded_images = {}
            for name, filename in required_files.items():
                file_path = script_dir / filename
                if not file_path.exists():
                    print(f"❌ Required file missing: {filename}")
                    return
                try:
                    loaded_images[name] = Image.open(file_path).convert("RGBA")
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")
                    return
            
            # Load backdrop image
            try:
                backdrop = Image.open(BytesIO(backdrop_data))
            except Exception as e:
                print(f"❌ Failed to process backdrop image: {e}")
                return
            
            # Resize and compose
            backdrop_resized = self._resize_image(backdrop, 1500)
            background = loaded_images["background"]
            background.paste(backdrop_resized, (1175, 0))
            background.paste(loaded_images["overlay"], (1175, 0), loaded_images["overlay"])
            
            # Add all content
            await self._add_content(background, item, details, credits, genres, loaded_images["tmdb_logo"], is_movie)
            
            # Save with optimizations for Reddit/ProjectiVy
            title = item.get("title" if is_movie else "name", "unknown")
            filename = self.output_dir / f"{self._clean_filename(title)}.jpg"
            background.convert('RGB').save(
                filename, 
                format='JPEG',
                quality=95, 
                optimize=True,
                progressive=True,
                exif=b''  # Strip all metadata
            )
            print(f"✅ Created: {filename.name}")
            
        except Exception as e:
            title = item.get("title" if is_movie else "name", "Unknown")
            print(f"❌ Poster creation failed for {title}: {e}")

    async def _add_content(self, img: Image.Image, item: Dict, details: Dict, credits: Dict, 
                          genres: Dict[int, str], tmdb_logo: Image.Image, is_movie: bool):
        """Add all text and elements to the poster"""
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        font_title = await self._get_font(190)
        font_text = await self._get_font(50)
        
        # Positions and colors
        title_pos = (200, 420)
        info_pos = (210, 650)
        shadow_offset = 2
        
        # TMDB logo - back to original gray tinting
        target_height = 40
        tmdb_aspect_ratio = tmdb_logo.width / tmdb_logo.height
        tmdb_new_width = int(target_height * tmdb_aspect_ratio)
        tmdb_resized = tmdb_logo.resize((tmdb_new_width, target_height))
        gray_overlay = Image.new('RGBA', tmdb_resized.size, (150, 150, 150, 255))
        tmdb_tinted = Image.composite(gray_overlay, tmdb_resized, tmdb_resized)
        tmdb_y_offset = info_pos[1] + ((50 - target_height) // 2) + 6
        img.paste(tmdb_tinted, (info_pos[0], tmdb_y_offset), tmdb_tinted)
        
        # Metadata with original gray colors - LIMIT TO 3 GENRES
        all_genres = [genres.get(gid, '') for gid in item.get('genre_ids', [])]
        # Take only the first 3 genres (TMDB orders them by relevance)
        top_genres = all_genres[:3]
        genre_text = ', '.join(top_genres)
        year = (item.get('release_date' if is_movie else 'first_air_date', '') or '')[:4]
        
        if is_movie:
            runtime = details.get('runtime', 0)
            duration = f"{runtime//60}h{runtime%60}min" if runtime else "N/A"
            additional_info = duration
        else:
            seasons = details.get('number_of_seasons', 0)
            additional_info = f"{seasons} {'Season' if seasons == 1 else 'Seasons'}"
        
        info_text = f"{genre_text}  •  {year}  •  {additional_info}  •"
        info_text_x = info_pos[0] + tmdb_new_width + 30
        
        self._draw_text_with_shadow(draw, (info_text_x, info_pos[1]), info_text, font_text, (150, 150, 150))
        
        # Rating with Rotten Tomatoes and Metacritic data, TMDB fallback
        ratings_data = await self._get_ratings(item, details)
        
        # Check if we have ANY rating available
        has_external_rating = ratings_data["rt_score"] is not None or ratings_data["metacritic_score"] is not None
        has_tmdb_rating = item.get('vote_average', 0) > 0
        
        if not has_external_rating and not has_tmdb_rating:
            title = item.get("title" if is_movie else "name", "Unknown")
            print(f"⚠️  Skipping {title}: No ratings available from any source")
            return
        
        await self._add_ratings(draw, img, ratings_data, info_text, info_text_x, info_pos, font_text, item)
        
        # Credits with original gray colors
        credits_y = await self._add_credits(draw, img, credits, info_pos[1] + 80, font_text, is_movie, details)
        
        # Overview with original gray colors
        overview = item.get('overview', '')
        wrapped_overview = "\n".join(textwrap.wrap(overview, width=70, max_lines=3, placeholder="..."))
        self._draw_text_with_shadow(draw, (210, credits_y + 25), wrapped_overview, font_text, (150, 150, 150))
        
        # Title or logo with error handling
        media_type = "movie" if is_movie else "tv"
        logo_path = await self._get_logo(media_type, item["id"])
        await self._add_title_or_logo(draw, img, item, logo_path, title_pos, font_title, info_pos, is_movie)

    async def _add_ratings(self, draw, img, ratings_data, info_text, info_text_x, info_pos, font, item):
        """Add both Rotten Tomatoes and Metacritic ratings, with TMDB fallback"""
        script_dir = Path(__file__).parent
        current_x = info_text_x
        
        # Calculate base position after info text
        bbox = draw.textbbox((0, 0), info_text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        space_bbox = draw.textbbox((0, 0), "  ", font=font)
        extra_offset = int((space_bbox[2] - space_bbox[0]) / 2)
        current_x = info_text_x + text_width + 10 + extra_offset
        
        # Track if we display any external ratings
        displayed_external = False
        
        # Add Rotten Tomatoes rating
        if ratings_data["rt_score"] is not None:
            rt_score = ratings_data["rt_score"]
            
            # Choose appropriate RT icon
            if ratings_data["certified_fresh"]:
                rt_icon_file = "Certified_Fresh_2018.png"
            else:
                rt_icon_file = "fresh_tomato.png" if rt_score >= 60 else "rotten_tomato.png"
            
            rt_icon_path = script_dir / rt_icon_file
            
            if rt_icon_path.exists():
                try:
                    rt_icon = Image.open(rt_icon_path).convert("RGBA").resize((50, 50))
                    rt_icon_y = info_pos[1] + (text_height - 50) // 2 + 10
                    
                    img.paste(rt_icon, (current_x, rt_icon_y), rt_icon)
                    
                    # RT percentage
                    rt_text = f"{rt_score}%"
                    rt_text_x = current_x + 60
                    self._draw_text_with_shadow(draw, (rt_text_x, info_pos[1]), rt_text, font, (150, 150, 150))
                    
                    # Update position for next rating
                    rt_text_bbox = draw.textbbox((0, 0), rt_text, font=font)
                    current_x = rt_text_x + (rt_text_bbox[2] - rt_text_bbox[0]) + 20  # 20px spacing
                    
                    print(f"✅ Using RT score: {rt_score}% {'(Certified Fresh)' if ratings_data['certified_fresh'] else ''}")
                    displayed_external = True
                    
                except Exception as e:
                    print(f"❌ Failed to load RT icon {rt_icon_file}: {e}")
        
        # Add Metacritic rating
        if ratings_data["metacritic_score"] is not None:
            mc_score = ratings_data["metacritic_score"]
            mc_icon_path = script_dir / "Metacritic_M.png"
            
            if mc_icon_path.exists():
                try:
                    mc_icon = Image.open(mc_icon_path).convert("RGBA").resize((50, 50))
                    mc_icon_y = info_pos[1] + (text_height - 50) // 2 + 10
                    
                    img.paste(mc_icon, (current_x, mc_icon_y), mc_icon)
                    
                    # Metacritic percentage
                    mc_text = f"{mc_score}%"
                    mc_text_x = current_x + 60
                    self._draw_text_with_shadow(draw, (mc_text_x, info_pos[1]), mc_text, font, (150, 150, 150))
                    
                    print(f"✅ Using Metacritic score: {mc_score}%")
                    displayed_external = True
                    
                except Exception as e:
                    print(f"❌ Failed to load Metacritic icon: {e}")
            else:
                print("❌ Metacritic icon not found: Metacritic_M.png")
        
        # Fallback to TMDB only if BOTH external ratings are missing
        if not displayed_external:
            tmdb_rating = item.get('vote_average', 0)
            if tmdb_rating > 0:
                # Convert TMDB 0-10 scale to 0-100 percentage
                tmdb_percentage = round(tmdb_rating * 10)
                
                # Choose tomato based on TMDB score (6.0+ = fresh)
                tomato_file = "fresh_tomato.png" if tmdb_rating >= 6.0 else "rotten_tomato.png"
                tomato_path = script_dir / tomato_file
                
                if tomato_path.exists():
                    try:
                        tmdb_icon = Image.open(tomato_path).convert("RGBA").resize((50, 50))
                        tmdb_icon_y = info_pos[1] + (text_height - 50) // 2 + 10
                        
                        img.paste(tmdb_icon, (current_x, tmdb_icon_y), tmdb_icon)
                        
                        # TMDB percentage
                        tmdb_text = f"{tmdb_percentage}%"
                        tmdb_text_x = current_x + 60
                        self._draw_text_with_shadow(draw, (tmdb_text_x, info_pos[1]), tmdb_text, font, (150, 150, 150))
                        
                        print(f"✅ Using TMDB fallback score: {tmdb_percentage}% (from {tmdb_rating}/10)")
                        
                    except Exception as e:
                        print(f"❌ Failed to load TMDB fallback icon {tomato_file}: {e}")
                else:
                    print(f"❌ TMDB fallback icon not found: {tomato_file}")
            else:
                print("⚠️  No ratings available (external or TMDB)")

    async def _add_credits(self, draw, img, credits, start_y, font, is_movie, details):
        """Add cast and crew credits"""
        # Get top actors (only show famous ones, no +number)
        cast_list = credits.get('cast', [])
        # Just take the first 3 actors (they're ordered by importance)
        top_cast = [actor['name'] for actor in cast_list[:3]]
        
        # Get directors - ensure we always have them
        if is_movie:
            directors = [crew['name'] for crew in credits.get('crew', []) if crew['job'] == 'Director']
        else:
            # For TV shows, get creators from details
            directors = [creator['name'] for creator in details.get('created_by', [])]
        
        # If no directors found, try to get producers as fallback
        if not directors and is_movie:
            producers = [crew['name'] for crew in credits.get('crew', []) 
                        if crew['job'] in ['Producer', 'Executive Producer']]
            directors = producers[:1]  # Just take the first producer
        
        # STANDARDIZED BASELINE CALCULATIONS
        # Calculate consistent text metrics for perfect alignment
        text_bbox = draw.textbbox((0, 0), "Ag", font=font)  # Standard reference chars
        text_height = text_bbox[3] - text_bbox[1]
        text_baseline_y = start_y  # This will be our consistent baseline for ALL text
        
        # Restore original emoji sizes - different for each emoji as in original
        arts_size = int(text_height * 1.1)  # 110% of text height (original size)
        clapper_size = int(text_height * 0.9)  # 90% of text height (original size)
        
        # Restore original emoji positioning offsets
        arts_y_offset = (text_height - arts_size) // 2 + 8  # Original positioning
        clapper_y_offset = (text_height - clapper_size) // 2 + 8  # Original positioning
        
        current_x = 210
        
        # Add cast with performing arts emoji
        if top_cast:
            cast_text = ", ".join(top_cast)
            
            # Add performing arts emoji before cast
            script_dir = Path(__file__).parent
            performing_arts_path = script_dir / "1f3ad.png"
            
            if performing_arts_path.exists():
                try:
                    # Load and resize performing arts image with original size
                    performing_arts_img = Image.open(performing_arts_path).convert("RGBA")
                    performing_arts_img = performing_arts_img.resize((arts_size, arts_size), Image.Resampling.LANCZOS)
                    
                    # Convert to grayscale
                    r, g, b, a = performing_arts_img.split()
                    rgb_img = Image.merge('RGB', (r, g, b))
                    gray_img = rgb_img.convert('L')
                    arts_tinted = Image.merge('RGBA', (gray_img, gray_img, gray_img, a))
                    
                    # Position with original positioning
                    arts_x = current_x - 4
                    arts_y = text_baseline_y + arts_y_offset
                    img.paste(arts_tinted, (arts_x, arts_y), arts_tinted)
                    current_x = arts_x + arts_size + 12
                    
                except Exception as e:
                    print(f"❌ Failed to load performing arts image: {e}")
            else:
                print("❌ Performing arts image not found: 1f3ad.png")
            
            # Draw cast text at exact baseline
            self._draw_text_with_shadow(draw, (current_x, text_baseline_y), cast_text, font, (150, 150, 150))
            
            # Calculate position after cast text
            bbox = draw.textbbox((0, 0), cast_text, font=font)
            text_width = bbox[2] - bbox[0]
            current_x += text_width + 20  # 20px spacing
        
        # Add director with clapper board image
        if directors:
            # Add bullet separator if we have cast
            if top_cast:
                bullet_text = "•"
                bullet_x = current_x + 10
                # Draw bullet at exact same baseline
                self._draw_text_with_shadow(draw, (bullet_x, text_baseline_y), bullet_text, font, (150, 150, 150))
                bullet_bbox = draw.textbbox((0, 0), bullet_text, font=font)
                current_x = bullet_x + (bullet_bbox[2] - bullet_bbox[0]) + 36
            
            # Load clapper board image
            script_dir = Path(__file__).parent
            clapper_path = script_dir / "1f3ac.png"
            
            if clapper_path.exists():
                try:
                    # Load and resize clapper board image with original size
                    clapper_img = Image.open(clapper_path).convert("RGBA")
                    clapper_img = clapper_img.resize((clapper_size, clapper_size), Image.Resampling.LANCZOS)
                    
                    # Apply grayscale conversion
                    r, g, b, a = clapper_img.split()
                    rgb_img = Image.merge('RGB', (r, g, b))
                    gray_img = rgb_img.convert('L')
                    flattened_gray = gray_img.point(lambda x: int(x * 0.8 + 40))
                    clapper_tinted = Image.merge('RGBA', (flattened_gray, flattened_gray, flattened_gray, a))
                    
                    # Position with original positioning
                    clapper_x = current_x - 8
                    clapper_y = text_baseline_y + clapper_y_offset
                    img.paste(clapper_tinted, (clapper_x, clapper_y), clapper_tinted)
                    current_x = clapper_x + clapper_size + 13
                    
                    # Add director name
                    director_text = directors[0]
                    if len(directors) > 1:
                        director_text += f" +{len(directors) - 1}"
                    
                    self._draw_text_with_shadow(draw, (current_x, text_baseline_y), director_text, font, (150, 150, 150))
                    
                except Exception as e:
                    print(f"❌ Failed to load clapper board image: {e}")
                    # Fallback to text
                    director_text = f"Dir. {directors[0]}"
                    if len(directors) > 1:
                        director_text += f" +{len(directors) - 1}"
                    self._draw_text_with_shadow(draw, (current_x, text_baseline_y), director_text, font, (150, 150, 150))
            else:
                print("❌ Clapper board image not found: 1f3ac.png")
                # Fallback to text
                director_text = f"Dir. {directors[0]}"
                if len(directors) > 1:
                    director_text += f" +{len(directors) - 1}"
                self._draw_text_with_shadow(draw, (current_x, text_baseline_y), director_text, font, (150, 150, 150))
        
        return start_y + 55

    async def _add_title_or_logo(self, draw, img, item, logo_path, title_pos, font_title, info_pos, is_movie):
        """Add title text or logo with error handling"""
        if logo_path:
            logo_url = f"{IMAGE_BASE}{logo_path}"
            try:
                async with self.session.get(logo_url) as response:
                    if response.status == 200:
                        logo_data = await response.read()
                        if logo_data:
                            logo_img = Image.open(BytesIO(logo_data)).convert("RGBA")
                            logo_resized = self._resize_logo(logo_img, 1344, 672)
                            logo_y = info_pos[1] - logo_resized.height - 40
                            img.paste(logo_resized, (210, logo_y), logo_resized)
                            return
                        else:
                            print(f"⚠️  Empty logo data received")
                    else:
                        print(f"⚠️  Failed to download logo: HTTP {response.status}")
            except Exception as e:
                print(f"⚠️  Logo download failed: {e}")
        
        # Fallback to text title
        title = item.get("title" if is_movie else "name", "")
        if title:
            self._draw_text_with_shadow(draw, title_pos, title, font_title, "white")
        else:
            print(f"⚠️  No title available for fallback text")

    async def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get font with caching"""
        if size not in self.font_cache:
            try:
                async with self.session.get(FONT_URL) as response:
                    font_data = await response.read()
                self.font_cache[size] = ImageFont.truetype(BytesIO(font_data), size=size)
            except:
                self.font_cache[size] = ImageFont.load_default()
        return self.font_cache[size]

    def _draw_text_with_shadow(self, draw, pos, text, font, color, shadow_offset=2):
        """Draw text with shadow"""
        draw.text((pos[0] + shadow_offset, pos[1] + shadow_offset), text, font=font, fill="black")
        draw.text(pos, text, font=font, fill=color)

    def _resize_image(self, img: Image.Image, height: int) -> Image.Image:
        """Resize maintaining aspect ratio"""
        ratio = height / img.height
        return img.resize((int(img.width * ratio), height), Image.Resampling.LANCZOS)

    def _resize_logo(self, img: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Resize logo within bounds with smart sizing for small logos"""
        aspect = img.width / img.height
        
        # First, calculate what the logo size would be at the ORIGINAL bounds (1120x560)
        original_max_width, original_max_height = 1120, 560
        original_width, original_height = original_max_width, int(original_max_width / aspect)
        if original_height > original_max_height:
            original_height, original_width = original_max_height, int(original_max_height * aspect)
        
        # Detect if this is a "small" logo based on how much of the original space it uses
        # Small logos (like Foundation) use less than 70% of the original height
        height_usage_ratio = original_height / original_max_height
        is_small_logo = height_usage_ratio < 0.7
        
        if is_small_logo:
            # Small logo like Foundation - use the expanded bounds (20% larger)
            width, height = max_width, int(max_width / aspect)
            if height > max_height:
                height, width = max_height, int(max_height * aspect)
        else:
            # Large logo like John Wick - use the original smaller bounds
            width, height = original_width, original_height
        
        return img.resize((width, height), Image.Resampling.LANCZOS)

    def _clean_filename(self, filename: str) -> str:
        """Clean filename for filesystem"""
        return "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    generator = TMDBPosterGenerator()
    await generator.run()

if __name__ == "__main__":
    asyncio.run(main())
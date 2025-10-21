import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import os
import random
import time
import math
from typing import Dict, Any, List, Optional, Tuple

# --- BOT CONFIGURATION ---
# Mengambil Token dari Environment Variable (Wajib untuk Hosting seperti Replit/VPS)
TOKEN = os.environ.get('DISCORD_BOT_SECRET')
if not TOKEN:
    # Dalam lingkungan real, Anda harus menangani ini dengan aman.
    print("WARNING: DISCORD_BOT_SECRET not found. Bot will not run.")
    
# Gunakan 'R$' sebagai mata uang utama
CURRENCY_SYMBOL = "R$"
COOLDOWN_TIME = 30 # Cooldown untuk Auto Fishing

intents = discord.Intents.default()
# Wajib mengaktifkan message_content intent
intents.message_content = True 
bot = commands.Bot(command_prefix='/', intents=intents)

# Embed Colors based on Rarity (Hex Codes)
RARITY_COLORS = {
    "Secret": 0x7000FF,
    "Mythic": 0xFF0000,
    "Legendary": 0xFFC300,
    "Epic": 0x7D00A3,
    "Rare": 0x00FF00,
    "Uncommon": 0x00FFFF,
    "Common": 0xFFFFFF,
    "Failed": 0x000000
}

# --- USER DATA (Database Simulation) ---
USER_DATA: Dict[int, Dict[str, Any]] = {}
GLOBAL_EVENT_BOOST: Dict[str, Any] = {"luck_multiplier": 1, "is_active": False}


# --- STATIC DATA: ISLANDS, RODS, BAITS, AND FISH (UPDATED FOR SPECIFIC POOL) ---

ISLAND_DATA = {
    "Fisherman Island": {"price": 0, "unlock_level": 1},
    "Ocean": {"price": 500, "unlock_level": 2},
    "Kohana Island": {"price": 5000, "unlock_level": 3},
    "Kohana Volcano": {"price": 50000, "unlock_level": 4},
    "Coral Reefs": {"price": 200000, "unlock_level": 5},
    "Esoteric Depths": {"price": 1000000, "unlock_level": 6},
    "Tropical Grove": {"price": 5000000, "unlock_level": 7},
    "Crater Island": {"price": 8000000, "unlock_level": 8},
    "Lost Isle": {"price": 10000000, "unlock_level": 9},
    "Ancient Jungle": {"price": 25000000, "unlock_level": 10},
}
ISLAND_LIST = list(ISLAND_DATA.keys())


# Helper function to parse fish data and separate them by island
def parse_fish_data_by_island(fish_str: str) -> Dict[str, List[Dict[str, Any]]]:
    lines = fish_str.strip().split('\n')
    parsed_data: Dict[str, List[Dict[str, Any]]] = {}
    current_location = "Fisherman Island"
    
    secret_weights = {
        "Crystal Crab": (110520, 130960), "Orca": (115470, 126780),
        "Monster Shark": (130410, 165610), "Eerie Shark": (1010, 1830),
        "Great Whale": (90700, 116040), "Robot Kraken (Sisyphus)": (259820, 389730),
        "King Crab (Treasure Room)": (130520, 160960), "Kraken (Both)": (103530, 112800), 
        "Queen Crab (Treasure Room)": (130520, 160960), "Blob Shark": (532.2, 590.5), 
        "Ghost Shark": (1090, 1210), "Worm Fish": (106950, 112040),
        "Lochnes Monster": (260000, 295000), "Thin Armor Shark": (14150, 21230), 
        "Scare": (142330, 165100), "Frostborn Shark": (7520, 8440), 
        "Panther Eel": (90670, 113400), "Giant Squid": (103530, 112800),
        "King Jelly": (160000, 190000), "Mosasaurus Shark": (80750, 95880), 
        "Elshark Grand Maja": (450000, 520000), "Bone Whale": (230880, 275680), 
        "Ancient Whale": (310890, 355730),
    }

    location_map = {
        1: "Fisherman Island", 2: "Ocean", 3: "Kohana Island", 4: "Kohana Volcano",
        5: "Coral Reefs", 6: "Esoteric Depths", 7: "Tropical Grove", 8: "Crater Island",
        9: "Lost Isle", 10: "Ancient Jungle"
    }
    
    for line in lines:
        line = line.strip()
        if not line: continue

        parts = line.split(',')
        
        # Check for new location marker (e.g., '1. Fisherman Island')
        if parts[0].isdigit():
            try:
                location_id = int(parts[0].split('.')[0])
                if location_id in location_map:
                    current_location = location_map[location_id]
                    if len(parts) > 1 and parts[1].strip() in location_map.values():
                        continue
            except ValueError:
                pass
        
        # Parse the fish line
        if len(parts) >= 4:
            fish_name = parts[1].strip() if parts[0].strip() == '' else parts[0].strip()
            
            # Re-adjust parts if the location ID and name were in parts[0], parts[1]
            if fish_name in location_map.values():
                if len(parts) >= 5:
                    fish_name = parts[2].strip()
                    rarity = parts[3].strip()
                    chance_str = parts[4].strip()
                else: continue
            else:
                rarity = parts[-2].strip()
                chance_str = parts[-1].strip()

            # Skip header rows
            if fish_name.lower() in ["ikan", "orca"] and current_location != "Fisherman Island": 
                continue

            try:
                # Menghilangkan titik ribuan dan M/K untuk konversi float
                chance_str = chance_str.replace('.', '').replace('M', '000000').replace('K', '000').strip()
                catch_chance = float(chance_str)
            except ValueError:
                continue

            weight_min, weight_max = 1, 10 
            is_secret_weight = False
            
            clean_name = fish_name.replace('(Sisyphus)', '').replace('(Treasure Room)', '').replace('(Both)', '').strip()
            
            if rarity == "Secret" and clean_name in secret_weights:
                weight_min, weight_max = secret_weights[clean_name]
                is_secret_weight = True

            base_price_multiplier = catch_chance / 1000
            if rarity == "Secret": base_price_multiplier *= 10
            elif rarity == "Mythic": base_price_multiplier *= 5
            elif rarity == "Legendary": base_price_multiplier *= 2
            base_price = (catch_chance / 10000) * 1.5 + base_price_multiplier
            
            fish_data = {
                "name": fish_name, 
                "rarity": rarity, 
                "chance": catch_chance, 
                "weight_min": weight_min, 
                "weight_max": weight_max, 
                "is_secret_weight": is_secret_weight,
                "base_price": base_price
            }
            
            if current_location not in parsed_data:
                parsed_data[current_location] = []
            
            if fish_name not in [f['name'] for f in parsed_data[current_location]]:
                parsed_data[current_location].append(fish_data)
                
    return parsed_data

# The full fish list from the user's request
RAW_FISH_INPUT = """
1. Fisherman Island,Orca,Secret,1.500.000
,Crystal Crab,Secret,750.000
,Dotted Stingray,Mythic,91.000
,Yellowfin Tuna,Legendary,7.500
,Lined Cardinal Fish,Epic,5.500
,Unicorn Tang,Epic,4.500
,Dorhey Tang,Epic,1.000
,Darwin Clownfish,Rare,750
,Frog,Rare,350
,Ballina Angelfish,Rare,350
,Korean Angelfish,Rare,350
,Barracuda Fish,Rare,300
,Flame Angelfish,Uncommon,100
,Bandit Angelfish,Uncommon,65
,Yello Damselfish,Uncommon,50
,Gar Fish,Uncommon,50
,Sea Shell,Uncommon,50
,Conch Shell,Uncommon,50
,Copperband Butterfly,Common,20
,Strawberry Dotty,Common,20
,Herring Fish,Common,10
,Pygmy Goby,Common,6
,White Tand,Common,5
,Watanabei Angelfish,Common,4
,Old Boot,Common,3
,Azure Damsel,Common,2
,Clownfish,Common,2
2. Ocean,Hammerhead Shark,Mythic,100.000
,Manta Ray,Mythic,50.000
,Ruby,Legendary,15.000
,Chrome Tuna,Legendary,9.000
,Slurpfish Chromis,Legendary,8.000
,Diamond Ring,Legendary,5.000
,Moorish Idol,Epic,3.330
,Narwhal,Epic,2.000
,Expensive Chain,Epic,1.500
,Cow Clownfish,Epic,1.000
,Candy Butterfly,Rare,375
,Jewel Tang,Rare,250
,Vintage Damsel,Uncommon,135
,Tricolore Butterfly,Uncommon,70
,Blue-Banded Goby,Uncommon,50
,Fade Tang,Common,15
,Skunk Tilefish,Common,7
,Conspi Angelfish,Common,2
,Masked Angelfish,Common,2
,Vintage Blue Tang,Common,2
,Yellowstate Angelfish,Common,2
3. Kohana Island,Prismy Seahorse,Mythic,88.000
,Loggerhead Turtle,Mythic,55.000
,Lobster,Legendary,25.000
,Bumblebee Grouper,Legendary,5.000
,Longnose Butterfly,Epic,1.500
,Sushi Cardinal,Epic,1.250
,Kau Cardinal,Rare,750
,Fire Goby,Rare,250
,Banded Butterfly,Uncommon,125
,Blumato Clownfish,Uncommon,55
,Shrimp Goby,Uncommon,50
,Sea Shell,Uncommon,50
,Conch Shell,Uncommon,50
,Boa Angelfish,Common,15
,Zoster Butterfly,Common,8
,Jennifer Dottyback,Common,2
,Reef Chromis,Common,2
4. Kohana Volcano,Magma Shark,Mythic,200.000
,Blueflame Ray,Mythic,93.000
,Lavafin Tuna,Legendary,10.000
,Firecoal Damsel,Epic,2.500
,Volsail Tang,Rare,300
,Rockform Cardinal,Rare,250
,Lava Butterfly,Uncommon,125
,Magma Goby,Uncommon,55
,Arowana,Uncommon,50
,Volcanic Basslet,Common,2
5. Coral Reefs,Monster Shark,Secret,2.500.000
,Eerie Shark,Secret,250.000
,Hawks Turtle,Mythic,75.000
,Blue Lobster,Legendary,25.000
,Greenbee Grouper,Legendary,6.000
,Pink Dolphin,Legendary,5.000
,Starjam Tang,Legendary,5.000
,Domino Damsel,Epic,1.500
,Panther Grouper,Epic,1.000
,Starfish,Rare,300
,Scissortail Dartfish,Rare,300
,White Clownfish,Rare,250
,Maze Angelfish,Uncommon,125
,Lion Fish,Uncommon,100
,Tricolore Butterfly,Uncommon,70
,Wahoo,Uncommon,65
,Flying Fish,Uncommon,50
,Flat Fish,Uncommon,50
,Salmon,Uncommon,50
,Sea Shell,Uncommon,50
,Conch Shell,Uncommon,50
,Orangy Goby,Common,7
,Sail Tang,Common,5
,Specked Butterfly,Common,2
,Corazon Damsel,Common,2
6. Esoteric Depths,Abyss Seahorse,Mythic,95.000
,Magic Tang,Legendary,7.500
,Enchanted Angelfish,Legendary,5.000
,Astra Damsel,Epic,2.000
,Charmed Tang,Rare,325
,Dark Tentacle,Rare,300
,Coal Tang,Uncommon,50
,Rockfish,Uncommon,50
,Ash Basslet,Common,2
7. Tropical Grove,Great Whale,Secret,900.000
,Thresher Shark,Mythic,95.000
,Ruby,Legendary,15.000
,Pufferfish,Epic,1.500
,King Mackarel,Rare,300
,Scissortail Dartfish,Rare,300
,Racoon Butterfly Fish,Uncommon,50
,Orange Basslet,Uncommon,50
8. Crater Island,Axolotl,Legendary,6.500
,Coney Fish,Rare,300
,Sheepshead Fish,Rare,300
,Catfish,Rare,300
,Silver Tuna,Uncommon,60
,Blackcap Basslet,Uncommon,50
,Parrot Fish,Uncommon,50
,Red Snapper,Uncommon,50
,Pilot Fish,Uncommon,50
9. Lost Isle,Robot Kraken (Sisyphus),Secret,3.500.000
,King Crab (Treasure Room),Secret,1.200.000
,Kraken (Both),Secret,800.000
,Queen Crab (Treasure Room),Secret,800.000
,Blob Fish (Both),Mythic,50.000
,Ruby,Legendary,15.000
,Synodontis (Both),Legendary,5.000
,Deep Sea Crab (Both),Legendary,5.000
,Angler Fish (Both),Epic,3.000
,Monk Fish (Both),Epic,3.000
,Vampire Squid (Both),Epic,3.000
,Antique Watch (Treasure Room),Epic,1.500
,Pearl (Sisyphus Statue),Rare,300
,Jellyfish (Both),Rare,300
,Spotted Lantern Fish (Both),Uncommon,50
,Viperfish (Both),Uncommon,50
,Swordfish (Treasure Room),Uncommon,50
,Dark Eel (Sisyphus Statue),Uncommon,50
,Skeleton Fish (Treasure Room),Common,10
,Dead Fish (Treasure Room),Common,4
,Boar Fish (Sisyphys Statue),Common,2
,Electric Eel (Sisyphys Statue),Common,2
10. Ancient Jungle,Ancient Relic Crocodile,Mythic,245.000
,Crocodile,Mythic,245.000
,Skeleton Angler Fish,Mythic,3.000
,Spear Guardian,Mythic,1.000
,Goliath Tiger,Mythic,1.000
,Temple Spokes Tuna,Legendary,5.000
,Manoai Statue Fish,Legendary,5.000
,Viperagnler Fish,Rare,300
,Parrot Fish,Rare,300
,Mossy Fishlet,Rare,300
,Freshwater Piranha,Rare,300
,Zebra Snakehead,Uncommon,150
,Red Goatfish,Uncommon,100
,Water Snake,Uncommon,50
,Sail Fish,Uncommon,50
,Drippy Tucanare,Uncommon,50
,Abyshorn Fish,Uncommon,50
,Ancient Arapaima,Uncommon,50
,Waveback Fish,Common,2
,Runic Wispeye,Common,2
,Beanie Leedsicheye,Common,2
"""

# GLOBAL POOL for easy reference, but fishing will use the specific pool
FISH_POOL_BY_ISLAND = parse_fish_data_by_island(RAW_FISH_INPUT)


ROD_DATA = {
    "Starter Rod": {"rarity": "Common", "luck_bonus": 0, "speed_bonus": 0, "max_weight_kg": 10, "price": 0, "max_ench_level": 5},
    "Luck Rod": {"rarity": "Common", "luck_bonus": 50, "speed_bonus": 0, "max_weight_kg": 15, "price": 150, "max_ench_level": 7},
    "Carbon Rod": {"rarity": "Common", "luck_bonus": 30, "speed_bonus": 4, "max_weight_kg": 20, "price": 500, "max_ench_level": 10},
    "Toy Rod": {"rarity": "Common", "luck_bonus": 30, "speed_bonus": 3, "max_weight_kg": 18, "price": 0, "max_ench_level": 5},
    "Lava Rod": {"rarity": "Uncommon", "luck_bonus": 30, "speed_bonus": 2, "max_weight_kg": 100, "price": 0, "max_ench_level": 12},
    "Lucky Rod": {"rarity": "Rare", "luck_bonus": 130, "speed_bonus": 7, "max_weight_kg": 5000, "price": 15000, "max_ench_level": 15},
    "Steampunk Rod": {"rarity": "Epic", "luck_bonus": 175, "speed_bonus": 19, "max_weight_kg": 25000, "price": 125000, "max_ench_level": 20},
    "Hazmat Rod": {"rarity": "Legendary", "luck_bonus": 380, "speed_bonus": 32, "max_weight_kg": 300000, "price": 1300000, "max_ench_level": 30},
    "Angler Rod": {"rarity": "Mythic", "luck_bonus": 530, "speed_bonus": 71, "max_weight_kg": 500000, "price": 8000000, "max_ench_level": 40},
    "Bamboo Rod": {"rarity": "Mythic", "luck_bonus": 760, "speed_bonus": 98, "max_weight_kg": 500000, "price": 12000000, "max_ench_level": 50},
    "Ghostfinn Rod": {"rarity": "Mythic", "luck_bonus": 610, "speed_bonus": 118, "max_weight_kg": 600000, "price": 0, "max_ench_level": 60},
    "Element Rod": {"rarity": "Secret", "luck_bonus": 1111, "speed_bonus": 130, "max_weight_kg": 900000, "price": 0, "max_ench_level": 100},
}

BAIT_DATA = {
    "Starter Bait": {"luck_bonus": 0, "price": 100},
    "Topwater Bait": {"luck_bonus": 0, "price": 100},
    "Luck Bait": {"luck_bonus": 10, "price": 1000},
    "Midnight Bait": {"luck_bonus": 20, "price": 3500},
    "Beach Ball Bait": {"luck_bonus": 5, "price": 0},
    "Nature Bait": {"luck_bonus": 45, "price": 83000},
    "Gold Bait": {"luck_bonus": 25, "price": 0},
    "Hyper Bait": {"luck_bonus": 40, "price": 0},
    "Chroma Bait": {"luck_bonus": 100, "price": 290000},
    "Royal Bait": {"luck_bonus": 130, "price": 425000},
    "Dark Matter Bait": {"luck_bonus": 160, "price": 630000},
    "Corrupt Bait": {"luck_bonus": 200, "price": 1150000},
    "Aether Bait": {"luck_bonus": 240, "price": 3700000},
    "Floral Bait": {"luck_bonus": 320, "price": 4000000},
    "Singularity Bait": {"luck_bonus": 380, "price": 8200000},
}

# --- QUEST DATA ---
QUEST_DATA = {
    "Lava Rod Quest": {"type": "catch_rarity", "rarity": "Rare", "goal": 3, "reward_item": "Lava Rod", "title": "Kohana Quest: Catch 3 Rare Fish"},
    "Ghostfinn Rod Quest": {"type": "catch_rarity", "rarity": "Mythic", "goal": 3, "reward_item": "Ghostfinn Rod", "title": "Deep Sea Quest: Catch 3 Mythic Fish"},
    "Element Rod Quest": {"type": "catch_rarity", "rarity": "Secret", "goal": 1, "reward_item": "Element Rod", "title": "Final Trial: Catch 1 Secret Fish"},
    "daily_1": {"type": "catch_rarity", "rarity": "Common", "goal": 5, "reward_koin": 500, "title": "Daily: Catch 5 Common Fish"},
    "daily_2": {"type": "sell_count", "goal": 10, "reward_koin": 1000, "title": "Daily: Sell 10 Fish"},
}


# --- UTILITY FUNCTIONS ---

def get_user_stats(user_id):
    if user_id not in USER_DATA:
        initial_progress = {q_id: 0 for q_id in QUEST_DATA if q_id.endswith("Quest")}
        
        USER_DATA[user_id] = {
            "koin": 500.0,
            "current_rod": "Starter Rod",
            "current_bait": "Starter Bait",
            "location": "Fisherman Island",
            "unlocked_islands": ["Fisherman Island"],
            "last_fished": 0,
            "inventory": {}, 
            "owned_rods": ["Starter Rod"], 
            "owned_baits": ["Starter Bait"], 
            "rod_enchantment": {"Starter Rod": 0},
            "quest_progress": initial_progress, 
            "daily_quests": generate_daily_quests(),
            "last_daily_reset": time.time(),
        }
    
    if time.time() - USER_DATA[user_id]["last_daily_reset"] > 24 * 3600:
        USER_DATA[user_id]["daily_quests"] = generate_daily_quests()
        USER_DATA[user_id]["last_daily_reset"] = time.time()

    return USER_DATA[user_id]

def generate_daily_quests():
    pool = [data for q_id, data in QUEST_DATA.items() if q_id.startswith("daily_")]
    return {
        f"daily_{i}": {**random.choice(pool), "progress": 0, "claimed": False}
        for i in range(3)
    }

def calculate_total_luck(user_stats):
    rod = ROD_DATA.get(user_stats["current_rod"], ROD_DATA["Starter Rod"])
    bait = BAIT_DATA.get(user_stats["current_bait"], BAIT_DATA["Starter Bait"])
    
    ench_level = user_stats["rod_enchantment"].get(user_stats["current_rod"], 0)
    ench_luck = ench_level * 10 
    
    total_luck = rod["luck_bonus"] + bait["luck_bonus"] + ench_luck
    
    total_luck *= GLOBAL_EVENT_BOOST["luck_multiplier"]
    
    return int(total_luck)

def update_quest_progress(user_stats, trigger_type, value=None, item_name=None, rarity=None):
    # Quest Rod (Permanent)
    for q_id, q_data in QUEST_DATA.items():
        if q_id.endswith("Quest"):
            progress = user_stats["quest_progress"].get(q_id, 0)
            if progress < q_data["goal"]: 
                if q_data["type"] == "catch_rarity" and trigger_type == "catch" and rarity == q_data["rarity"]:
                    # Logic: Element Rod Quest hanya bisa di-progress setelah punya Ghostfinn
                    if q_id == "Element Rod Quest" and "Ghostfinn Rod" not in user_stats["owned_rods"]:
                        continue
                        
                    user_stats["quest_progress"][q_id] = min(user_stats["quest_progress"].get(q_id, 0) + (value or 1), q_data["goal"])

    # Daily Quests
    for q_id, q_data in user_stats["daily_quests"].items():
        if not q_data["claimed"] and q_data["progress"] < q_data["goal"]:
            if q_data["type"] == "catch_rarity" and trigger_type == "catch" and rarity == q_data["rarity"]:
                q_data["progress"] = min(q_data["progress"] + (value or 1), q_data["goal"])
            elif q_data["type"] == "sell_count" and trigger_type == "sell":
                q_data["progress"] = min(q_data["progress"] + value, q_data["goal"])
                
def check_quest_completion(user_stats):
    completed_count = 0
    
    # Quest Rod (Permanent)
    for q_id, q_data in QUEST_DATA.items():
         if q_id.endswith("Quest"):
            progress = user_stats["quest_progress"].get(q_id, 0)
            # 1.5 menandakan sudah completed tapi belum diklaim (jika 1.5 = sudah diklaim)
            if progress >= q_data["goal"] and progress < q_data["goal"] + 0.5: 
                completed_count += 1
                
    # Daily Quests
    for q_id, q_data in user_stats["daily_quests"].items():
        if q_data["progress"] >= q_data["goal"] and not q_data["claimed"]:
            completed_count += 1
            
    return completed_count

def perform_fishing(user_stats):
    total_luck = calculate_total_luck(user_stats)
    current_location = user_stats["location"]
    
    fish_pool_location = FISH_POOL_BY_ISLAND.get(current_location, [])
    
    if not fish_pool_location: 
        return "Failed", f"No fish data found for **{current_location}**.", "0.00", "Failed", 0.00
        
    choices = []
    weights = []
    
    for fish in fish_pool_location:
        base_chance = fish["chance"]
        
        # Formula untuk Adjusted Weight: Luck mempengaruhi peluang mendapatkan ikan langka.
        # Semakin kecil base_chance (semakin langka), semakin besar bobotnya jika luck tinggi.
        adjusted_weight = (1 / base_chance) * (1 + (total_luck / 100))
        
        choices.append(fish)
        weights.append(adjusted_weight)
    
    # Pilih ikan berdasarkan weights
    chosen_fish = random.choices(choices, weights=weights, k=1)[0]
    
    # Tentukan berat ikan
    weight_kg = random.uniform(chosen_fish["weight_min"], chosen_fish["weight_max"])
    
    rod_data = ROD_DATA.get(user_stats["current_rod"])
    max_rod_weight = rod_data["max_weight_kg"]
    
    # Weight Check (Gagal Tarik)
    if weight_kg > max_rod_weight:
        update_quest_progress(user_stats, "catch", value=1, rarity=chosen_fish["rarity"]) 
        return "Failed", f"LOST IT! The **{chosen_fish['name']}**'s weight ({weight_kg:,.2f} kg) exceeded your **{user_stats['current_rod']}** capacity ({max_rod_weight:,} kg). You need a stronger Rod to catch this {chosen_fish['rarity']} fish!", f"{weight_kg:,.2f}", chosen_fish["rarity"], 0.00

    # Success
    weight_ratio = max(1.0, float(weight_kg) / float(chosen_fish["weight_min"]))
    coins_earned = chosen_fish["base_price"] * weight_ratio
    
    user_stats["koin"] += coins_earned
    fish_name = chosen_fish['name']
    user_stats["inventory"][fish_name] = user_stats["inventory"].get(fish_name, 0) + 1
    
    update_quest_progress(user_stats, "catch", value=1, rarity=chosen_fish["rarity"])

    return "Success", chosen_fish, f"{weight_kg:,.2f}", chosen_fish["rarity"], coins_earned


# --- DISCORD BOT VIEWS (Interactions) ---
class BackView(View):
    def __init__(self, user_id, bot_instance, timeout=120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.bot = bot_instance

    @discord.ui.button(label="↩️ Main Menu", style=discord.ButtonStyle.secondary, row=4)
    async def back_to_main_menu(self, button: Button, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This is not your menu!", ephemeral=True)
        
        main_view = MainMenuView(self.user_id, self.bot)
        await interaction.response.edit_message(
            embed=main_view.create_main_embed(), 
            view=main_view
        )

class MainMenuView(BackView):
    def __init__(self, user_id, bot_instance):
        super().__init__(user_id, bot_instance)
        self.clear_items() 

        self.add_item(Button(label="🎣 Auto Fishing", custom_id="main_fish", style=discord.ButtonStyle.green)) 
        
        self.add_item(Button(label="🌍 Travel", custom_id="main_travel", style=discord.ButtonStyle.blurple))
        self.add_item(Button(label="🏪 Shop & Sell", custom_id="main_shop", style=discord.ButtonStyle.blurple))
        self.add_item(Button(label="⚙️ Equip & Upgrade", custom_id="main_equip", style=discord.ButtonStyle.blurple))

        self.add_item(Button(label="⭐ Quests", custom_id="main_quests", style=discord.ButtonStyle.red))
        self.add_item(Button(label="🏆 Leaderboard", custom_id="main_top", style=discord.ButtonStyle.red))
        self.add_item(Button(label="👤 Profile", custom_id="main_profile", style=discord.ButtonStyle.grey))
        
        # Tambahkan callback untuk semua tombol di Main Menu
        for item in self.children:
            if isinstance(item, Button) and item.custom_id.startswith("main_"):
                item.callback = self.main_menu_callback

    def create_main_embed(self):
        user_stats = get_user_stats(self.user_id)
        embed = discord.Embed(
            title="🐠 Welcome to the Auto Fishing Bot!",
            description="Use the buttons below to manage your automated fishing journey.",
            color=0x4169E1
        )
        
        embed.add_field(name=f"💰 Money ({CURRENCY_SYMBOL})", value=f"**{CURRENCY_SYMBOL}{user_stats['koin']:,.2f}**", inline=True)
        embed.add_field(name="📍 Location", value=user_stats['location'], inline=True)
        
        completed = check_quest_completion(user_stats)
        luck_text = f"Total Luck: {calculate_total_luck(user_stats)}%"
        if GLOBAL_EVENT_BOOST["is_active"]:
            luck_text += f" (Event x{GLOBAL_EVENT_BOOST['luck_multiplier']:.0f})"

        if completed > 0:
            embed.set_footer(text=f"⭐ {completed} Quests Ready to Claim! Press 'Quests' button. | {luck_text}")
        else:
            embed.set_footer(text=f"{luck_text} | Happy Fishing!")
            
        return embed
    
    async def main_menu_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This is not your menu!", ephemeral=True)
        
        custom_id = interaction.data['custom_id']
        user_stats = get_user_stats(self.user_id)
        
        if custom_id == "main_fish":
            fish_view = AutoFishingView(self.user_id, self.bot)
            await interaction.response.edit_message(
                embed=fish_view.create_fishing_embed(user_stats),
                view=fish_view
            )
        elif custom_id == "main_travel":
            travel_view = TravelView(self.user_id, self.bot)
            await interaction.response.edit_message(
                embed=travel_view.create_travel_embed(user_stats),
                view=travel_view
            )
        # TODO: Implement remaining menu options (Shop, Equip, Quests, etc.)
        else:
            await interaction.response.send_message(f"Feature '{custom_id.replace('main_', '').title()}' not implemented yet.", ephemeral=True)


class TravelLocationSelect(Select):
    def __init__(self, user_stats, user_id):
        options = [
            discord.SelectOption(label=name, value=name, default=(name == user_stats['location']))
            for name in user_stats["unlocked_islands"]
        ]
        super().__init__(placeholder="Set current location to fish...", options=options, custom_id="set_fishing_location", row=1)
        self.user_id = user_id
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return await interaction.response.send_message("Not your menu!", ephemeral=True)
        user_stats = get_user_stats(self.user_id)
        new_location = self.values[0]
        user_stats["location"] = new_location
        
        travel_view = TravelView(self.user_id, interaction.client)
        await interaction.response.edit_message(embed=travel_view.create_travel_embed(user_stats), view=travel_view)
        await interaction.followup.send(f"📍 Lokasi memancing diatur ke **{new_location}**! Siap untuk tantangan ikan lokal.", ephemeral=True)


class TravelView(BackView):
    def __init__(self, user_id, bot_instance):
        super().__init__(user_id, bot_instance, timeout=300)
        self.update_items()
        
    def create_travel_embed(self, user_stats):
        embed = discord.Embed(
            title="🌍 Travel to New Fishing Grounds",
            description=f"Unlock new islands to access their unique fish pools and shop items. You are currently at **{user_stats['location']}**.",
            color=0x3CB371
        )
        embed.add_field(name="Your Money", value=f"**{CURRENCY_SYMBOL}{user_stats['koin']:,.2f}**", inline=False)
        
        island_list = []
        for name, data in ISLAND_DATA.items():
            status = "✅ UNLOCKED" if name in user_stats["unlocked_islands"] else f"🔒 LOCKED ({CURRENCY_SYMBOL}{data['price']:,.2f})"
            pool = FISH_POOL_BY_ISLAND.get(name, [])
            max_rarity = max([f['rarity'] for f in pool]) if pool else "N/A"
            island_list.append(f"**{name}** (Max Rarity: {max_rarity}) | {status}")
            
        embed.add_field(name="Available Islands", value="\n".join(island_list), inline=False)
        return embed

    def update_items(self):
        self.clear_items()
        user_stats = get_user_stats(self.user_id)
        
        next_island_to_unlock = None
        for island_name in ISLAND_LIST:
            if island_name not in user_stats["unlocked_islands"]:
                next_island_to_unlock = island_name
                break
        
        if next_island_to_unlock:
            data = ISLAND_DATA[next_island_to_unlock]
            self.add_item(Button(
                label=f"Unlock {next_island_to_unlock} ({CURRENCY_SYMBOL}{data['price']:,})",
                custom_id="travel_buy_next",
                style=discord.ButtonStyle.primary,
                row=0
            ))
        
        unlocked_options = [
            discord.SelectOption(label=name, value=name, default=(name == user_stats['location']))
            for name in user_stats["unlocked_islands"]
        ]
        if unlocked_options:
            self.add_item(TravelLocationSelect(user_stats, self.user_id))
            
        super().add_item(super().back_to_main_menu)

    @discord.ui.button(label="Buy Next Island", custom_id="travel_buy_next", style=discord.ButtonStyle.primary, row=0)
    async def travel_buy_callback(self, button: Button, interaction: discord.Interaction):
        # Callback logic is correct as provided in your initial code
        if interaction.user.id != self.user_id: return await interaction.response.send_message("Not your menu!", ephemeral=True)
        user_stats = get_user_stats(self.user_id)
        
        next_island_to_unlock = None
        for island_name in ISLAND_LIST:
            if island_name not in user_stats["unlocked_islands"]:
                next_island_to_unlock = island_name
                break
        
        if not next_island_to_unlock:
            return await interaction.response.send_message("❌ You have unlocked all islands!", ephemeral=True)
            
        island_data = ISLAND_DATA[next_island_to_unlock]
        price = island_data["price"]
        
        if user_stats["koin"] < price:
            return await interaction.response.send_message(f"❌ Not enough coins! You need **{CURRENCY_SYMBOL}{price:,.2f}** to unlock **{next_island_to_unlock}**.", ephemeral=True)

        user_stats["koin"] -= price
        user_stats["unlocked_islands"].append(next_island_to_unlock)
        user_stats["location"] = next_island_to_unlock
        
        new_view = TravelView(self.user_id, self.bot)
        await interaction.response.edit_message(embed=new_view.create_travel_embed(user_stats), view=new_view)
        await interaction.followup.send(f"🎉 Unlocked and traveled to **{next_island_to_unlock}** for **{CURRENCY_SYMBOL}{price:,.2f}**! New challenges await!", ephemeral=True)


# --- Fish Implementation (Auto Fishing) ---
class AutoFishingView(BackView):
    COOLDOWN_TIME = 30 

    def __init__(self, user_id, bot_instance):
        super().__init__(user_id, bot_instance, timeout=300)
        self.clear_items()
        
        user_stats = get_user_stats(user_id)
        # Tentukan status tombol berdasarkan cooldown
        is_cooldown = time.time() - user_stats["last_fished"] < self.COOLDOWN_TIME
        
        self.auto_fish_button = Button(
            label="🎣 Reel In (Auto Fish)!", 
            custom_id="auto_fish_button", 
            style=discord.ButtonStyle.green, 
            row=0,
            disabled=is_cooldown
        )
        
        self.add_item(self.auto_fish_button)
        super().add_item(super().back_to_main_menu)
        
        # Tambahkan fungsi callback
        self.auto_fish_button.callback = self.auto_fish_callback
        
    def create_fishing_embed(self, user_stats):
        embed = discord.Embed(
            title="🎣 Auto Fishing Management",
            description=f"You are currently fishing at **{user_stats['location']}** with **{user_stats['current_rod']}** and **{user_stats['current_bait']}**.",
            color=0x4169E1
        )
        remaining = max(0, self.COOLDOWN_TIME - (time.time() - user_stats["last_fished"]))
        
        embed.add_field(name="Cooldown Status", value=f"⏱️ Next Catch: **{remaining:.1f} seconds**", inline=False)
        embed.add_field(name="Current Luck", value=f"✨ {calculate_total_luck(user_stats)}%", inline=True)
        embed.add_field(name="Current Money", value=f"💰 {CURRENCY_SYMBOL}{user_stats['koin']:,.2f}", inline=True)
        
        return embed

    async def auto_fish_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("This is not your fishing pole!", ephemeral=True)
            
        user_stats = get_user_stats(self.user_id)
        
        if time.time() - user_stats["last_fished"] < self.COOLDOWN_TIME:
            remaining = self.COOLDOWN_TIME - (time.time() - user_stats["last_fished"])
            return await interaction.response.send_message(f"Your line is still out! Wait **{remaining:.1f}** seconds for the next catch.", ephemeral=True)
        
        user_stats["last_fished"] = time.time()
        
        status, result_data, weight, rarity, coins_earned = perform_fishing(user_stats)
        
        # Disable button while on cooldown
        self.auto_fish_button.disabled = True
        
        embed = discord.Embed(title=f"🎣 Auto Fishing Catch at {user_stats['location']}!", 
                              color=RARITY_COLORS.get(rarity, 0x000000))
        
        if status == "Success":
            fish_name = result_data['name']

            embed.description = f"🎉 **{rarity.upper()}!** You auto-reeled in a **{fish_name}**!"
            embed.add_field(name="Result", 
                            value=(f"**Rarity:** {rarity}\n"
                                   f"**Weight:** {weight} kg\n"
                                   f"**Reward:** **{CURRENCY_SYMBOL}{coins_earned:,.2f}**"), 
                            inline=False)
        else: # Failed
            embed.description = status
            embed.add_field(name="Weight Lost", value=f"**{weight} kg**", inline=False)
            embed.color = RARITY_COLORS["Failed"]
        
        completed_quests = check_quest_completion(user_stats)
        luck_text = f"Total Luck: {calculate_total_luck(user_stats)}%"
        if GLOBAL_EVENT_BOOST["is_active"]:
            luck_text += f" (Event x{GLOBAL_EVENT_BOOST['luck_multiplier']:.0f})"
        
        footer_text = f"{luck_text} | Next catch in {self.COOLDOWN_TIME}s."
        if completed_quests > 0:
             footer_text = f"⭐ {completed_quests} Quests Ready! | " + footer_text
             
        embed.set_footer(text=footer_text)
        
        # Update embed dan view
        await interaction.response.edit_message(embed=self.create_fishing_embed(user_stats), view=self)
        
        # Kirim hasil pancingan sebagai follow-up message (Visible ke semua orang)
        await interaction.followup.send(embed=embed)

        # Re-enable the button after cooldown (Ini perlu loop atau task, tapi kita pakai cara sederhana)
        # Karena kita menggunakan edit_message, kita akan mengandalkan user untuk menekan lagi setelah cooldown habis.


# --- BOT EVENTS & COMMANDS ---

@bot.event
async def on_ready():
    """Dipanggil saat bot berhasil login."""
    print(f'Bot is ready. Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name=f"R$ Fishing | /menu"))
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="menu", description="Membuka Menu Utama Bot Memancing Interaktif.")
async def menu_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    # Memastikan user stats terinisialisasi
    get_user_stats(user_id) 
    
    main_view = MainMenuView(user_id, bot)
    await interaction.response.send_message(
        embed=main_view.create_main_embed(), 
        view=main_view,
        ephemeral=True # Hanya bisa dilihat oleh pengguna (disarankan untuk menu)
    )

# --- RUN BOT ---

# Untuk Replit: Anda harus mengimpor dan memanggil keep_alive di sini
# from keep_alive import keep_alive
# keep_alive()

if TOKEN:
    bot.run(TOKEN)
else:
    print("FATAL ERROR: Bot tidak dapat dijalankan karena Token Discord tidak ditemukan.")

import json
import argparse
import math
import re
from bs4 import BeautifulSoup

def _get_modifier_text(score):
    """Calculates and returns the D&D 5e ability modifier text."""
    if not isinstance(score, (int, float)):
        return ''
    modifier = math.floor((score - 10) / 2)
    return f"({'+' if modifier >= 0 else ''}{modifier})"

def _calculate_xp_and_pb(cr_str):
    """Calculates XP and Proficiency Bonus based on Challenge Rating."""
    cr_to_xp = {
        "0": 10, "1/8": 25, "1/4": 50, "1/2": 100,
        "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800,
        "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900,
        "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
        "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
        "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000,
        "26": 90000, "27": 105000, "28": 120000, "29": 135000, "30": 155000
    }
    
    # Proficiency Bonus based on CR ranges
    cr_to_pb = {
        (0, 4): 2, (5, 8): 3, (9, 12): 4, (13, 16): 5,
        (17, 20): 6, (21, 24): 7, (25, 28): 8, (29, 30): 9
    }

    xp = cr_to_xp.get(cr_str, 'N/A')
    
    pb = 'N/A'
    try:
        cr_val_str = str(cr_str)
        if '/' in cr_val_str:
            cr_val = float(eval(cr_val_str)) # Handles fractions like "1/4"
        else:
            cr_val = float(cr_val_str)

        for (min_cr, max_cr), bonus in cr_to_pb.items():
            if min_cr <= cr_val <= max_cr:
                pb = bonus
                break
        if pb == 'N/A' and cr_val > 30: # For CRs higher than 30, estimate PB
            pb = math.ceil((cr_val - 10) / 4) + 4 # A common extended rule
            if pb < 9: pb = 9 # Ensure it doesn't go below known max
            
    except (ValueError, TypeError, ZeroDivisionError):
        pass # PB remains 'N/A' or default

    return xp, pb


def _generate_header_html(monster_data):
    """Generates the HTML for the monster header."""
    name = monster_data.get('name', 'Unnamed Monster')
    size = monster_data.get('size', 'Unknown')
    m_type = monster_data.get('type', 'creature')
    subtype = f" ({monster_data['subtype'].replace('any race', 'any race').title()})" if monster_data.get('subtype') else ''
    alignment = monster_data.get('alignment', 'unaligned')

    return f"""
<div class="mon-stat-block__header" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; line-height: 1.1; background-color: rgb(255, 255, 255);">
    <div class="mon-stat-block__name" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold; font-size: 34px; font-family: MrsEavesSmallCaps, Roboto, Helvetica, sans-serif; color: rgb(130, 32, 0);">
        <span class="mon-stat-block__name-link" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(130, 32, 0); text-decoration: none;">{name}</span>
    </div>
    <div class="mon-stat-block__meta" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-style: italic; margin-bottom: 15px;">{size} {m_type.title()}{subtype}, {alignment}</div>
</div>
"""

def _generate_attributes_html(monster_data):
    """Generates the HTML for AC, HP, and Speed attributes."""
    hp_extra = ""
    if monster_data.get('hit_dice') and monster_data.get('constitution') is not None:
        try:
            num_dice_str = monster_data['hit_dice'].split('d')[0]
            num_dice = int(num_dice_str)
            con_mod = math.floor((int(monster_data['constitution']) - 10) / 2)
            calculated_hp_bonus = num_dice * con_mod
            if calculated_hp_bonus > 0:
                 hp_extra = f" ({monster_data['hit_dice']} + {calculated_hp_bonus})"
            elif calculated_hp_bonus < 0:
                 hp_extra = f" ({monster_data['hit_dice']} - {abs(calculated_hp_bonus)})"
            else: # If bonus is 0, just show hit dice
                 hp_extra = f" ({monster_data['hit_dice']})"
        except (ValueError, TypeError):
            hp_extra = f" ({monster_data.get('hit_dice', 'N/A')})" # Fallback if parsing hit_dice or con fails
    elif monster_data.get('hit_dice'):
        hp_extra = f" ({monster_data['hit_dice']})"


    return f"""
<div class="mon-stat-block__attributes" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Armor Class</span>&nbsp;<span class="mon-stat-block__attribute-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('armor_class', 'N/A')}&nbsp;</span><span class="mon-stat-block__attribute-data-extra" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"></span></span>
    </div>
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Hit Points</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="mon-stat-block__attribute-data-value" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('hit_points', 'N/A')}&nbsp;</span><span class="mon-stat-block__attribute-data-extra" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{hp_extra}</span></span>
    </div>
    <div class="mon-stat-block__attribute" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__attribute-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Speed</span>&nbsp;<span class="mon-stat-block__attribute-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data.get('speed', 'N/A')}</span>
    </div>
</div>
"""

def _generate_ability_scores_html_for_main_block(monster_data):
    """
    Generates the HTML for the ability scores block,
    specifically for the main stat block HTML.
    """
    abilities_html = ""
    ability_order = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']

    for stat in ability_order:
        score = monster_data.get(stat, 'N/A')
        mod_text = _get_modifier_text(score)
        stat_abbr = stat[:3].upper()
        
        abilities_html += f"""
<div class="ability-block__stat ability-block__stat--{stat_abbr.lower()}" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; width: 59.1667px; padding: 5px 0px; text-align: center;">
    <div class="ability-block__heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{stat_abbr}</div>
    <div class="ability-block__data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><span class="ability-block__score" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{score}</span>&nbsp;<span class="ability-block__modifier" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-left: 2px;">{mod_text}</span></div>
</div>"""
    return abilities_html


def _generate_tidbits_html(monster_data):
    """Generates HTML for saving throws, skills, senses, languages, and CR/PB."""
    tidbits_html = []

    # Saving Throws
    save_throws = []
    for stat in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
        save_key = f"{stat}_save"
        if monster_data.get(save_key) is not None and str(monster_data[save_key]).strip():
            save_throws.append(f"{stat[:3].upper()} +{monster_data[save_key]}")
    if save_throws:
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Saving Throws</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{', '.join(save_throws)}</span>
</div>""")

    # Skills
    skills = []
    skill_mapping = {
        'history': 'History', 'perception': 'Perception', 'stealth': 'Stealth',
        'insight': 'Insight', 'persuasion': 'Persuasion', 'medicine': 'Medicine',
        'religion': 'Religion', 'athletics': 'Athletics', 'acrobatics': 'Acrobatics',
        'sleight_of_hand': 'Sleight of Hand', 'arcana': 'Arcana', 'investigation': 'Investigation',
        'nature': 'Nature', 'performance': 'Performance', 'intimidation': 'Intimidation',
        'survival': 'Survival', 'deception': 'Deception', 'animal_handling': 'Animal Handling'
    }

    for key, display_name in skill_mapping.items():
        if monster_data.get(key) is not None and str(monster_data[key]).strip():
            skills.append(f"{display_name} +{monster_data[key]}")

    if skills:
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Skills</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{', '.join(skills)}</span>
</div>""")

    # Senses
    if monster_data.get('senses'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Senses</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['senses']}</span>
</div>""")

    # Languages
    if monster_data.get('languages'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Languages</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['languages']}</span>
</div>""")

    # Damage Vulnerabilities, Resistances, Immunities, Condition Immunities (only if they have values)
    if monster_data.get('damage_vulnerabilities'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Damage Vulnerabilities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['damage_vulnerabilities']}</span>
</div>""")
    if monster_data.get('damage_resistances'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Damage Resistances</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['damage_resistances']}</span>
</div>""")
    if monster_data.get('damage_immunities'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Damage Immunities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['damage_immunities']}</span>
</div>""")
    if monster_data.get('condition_immunities'):
        tidbits_html.append(f"""
<div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
    <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Condition Immunities</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{monster_data['condition_immunities']}</span>
</div>""")


    # Challenge Rating and Proficiency Bonus
    cr_str = str(monster_data.get('challenge_rating', '0'))
    xp, pb = _calculate_xp_and_pb(cr_str)
    
    tidbits_html.append(f"""
<div class="mon-stat-block__tidbit-container" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; display: flex;">
    <div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Challenge</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">{cr_str} ({xp} XP)</span>
    </div>
    <div class="mon-stat-block__tidbit-spacer" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; width: 40px; min-width: 10px;"></div>
    <div class="mon-stat-block__tidbit" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin: 5px 0px; color: rgb(130, 32, 0); line-height: 1.2;">
        <span class="mon-stat-block__tidbit-label" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">Proficiency Bonus</span>&nbsp;<span class="mon-stat-block__tidbit-data" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">+{pb}</span>
    </div>
</div>
""")

    return "\n".join(tidbits_html)

def _generate_description_block_html(heading_text, items):
    """Generates HTML for special abilities, actions, or legendary actions."""
    if not items:
        return ""

    content_html = ""
    for item in items:
        name = item.get('name', 'Unknown')
        desc = item.get('desc', 'No description.')
        
        # Replace newlines with <br> for HTML display if present
        desc = desc.replace('\\n', '<br>')

        # Use BeautifulSoup to parse and clean the description HTML, removing hrefs
        soup = BeautifulSoup(desc, 'html.parser')
        for a_tag in soup.find_all('a'):
            a_tag.unwrap() # Remove the <a> tag but keep its content

        # Convert back to string and ensure it's clean (no extra newlines from BeautifulSoup)
        cleaned_desc = str(soup).strip()
        
        # Add emphasis/strong tags as per example
        if heading_text == "Traits":
             content_html += f"""<p style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;"><em style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><strong style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{name}.</strong></em>&nbsp;{cleaned_desc}</p>"""
        else: # For Actions and Legendary Actions, name is usually bold, then desc follows.
            content_html += f"""<p style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-bottom: 10px;"><strong style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; font-weight: bold;">{name}.</strong>&nbsp;{cleaned_desc}</p>"""
            
    return f"""
<div class="mon-stat-block__description-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
    <div class="mon-stat-block__description-block-heading" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: rgb(130, 32, 0); color: rgb(130, 32, 0); font-size: 24px; line-height: 1.4; margin-top: 20px; margin-bottom: 15px;">{heading_text}</div>
    <div class="mon-stat-block__description-block-content" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
        {content_html}
    </div>
</div>
"""

def format_monster_notes(monster_data):
    """
    Formats various attributes of a monster into a comprehensive HTML string
    mimicking D&D Beyond stat block styling for the 'notes' field.
    All href links are removed.
    """
    
    header_html = _generate_header_html(monster_data)
    attributes_html = _generate_attributes_html(monster_data)
    ability_scores_html = _generate_ability_scores_html_for_main_block(monster_data)
    tidbits_html = _generate_tidbits_html(monster_data)
    
    traits_html = _generate_description_block_html("Traits", monster_data.get('special_abilities', []))
    actions_html = _generate_description_block_html("Actions", monster_data.get('actions', []))
    legendary_actions_html = _generate_description_block_html("Legendary Actions", monster_data.get('legendary_actions', []))

    full_notes_html = f"""
<div class="mon-stat-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; color: rgb(0, 0, 0); font-family: &quot;Scala Sans Offc&quot;, Roboto, Helvetica, sans-serif; font-size: 15px; font-variant-caps: normal; letter-spacing: normal;">
    {header_html}
    <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: none; min-height: 10px;"></div>
    {attributes_html}
    <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: none; min-height: 10px;"></div>
    <div class="ability-block" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; display: flex; flex-wrap: wrap; margin: 0px; color: rgb(130, 32, 0);">
        {ability_scores_html}
    </div>
    <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: none; min-height: 10px;"></div>
    <div class="mon-stat-block__tidbits" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;">
        {tidbits_html}
    </div>
    <div class="mon-stat-block__separator" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px;"><img class="mon-stat-block__separator-img" alt="" src="https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; border-style: none; min-height: 10px;"></div>
    <div class="mon-stat-block__description-blocks" style="box-sizing: inherit; -webkit-tap-highlight-color: transparent; outline: 0px; margin-top: 20px;">
        {traits_html}
        {actions_html}
        {legendary_actions_html}
    </div>
</div>
"""
    return full_notes_html


def convert_monster_data(input_json_path, output_json_path):
    """
    Reads monster data from a JSON file and converts it to the Initiative Tracker format.
    """
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            monster_dump_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_json_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_json_path}. Please ensure it's valid JSON.")
        return

    converted_monsters = []
    for monster in monster_dump_data:
        # Check for a valid monster name before proceeding
        original_name = monster.get('name')
        if not original_name: # Skips if name is missing or an empty string
            print("Warning: Skipping an entry because monster name is missing.")
            continue

        try:
            # Ensure HP is an integer for totalHp
            hp_value = int(monster.get('hit_points', 0))
            
            # Get CR for the challenge field
            cr = monster.get('challenge_rating', '0')
            
            # Calculate initiative bonus from Dexterity
            dex_score = monster.get('dexterity', 10) # Default to 10 (modifier of 0) if missing
            initiative_bonus = 0
            if isinstance(dex_score, int):
                initiative_bonus = math.floor((dex_score - 10) / 2)

            converted_monster = {
                "name": original_name,
                "hp": str(hp_value),
                "totalHp": str(hp_value),
                "initiativeBonus": initiative_bonus,
                "version": "dnd_5e",
                "challenge": str(cr),
                "notes": format_monster_notes(monster)
            }

            converted_monsters.append(converted_monster)
        except Exception as e:
            # Now using original_name in the warning message for better context
            print(f"Warning: Failed to process monster '{original_name}' due to: {e}")
            continue

    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(converted_monsters, f, indent=2, ensure_ascii=False)
        print(f"Successfully converted {len(converted_monsters)} monsters to {output_json_path}")
    except IOError as e:
        print(f"Error writing to output file {output_json_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert D&D monster data from a dump to Initiative Tracker format.")
    parser.add_argument("input_file", type=str, help="Path to the input JSON monster dump file.")
    parser.add_argument("output_file", type=str, help="Path for the output JSON file in Initiative Tracker format.")
    
    args = parser.parse_args()
    
    convert_monster_data(args.input_file, args.output_file)
